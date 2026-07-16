from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.constants import (
    ESTADO_SOL_APROBADA,
    ESTADO_SOL_DENEGADA,
    ESTADO_SOL_PENDIENTE,
    ESTADO_SOL_PENDIENTE_APROBACION,
    RESPUESTA_APROBADA,
    RESPUESTA_DENEGADA,
    ROLE_SUPERADMIN,
)
from app.extensions import db
from app.mail import (
    enviar_correos_nueva_solicitud,
    mail_tic_respuesta_aprobacion,
)
from app.main.forms import RespuestaAprobacionForm, SolicitudUsuarioForm, UsabilidadSusForm
from app.models import Equipo, SolicitudMantenimiento
from app.solicitud_service import (
    choices_equipo_por_area,
    crear_solicitud_con_adjuntos,
    listar_equipos_por_area_laboral,
    preparar_evidencias,
)
from app.usabilidad_service import encuesta_de_usuario, guardar_encuesta_sus
from app.validators import flash_form_errors

bp = Blueprint("main", __name__)


def _equipo_resumen(eq: Equipo) -> dict:
    return {
        "numero_inventario": eq.numero_inventario or "",
        "numero_contable": eq.numero_contable or "",
        "codigo_contable": eq.codigo_contable or "",
        "departamento": eq.departamento or "",
        "area": eq.area or "",
        "usuario": eq.usuario or "",
        "cargo": eq.cargo or "",
        "descripcion": eq.descripcion or "",
        "marca_referencia": eq.marca_referencia or "",
        "service_tag": eq.service_tag or "",
        "serial_cpu": eq.serial_cpu or "",
        "fecha_adquisicion": eq.fecha_adquisicion.strftime("%d/%m/%Y") if eq.fecha_adquisicion else "",
        "observaciones": eq.observaciones or "",
    }


@bp.route("/")
def inicio():
    sus_pendiente = False
    if current_user.is_authenticated and not current_user.is_superadmin():
        try:
            sus_pendiente = encuesta_de_usuario(current_user.id) is None
        except Exception:
            db.session.rollback()
            sus_pendiente = False
    return render_template("inicio.html", sus_pendiente=sus_pendiente)


@bp.route("/usabilidad/encuesta", methods=["GET", "POST"])
@login_required
def usabilidad_encuesta():
    if current_user.is_superadmin():
        flash("Esta encuesta es para los usuarios del portal. Como administrador puede ver los resultados en Usabilidad.", "info")
        return redirect(url_for("equipos.usabilidad"))

    existente = encuesta_de_usuario(current_user.id)
    form = UsabilidadSusForm()
    if request.method == "GET" and existente:
        for i in range(1, 11):
            getattr(form, f"q{i}").data = str(getattr(existente, f"q{i}"))

    if form.validate_on_submit():
        answers = [int(getattr(form, f"q{i}").data) for i in range(1, 11)]
        try:
            row = guardar_encuesta_sus(current_user.id, answers)
            flash(
                f"Gracias por responder. Su puntuaci?n qued? en {float(row.score):.0f} de 100. Si quiere, puede actualizarla m?s adelante.",
                "success",
            )
            return redirect(url_for("main.inicio"))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("usabilidad_encuesta")
            flash("No se pudo guardar la encuesta. Intente de nuevo.", "danger")
    elif form.is_submitted():
        flash_form_errors(form)

    return render_template(
        "main/usabilidad_encuesta.html",
        form=form,
        ya_respondio=existente is not None,
        score_actual=float(existente.score) if existente else None,
    )


@bp.route("/login")
def login_alias():
    """Atajo: /login ? /auth/login (evita 404 si el usuario escribe la URL corta)."""
    return redirect(url_for("auth.login", **request.args))


@bp.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="favicon.svg"))


