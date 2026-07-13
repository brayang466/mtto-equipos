"""Lógica compartida para crear solicitudes de mantenimiento y adjuntos."""
from __future__ import annotations

import secrets
from pathlib import Path
from datetime import date

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from sqlalchemy import Integer, cast, func

from app.constants import (
    ESTADO_SOL_APROBADA,
    ESTADO_SOL_ATENDIDA,
    ESTADO_SOL_DENEGADA,
    ESTADO_SOL_PENDIENTE,
    ESTADO_SOL_PENDIENTE_APROBACION,
    RESPUESTA_APROBADA,
    RESPUESTA_DENEGADA,
    TIPO_ORIGEN_TIC,
    TIPO_ORIGEN_USUARIO,
)
from app.extensions import db
from app.models import Equipo, SolicitudAdjunto, SolicitudMantenimiento, User


def _label_equipo_en_lista(eq: Equipo) -> str:
    partes: list[str] = [eq.numero_inventario]
    desc = (eq.descripcion or "").strip()
    if desc:
        if len(desc) > 52:
            desc = desc[:49] + "…"
        partes.append(desc)
    usr = (eq.usuario or "").strip()
    if usr:
        if len(usr) > 38:
            usr = usr[:35] + "…"
        partes.append(usr)
    return " — ".join(partes)


def listar_equipos_por_area_laboral(area_usuario: str | None) -> list[Equipo]:
    """
    Equipos cuyo campo inventario `area` coincide con el área del usuario (trim, sin distinguir mayúsculas).
    """
    a = (area_usuario or "").strip()
    if not a:
        return []
    return (
        Equipo.query.filter(func.lower(func.trim(Equipo.area)) == a.lower())
        .order_by(cast(Equipo.numero_inventario, Integer).asc())
        .all()
    )


def choices_equipo_por_area(equipos: list[Equipo]) -> list[tuple[str, str]]:
    """Opciones (valor=numero_inventario, etiqueta) para un SelectField."""
    if not equipos:
        return [("", "— Sin equipos en inventario para su área — contacte a TIC —")]
    return [("", "Seleccione su equipo…")] + [
        (e.numero_inventario, _label_equipo_en_lista(e)) for e in equipos
    ]


def preparar_evidencias(files: list[FileStorage]) -> tuple[list[tuple[str, str, bytes, str | None]], str | None]:
    """
    Valida y lee en memoria los archivos subidos.
    Devuelve (prepared, error) donde prepared es lista de (orig, ext, data, mime).
    """
    max_files = int(current_app.config.get("MAX_UPLOAD_FILES") or 12)
    max_bytes = int(current_app.config.get("MAX_UPLOAD_BYTES_PER_FILE") or (5 * 1024 * 1024))
    allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS") or frozenset()

    non_empty = [f for f in files if f and f.filename]
    if len(non_empty) > max_files:
        return [], f"Como máximo {max_files} imágenes por solicitud."

    prepared: list[tuple[str, str, bytes, str | None]] = []
    for f in non_empty:
        orig = secure_filename(f.filename or "") or "imagen"
        ext = Path(orig).suffix.lower().lstrip(".")
        if ext not in allowed:
            return [], f"Formato no permitido: .{ext or '?'}. Use: {', '.join(sorted(allowed))}."
        data = f.read()
        if len(data) > max_bytes:
            return [], f"Cada imagen debe pesar como máximo {max_bytes // (1024 * 1024)} MB."
        mime = (f.mimetype or "")[:128] or None
        prepared.append((orig, ext, data, mime))
    return prepared, None


def crear_solicitud_con_adjuntos(
    equipo: Equipo,
    fecha_solicitud: date,
    fecha_mantenimiento: date | None,
    observaciones: str | None,
    prepared: list[tuple[str, str, bytes, str | None]],
    registrado_por_user_id: int | None,
) -> tuple[SolicitudMantenimiento | None, str | None]:
    """
    Persiste solicitud + archivos. Devuelve (solicitud, None) o (None, mensaje_error).
    """
    solicitud = SolicitudMantenimiento(
        equipo_id=equipo.id,
        registrado_por_user_id=registrado_por_user_id,
        tipo_origen=TIPO_ORIGEN_USUARIO,
        fecha_solicitud=fecha_solicitud,
        fecha_mantenimiento=fecha_mantenimiento,
        observaciones=observaciones,
    )
    db.session.add(solicitud)
    db.session.flush()

    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    written: list[Path] = []
    try:
        for orig, ext, data, mime in prepared:
            disk_name = f"{secrets.token_hex(16)}.{ext}"
            full_path = upload_root / disk_name
            full_path.write_bytes(data)
            written.append(full_path)
            db.session.add(
                SolicitudAdjunto(
                    solicitud_id=solicitud.id,
                    nombre_archivo=disk_name,
                    nombre_original=orig[:500],
                    mime=mime,
                    tamano_bytes=len(data),
                )
            )
        db.session.commit()
    except OSError:
        db.session.rollback()
        for p in written:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        return None, "No se pudieron guardar las imágenes. Intente de nuevo."
    return solicitud, None


def usuarios_aprobadores_por_equipo(equipo: Equipo) -> list[User]:
    """Usuarios del portal en la misma área laboral que el equipo (para aprobar)."""
    area = (equipo.area or "").strip()
    q = User.query.filter(User.activo.is_(True), User.role == "user")
    if area:
        q = q.filter(func.lower(func.trim(User.area)) == area.lower())
    return q.order_by(User.username).all()