@bp.route("/mis-aprobaciones", methods=["GET", "POST"])
@login_required
def mis_aprobaciones():
    if getattr(current_user, "role", None) == ROLE_SUPERADMIN:
        return redirect(url_for("equipos.lista"))

    pendientes = (
        SolicitudMantenimiento.query.filter_by(
            usuario_aprobador_id=current_user.id,
            estado=ESTADO_SOL_PENDIENTE_APROBACION,
        )
        .order_by(SolicitudMantenimiento.creado_en.desc())
        .all()
    )

    sol_id = request.args.get("id", type=int) or request.form.get("solicitud_id", type=int)
    solicitud = None
    if sol_id:
        solicitud = db.session.get(SolicitudMantenimiento, sol_id)
        if (
            solicitud is None
            or solicitud.usuario_aprobador_id != current_user.id
            or solicitud.estado != ESTADO_SOL_PENDIENTE_APROBACION
        ):
            solicitud = None

    form = RespuestaAprobacionForm()
    if solicitud and request.method == "GET" and solicitud.fecha_mantenimiento:
        form.fecha_mantenimiento.data = solicitud.fecha_mantenimiento

    if request.method == "POST" and solicitud:
        if form.validate_on_submit():
            decision = form.decision.data
            comentario = (form.comentario.data or "").strip() or None
            try:
                if decision == RESPUESTA_APROBADA:
                    if not form.fecha_mantenimiento.data:
                        flash("Indique la fecha en la que puede recibir el mantenimiento.", "warning")
                    elif (
                        solicitud.fecha_solicitud
                        and form.fecha_mantenimiento.data < solicitud.fecha_solicitud
                    ):
                        flash(
                            "La fecha de mantenimiento no puede ser anterior a la fecha de la solicitud TIC.",
                            "warning",
                        )
                    else:
                        solicitud.respuesta_usuario = RESPUESTA_APROBADA
                        solicitud.fecha_respuesta_usuario = form.fecha_mantenimiento.data
                        solicitud.fecha_mantenimiento = form.fecha_mantenimiento.data
                        solicitud.comentario_respuesta = comentario
                        solicitud.estado = ESTADO_SOL_APROBADA
                        db.session.commit()
                        if current_app.config.get("MAIL_ENABLED"):
                            try:
                                if not mail_tic_respuesta_aprobacion(solicitud):
                                    flash(
                                        "Mantenimiento aprobado. No se pudo enviar el aviso por correo a TIC.",
                                        "warning",
                                    )
                                else:
                                    flash(
                                        "Mantenimiento aprobado. TIC fue notificado con la fecha indicada.",
                                        "success",
                                    )
                            except Exception:
                                current_app.logger.exception("mail aprobacion")
                                flash(
                                    "Mantenimiento aprobado. No se pudo enviar el correo a TIC.",
                                    "warning",
                                )
                        else:
                            flash(
                                "Mantenimiento aprobado. TIC ver? la respuesta en el panel de solicitudes.",
                                "success",
                            )
                        return redirect(url_for("main.mis_aprobaciones"))
                elif decision == RESPUESTA_DENEGADA:
                    if not form.fecha_mantenimiento.data:
                        flash(
                            "Indique la fecha hasta la cual debe permanecer visible la solicitud denegada.",
                            "warning",
                        )
                    else:
                        solicitud.respuesta_usuario = RESPUESTA_DENEGADA
                        solicitud.fecha_respuesta_usuario = form.fecha_mantenimiento.data
                        solicitud.fecha_mantenimiento = form.fecha_mantenimiento.data
                        solicitud.comentario_respuesta = comentario
                        solicitud.estado = ESTADO_SOL_DENEGADA
                        db.session.commit()
                        if current_app.config.get("MAIL_ENABLED"):
                            try:
                                if not mail_tic_respuesta_aprobacion(solicitud):
                                    flash(
                                        "Solicitud denegada. No se pudo enviar el aviso por correo a TIC.",
                                        "warning",
                                    )
                                else:
                                    flash(
                                        "Solicitud denegada. Permanece abierta hasta la fecha indicada.",
                                        "info",
                                    )
                            except Exception:
                                current_app.logger.exception("mail denegacion")
                                flash(
                                    "Solicitud denegada. No se pudo enviar el correo a TIC.",
                                    "warning",
                                )
                        else:
                            flash(
                                "Solicitud denegada. Permanece abierta hasta la fecha indicada.",
                                "info",
                            )
                        return redirect(url_for("main.mis_aprobaciones"))
            except Exception:
                db.session.rollback()
                current_app.logger.exception("mis_aprobaciones POST")
                flash(
                    "No se pudo guardar la respuesta. Intente de nuevo; si persiste, contacte a TIC.",
                    "danger",
                )
        elif form.is_submitted():
            flash_form_errors(form)

    return render_template(
        "main/mis_aprobaciones.html",
        pendientes=pendientes,
        solicitud=solicitud,
        form=form,
        sol_id=sol_id,
        equipo_resumen=_equipo_resumen(solicitud.equipo) if solicitud and solicitud.equipo else None,
    )


@bp.route("/api/session/ping")
@login_required
def session_ping():
    """Heartbeat liviano: solo valida sesi?n y reporta boot_id (sin chat/DB pesada)."""
    from flask import jsonify

    return jsonify({"ok": True, "boot_id": current_app.config.get("APP_BOOT_ID", "")})



@bp.route("/api/indicators")
@login_required
def api_indicators():
    """Indicadores globales en vivo (aprobaciones, conectados, presencia opcional por IDs)."""
    from flask import jsonify

    from app.presence_service import count_online_users, count_pending_approvals, users_presence_snapshot

    try:
        payload: dict = {
            "ok": True,
            "online_count": count_online_users(),
            "pending_approvals_count": None,
        }
        if not current_user.is_superadmin():
            payload["pending_approvals_count"] = count_pending_approvals(current_user.id)

        user_ids_raw = (request.args.get("user_ids") or "").strip()
        if user_ids_raw:
            ids: list[int] = []
            for part in user_ids_raw.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.append(int(part))
            payload["users"] = users_presence_snapshot(ids[:80])
        return jsonify(payload)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("api_indicators")
        return jsonify({"ok": False, "online_count": 0, "pending_approvals_count": None}), 500


@bp.route("/api/chat/estado")
@login_required
def chat_estado():
    from flask import jsonify

    from app.chat_service import (
        CHAT_TIPO_AREA,
        CHAT_TIPO_SUSURRO,
        historial_reciente,
        mensajes_desde,
        mensaje_a_dict,
        normalizar_area,
        portal_usuarios_chat_payload,
    )

    try:
        since_id = request.args.get("since_id", 0, type=int) or 0
        modo = (request.args.get("modo") or CHAT_TIPO_AREA).strip()
        if modo not in (CHAT_TIPO_AREA, CHAT_TIPO_SUSURRO):
            modo = CHAT_TIPO_AREA
        peer_id = request.args.get("peer_id", type=int)
        user_area = normalizar_area(getattr(current_user, "area", None))
        # Por defecto solo en carga inicial; el JS pide presencia cada N polls.
        include_presence = request.args.get("presence", "0" if since_id > 0 else "1")
        want_presence = str(include_presence).strip().lower() in ("1", "true", "yes")

        if since_id <= 0:
            msgs = historial_reciente(current_user.id, user_area, modo, peer_id)
        else:
            msgs = mensajes_desde(current_user.id, user_area, modo, peer_id, since_id)

        payload = {
            "messages": [mensaje_a_dict(m, current_user.id) for m in msgs],
            "modo": modo,
            "area": user_area,
            "self_user_id": current_user.id,
        }
        if want_presence:
            usuarios, online_count = portal_usuarios_chat_payload()
            payload["usuarios"] = usuarios
            payload["online_count"] = online_count
        return jsonify(payload)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("chat_estado")
        return jsonify({"messages": [], "error": "No se pudo cargar el chat."}), 500


@bp.route("/api/presence/offline", methods=["POST"])
@login_required
def presence_offline():
    from flask import jsonify
    from flask_wtf.csrf import validate_csrf
    from wtforms.validators import ValidationError

    from app.presence_service import mark_user_offline

    token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    try:
        validate_csrf(token)
    except ValidationError:
        return jsonify({"ok": False}), 400
    mark_user_offline(current_user.id)
    return jsonify({"ok": True})