def choices_usuario_aprobador(users: list[User]) -> list[tuple[str, str]]:
    if not users:
        return [("", "— No hay usuarios en el área del equipo —")]
    return [("", "Seleccione al usuario que debe aprobar…")] + [
        (str(u.id), f"{u.username} ({u.email})") for u in users
    ]


def crear_solicitud_tic(
    equipo: Equipo,
    fecha_solicitud: date,
    fecha_mantenimiento_propuesta: date | None,
    observaciones: str | None,
    registrado_por_user_id: int,
    usuario_aprobador_id: int,
) -> tuple[SolicitudMantenimiento | None, str | None]:
    aprobador = db.session.get(User, usuario_aprobador_id)
    if aprobador is None or not aprobador.activo:
        return None, "El usuario seleccionado no es válido."
    solicitud = SolicitudMantenimiento(
        equipo_id=equipo.id,
        registrado_por_user_id=registrado_por_user_id,
        tipo_origen=TIPO_ORIGEN_TIC,
        usuario_aprobador_id=usuario_aprobador_id,
        fecha_solicitud=fecha_solicitud,
        fecha_mantenimiento=fecha_mantenimiento_propuesta,
        observaciones=observaciones,
        estado=ESTADO_SOL_PENDIENTE_APROBACION,
    )
    db.session.add(solicitud)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return None, "No se pudo registrar la solicitud. Intente de nuevo."
    return solicitud, None


def fecha_vigencia_usuario(sol: SolicitudMantenimiento) -> date | None:
    """Fecha indicada por el usuario (aprobación o denegación con fecha)."""
    if sol.fecha_respuesta_usuario:
        return sol.fecha_respuesta_usuario
    if sol.respuesta_usuario and sol.fecha_mantenimiento:
        return sol.fecha_mantenimiento
    return None


def denegada_sigue_abierta(sol: SolicitudMantenimiento, ref: date | None = None) -> bool:
    if sol.estado != ESTADO_SOL_DENEGADA:
        return False
    f = fecha_vigencia_usuario(sol)
    if not f:
        return False
    return f >= (ref or date.today())


def puede_marcar_atendida(sol: SolicitudMantenimiento) -> bool:
    if sol.estado in (ESTADO_SOL_PENDIENTE, ESTADO_SOL_APROBADA):
        return True
    return denegada_sigue_abierta(sol)


def etiqueta_estado_solicitud(sol: SolicitudMantenimiento) -> tuple[str, str]:
    """Etiqueta visible y clase CSS badge."""
    if sol.estado == ESTADO_SOL_PENDIENTE_APROBACION:
        return "Espera usuario", "warn"
    if sol.estado == ESTADO_SOL_APROBADA:
        return "Aprobada", "ok"
    if sol.estado == ESTADO_SOL_ATENDIDA:
        return "Atendida", "ok"
    if sol.estado == ESTADO_SOL_DENEGADA:
        if denegada_sigue_abierta(sol):
            f = fecha_vigencia_usuario(sol)
            txt = f"Denegada · abierta hasta {f.strftime('%d/%m/%Y')}" if f else "Denegada"
            return txt, "warn"
        return "Denegada · cerrada", "no"
    return "Pendiente", "no"


def respuesta_usuario_legible(sol: SolicitudMantenimiento) -> str:
    if sol.respuesta_usuario == RESPUESTA_APROBADA:
        return "Aprobada"
    if sol.respuesta_usuario == RESPUESTA_DENEGADA:
        return "Denegada"
    return "—"


def solicitud_detalle_context(sol: SolicitudMantenimiento) -> dict:
    eq = sol.equipo
    aprobador = sol.usuario_aprobador
    registrador = sol.registrado_por
    return {
        "sol": sol,
        "equipo": eq,
        "tipo_origen": "TIC → usuario" if sol.tipo_origen == TIPO_ORIGEN_TIC else "Usuario",
        "registrado_por": registrador.username if registrador else "Panel TIC",
        "aprobador": aprobador.username if aprobador else "—",
        "aprobador_area": (aprobador.area if aprobador else None) or "—",
        "respuesta_texto": respuesta_usuario_legible(sol),
        "denegada_abierta": denegada_sigue_abierta(sol),
        "puede_atender": puede_marcar_atendida(sol),
        "estado_label": etiqueta_estado_solicitud(sol),
    }


def eliminar_solicitud_completa(sol: SolicitudMantenimiento) -> None:
    """Elimina la solicitud y los archivos de evidencia en disco."""
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    for adj in list(sol.adjuntos):
        path = (upload_root / adj.nombre_archivo).resolve()
        try:
            path.relative_to(upload_root)
            if path.is_file():
                path.unlink(missing_ok=True)
        except (ValueError, OSError):
            pass
    db.session.delete(sol)
    db.session.commit()


def aplicar_edicion_admin_solicitud(
    sol: SolicitudMantenimiento,
    *,
    fecha_solicitud: date,
    fecha_mantenimiento: date | None,
    fecha_respuesta_usuario: date | None,
    estado: str,
    observaciones: str | None,
    comentario_respuesta: str | None,
    respuesta_usuario: str | None,
) -> None:
    from app.datetime_utils import now_colombia_naive

    sol.fecha_solicitud = fecha_solicitud
    sol.fecha_mantenimiento = fecha_mantenimiento
    sol.fecha_respuesta_usuario = fecha_respuesta_usuario
    sol.estado = estado
    sol.observaciones = observaciones
    sol.comentario_respuesta = comentario_respuesta
    sol.respuesta_usuario = respuesta_usuario or None
    if estado == ESTADO_SOL_ATENDIDA:
        if not sol.atendido_en:
            sol.atendido_en = now_colombia_naive()
    else:
        sol.atendido_en = None
    db.session.commit()