@bp.route("/api/chat/enviar", methods=["POST"])
@login_required
def chat_enviar():
    from flask import jsonify
    from flask_wtf.csrf import validate_csrf
    from wtforms.validators import ValidationError

    from app.chat_service import (
        CHAT_TIPO_SUSURRO,
        crear_mensaje_area,
        crear_mensaje_susurro,
        mensaje_a_dict,
        normalizar_area,
    )

    token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    try:
        validate_csrf(token)
    except ValidationError:
        return jsonify({"ok": False, "error": "Sesi?n expirada. Recargue la p?gina."}), 400

    data = request.get_json(silent=True) or {}
    texto = (data.get("texto") or request.form.get("texto") or "").strip()
    if not texto:
        return jsonify({"ok": False, "error": "Escriba un mensaje."}), 400
    if len(texto) > 500:
        return jsonify({"ok": False, "error": "M?ximo 500 caracteres."}), 400

    destinatario_id = data.get("destinatario_id")
    if destinatario_id is not None:
        try:
            destinatario_id = int(destinatario_id)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Destinatario no v?lido."}), 400
        msg = crear_mensaje_susurro(current_user.id, destinatario_id, texto)
        if msg is None:
            return jsonify({"ok": False, "error": "No se puede enviar el susurro a ese usuario."}), 400
    else:
        msg = crear_mensaje_area(
            current_user.id,
            normalizar_area(getattr(current_user, "area", None)),
            texto,
        )

    from app.presence_service import touch_presence

    touch_presence(current_user.id, force=True)
    return jsonify({"ok": True, "message": mensaje_a_dict(msg, current_user.id)})


@bp.route("/registrar-solicitud", methods=["GET", "POST"])
@login_required
def registrar_solicitud():
    if getattr(current_user, "role", None) == ROLE_SUPERADMIN:
        return redirect(url_for("equipos.lista"))

    equipos_area = listar_equipos_por_area_laboral(getattr(current_user, "area", None))
    form = SolicitudUsuarioForm()
    form.numero_inventario.choices = choices_equipo_por_area(equipos_area)

    if request.method == "GET" and not form.fecha_solicitud.data:
        form.fecha_solicitud.data = date.today()

    if request.method == "POST":
        if form.validate_on_submit():
            inv = (form.numero_inventario.data or "").strip()
            equipo = Equipo.query.filter_by(numero_inventario=inv).first()
            permitidos = {e.numero_inventario for e in equipos_area}
            if equipo is None or inv not in permitidos:
                flash(
                    "No se pudo validar el equipo seleccionado. Elija un equipo de la lista de su ?rea.",
                    "warning",
                )
            else:
                files = request.files.getlist("evidencias")
                prepared, err = preparar_evidencias(files)
                if err:
                    flash(err, "warning")
                else:
                    obs = (form.observaciones.data or "").strip() or None
                    sol, err2 = crear_solicitud_con_adjuntos(
                        equipo,
                        form.fecha_solicitud.data,
                        form.fecha_mantenimiento.data,
                        obs,
                        prepared,
                        current_user.id,
                    )
                    if err2:
                        flash(err2, "danger")
                    else:
                        enviar_correos_nueva_solicitud(sol)
                        flash(
                            "Solicitud registrada correctamente. Si el correo est? activado (MAIL_ENABLED), "
                            "TIC y usted recibir?n el aviso correspondiente.",
                            "success",
                        )
                        return redirect(url_for("main.inicio"))
        elif form.is_submitted():
            flash_form_errors(form)

    max_bytes = int(current_app.config.get("MAX_UPLOAD_BYTES_PER_FILE") or (5 * 1024 * 1024))
    return render_template(
        "main/registrar_solicitud.html",
        form=form,
        equipos_en_area=len(equipos_area),
        equipos_area=equipos_area,
        equipos_json=[_equipo_resumen(e) for e in equipos_area],
        max_upload_files=int(current_app.config.get("MAX_UPLOAD_FILES") or 12),
        max_upload_mb=max(1, max_bytes // (1024 * 1024)),
    )
