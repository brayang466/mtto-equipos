"""Métricas de usabilidad operativa y agregado SUS."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.constants import (
    CHAT_TIPO_AREA,
    CHAT_TIPO_SUSURRO,
    ESTADO_SOL_APROBADA,
    ESTADO_SOL_ATENDIDA,
    ESTADO_SOL_DENEGADA,
    ESTADO_SOL_PENDIENTE,
    ESTADO_SOL_PENDIENTE_APROBACION,
    RESPUESTA_APROBADA,
    RESPUESTA_DENEGADA,
    ROLE_USER,
)
from app.datetime_utils import now_colombia_naive
from app.extensions import db
from app.models import (
    ChatMensaje,
    SolicitudAdjunto,
    SolicitudMantenimiento,
    UsabilidadEncuesta,
    User,
    UserPresence,
)
from app.presence_service import PRESENCE_OFFLINE_MARKER, PRESENCE_ONLINE_SECONDS
from app.solicitud_service import denegada_sigue_abierta


def calcular_score_sus(answers: list[int] | tuple[int, ...]) -> float:
    """SUS clásico: 10 ítems Likert 1–5 → score 0–100."""
    if len(answers) != 10:
        raise ValueError("Se requieren exactamente 10 respuestas SUS.")
    total = 0.0
    for i, raw in enumerate(answers):
        v = int(raw)
        if v < 1 or v > 5:
            raise ValueError(f"Respuesta inválida en ítem {i + 1}: {v}")
        if i % 2 == 0:  # impar (q1, q3, …): contribución = v - 1
            total += v - 1
        else:  # par (q2, q4, …): contribución = 5 - v
            total += 5 - v
    return round(total * 2.5, 2)


def encuesta_de_usuario(user_id: int) -> UsabilidadEncuesta | None:
    return UsabilidadEncuesta.query.filter_by(user_id=user_id).first()


def guardar_encuesta_sus(user_id: int, answers: list[int]) -> UsabilidadEncuesta:
    score = calcular_score_sus(answers)
    row = encuesta_de_usuario(user_id)
    if row is None:
        row = UsabilidadEncuesta(user_id=user_id)
        db.session.add(row)
    for i in range(10):
        setattr(row, f"q{i + 1}", int(answers[i]))
    row.score = Decimal(str(score))
    db.session.commit()
    db.session.refresh(row)
    return row


def _semaforo(valor: float | None, *, bueno_min: float, malo_max: float, invertido: bool = False) -> str:
    """Devuelve 'ok' | 'warn' | 'no' según umbrales. invertido=True: valores altos son peores."""
    if valor is None:
        return "warn"
    if invertido:
        if valor <= bueno_min:
            return "ok"
        if valor >= malo_max:
            return "no"
        return "warn"
    if valor >= bueno_min:
        return "ok"
    if valor <= malo_max:
        return "no"
    return "warn"


def _pct(parte: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(100.0 * parte / total, 1)


def _parse_fecha(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _filtro_solicitudes(q, desde: date | None, hasta: date | None):
    if desde:
        q = q.filter(SolicitudMantenimiento.fecha_solicitud >= desde)
    if hasta:
        q = q.filter(SolicitudMantenimiento.fecha_solicitud <= hasta)
    return q


def _filtro_chat(q, desde: date | None, hasta: date | None):
    if desde:
        q = q.filter(ChatMensaje.creado_en >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        q = q.filter(
            ChatMensaje.creado_en < datetime.combine(hasta + timedelta(days=1), datetime.min.time())
        )
    return q


def agregar_sus() -> dict:
    rows = UsabilidadEncuesta.query.all()
    n = len(rows)
    usuarios_activos = User.query.filter(User.activo.is_(True), User.role == ROLE_USER).count()
    if n == 0:
        return {
            "n": 0,
            "promedio": None,
            "pct_respuesta": _pct(0, usuarios_activos) if usuarios_activos else None,
            "usuarios_elegibles": usuarios_activos,
            "excelente": 0,
            "aceptable": 0,
            "mejorar": 0,
            "semaforo": "warn",
            "interpretacion": "Todavía nadie ha respondido la encuesta. Cuando los usuarios la completen, aquí verá el resultado.",
        }
    scores = [float(r.score) for r in rows]
    promedio = round(sum(scores) / n, 1)
    excelente = sum(1 for s in scores if s >= 80)
    aceptable = sum(1 for s in scores if 68 <= s < 80)
    mejorar = sum(1 for s in scores if s < 68)
    sem = _semaforo(promedio, bueno_min=80, malo_max=67)
    if promedio >= 80:
        interp = "En general, los usuarios encuentran el portal fácil de usar."
    elif promedio >= 68:
        interp = "La valoración es aceptable: hay cosas que funcionan bien y otras que se pueden mejorar."
    else:
        interp = "La valoración es baja: conviene revisar qué pasos les cuestan más a los usuarios."
    return {
        "n": n,
        "promedio": promedio,
        "pct_respuesta": _pct(n, usuarios_activos) if usuarios_activos else None,
        "usuarios_elegibles": usuarios_activos,
        "excelente": excelente,
        "aceptable": aceptable,
        "mejorar": mejorar,
        "semaforo": sem,
        "interpretacion": interp,
    }


def kpis_operativos(desde: date | None = None, hasta: date | None = None) -> dict:
    now = now_colombia_naive()
    cutoff_online = now - timedelta(seconds=PRESENCE_ONLINE_SECONDS)
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)

    usuarios_activos = User.query.filter(User.activo.is_(True)).count()
    online = (
        UserPresence.query.join(User, User.id == UserPresence.user_id)
        .filter(
            User.activo.is_(True),
            UserPresence.last_seen >= cutoff_online,
            or_pagina_not_offline(),
        )
        .count()
    )
    activos_7 = (
        UserPresence.query.join(User, User.id == UserPresence.user_id)
        .filter(User.activo.is_(True), UserPresence.last_seen >= cutoff_7)
        .count()
    )
    activos_30 = (
        UserPresence.query.join(User, User.id == UserPresence.user_id)
        .filter(User.activo.is_(True), UserPresence.last_seen >= cutoff_30)
        .count()
    )
    adopcion_7 = _pct(activos_7, usuarios_activos)
    adopcion_30 = _pct(activos_30, usuarios_activos)

    q_sol = _filtro_solicitudes(SolicitudMantenimiento.query, desde, hasta)
    solicitudes = q_sol.all()
    total_sol = len(solicitudes)

    por_estado: dict[str, int] = {
        ESTADO_SOL_PENDIENTE: 0,
        ESTADO_SOL_PENDIENTE_APROBACION: 0,
        ESTADO_SOL_APROBADA: 0,
        ESTADO_SOL_DENEGADA: 0,
        ESTADO_SOL_ATENDIDA: 0,
    }
    for s in solicitudes:
        por_estado[s.estado] = por_estado.get(s.estado, 0) + 1

    atendidas = [s for s in solicitudes if s.estado == ESTADO_SOL_ATENDIDA and s.atendido_en]
    ciclos: list[float] = []
    for s in atendidas:
        if s.fecha_solicitud and s.atendido_en:
            delta = s.atendido_en.date() - s.fecha_solicitud
            ciclos.append(float(delta.days))
    ciclo_medio = round(sum(ciclos) / len(ciclos), 1) if ciclos else None

    respuesta_dias: list[float] = []
    for s in solicitudes:
        if s.respuesta_usuario and s.creado_en and s.fecha_respuesta_usuario:
            delta = s.fecha_respuesta_usuario - s.creado_en.date()
            respuesta_dias.append(float(max(0, delta.days)))

    tiempo_respuesta_medio = (
        round(sum(respuesta_dias) / len(respuesta_dias), 1) if respuesta_dias else None
    )

    tasa_cierre = _pct(por_estado.get(ESTADO_SOL_ATENDIDA, 0), total_sol)

    con_respuesta = [
        s for s in solicitudes if s.respuesta_usuario in (RESPUESTA_APROBADA, RESPUESTA_DENEGADA)
    ]
    aprobadas_n = sum(1 for s in con_respuesta if s.respuesta_usuario == RESPUESTA_APROBADA)
    denegadas_n = sum(1 for s in con_respuesta if s.respuesta_usuario == RESPUESTA_DENEGADA)
    tasa_aprobacion = _pct(aprobadas_n, len(con_respuesta)) if con_respuesta else None

    backlog = 0
    for s in solicitudes:
        if s.estado in (ESTADO_SOL_PENDIENTE, ESTADO_SOL_PENDIENTE_APROBACION, ESTADO_SOL_APROBADA):
            backlog += 1
        elif denegada_sigue_abierta(s):
            backlog += 1

    sol_ids = [s.id for s in solicitudes]
    con_adjuntos = 0
    if sol_ids:
        con_adjuntos = (
            db.session.query(func.count(func.distinct(SolicitudAdjunto.solicitud_id)))
            .filter(SolicitudAdjunto.solicitud_id.in_(sol_ids))
            .scalar()
            or 0
        )
    pct_evidencias = _pct(int(con_adjuntos), total_sol)

    q_chat = _filtro_chat(ChatMensaje.query, desde, hasta)
    mensajes = q_chat.all()
    total_msg = len(mensajes)
    msg_area = sum(1 for m in mensajes if m.tipo == CHAT_TIPO_AREA)
    msg_susurro = sum(1 for m in mensajes if m.tipo == CHAT_TIPO_SUSURRO)
    ratio_susurro = _pct(msg_susurro, total_msg)

    chat_por_area: dict[str, int] = {}
    for m in mensajes:
        if m.tipo != CHAT_TIPO_AREA:
            continue
        area = (m.area or "Sin área").strip() or "Sin área"
        chat_por_area[area] = chat_por_area.get(area, 0) + 1

    # Cobertura por área: usuarios activos vs solicitudes registradas por área del usuario
    cobertura: list[dict] = []
    areas_users = (
        db.session.query(User.area, func.count(User.id))
        .filter(User.activo.is_(True))
        .group_by(User.area)
        .all()
    )
    sol_por_area_user: dict[str, int] = {}
    for s in solicitudes:
        reg = s.registrado_por
        area = (reg.area if reg else None) or "Sin área"
        area = area.strip() or "Sin área"
        sol_por_area_user[area] = sol_por_area_user.get(area, 0) + 1
        # también por área del equipo
    for area, n_users in areas_users:
        a = (area or "Sin área").strip() or "Sin área"
        n_sol = sol_por_area_user.get(a, 0)
        cobertura.append(
            {
                "area": a,
                "usuarios": int(n_users),
                "solicitudes": n_sol,
                "solicitudes_por_usuario": round(n_sol / n_users, 2) if n_users else 0,
            }
        )
    cobertura.sort(key=lambda x: x["area"].lower())

    kpis = [
        {
            "id": "adopcion_7",
            "titulo": "Activos esta semana",
            "valor": adopcion_7,
            "unidad": "%",
            "detalle": f"{activos_7} de {usuarios_activos} cuentas entraron en los últimos 7 días",
            "semaforo": _semaforo(adopcion_7 or 0, bueno_min=40, malo_max=15),
            "interpretacion": "Cuántos usuarios del portal se conectaron en la última semana.",
        },
        {
            "id": "adopcion_30",
            "titulo": "Activos este mes",
            "valor": adopcion_30,
            "unidad": "%",
            "detalle": f"{activos_30} de {usuarios_activos} cuentas entraron en los últimos 30 días",
            "semaforo": _semaforo(adopcion_30 or 0, bueno_min=60, malo_max=25),
            "interpretacion": "Muestra si el portal se está usando de forma constante durante el mes.",
        },
        {
            "id": "online",
            "titulo": "Conectados ahora",
            "valor": online,
            "unidad": "",
            "detalle": "Personas en el portal en este momento",
            "semaforo": "ok" if online > 0 else "warn",
            "interpretacion": "Quién está trabajando en el sistema ahora mismo.",
        },
        {
            "id": "ciclo",
            "titulo": "Tiempo hasta cerrar",
            "valor": ciclo_medio,
            "unidad": "días",
            "detalle": f"Promedio de {len(ciclos)} solicitud(es) ya atendidas",
            "semaforo": _semaforo(ciclo_medio, bueno_min=7, malo_max=21, invertido=True)
            if ciclo_medio is not None
            else "warn",
            "interpretacion": "Cuántos días pasan, en promedio, desde que se pide el mantenimiento hasta que TIC lo marca como atendido.",
        },
        {
            "id": "respuesta_usuario",
            "titulo": "Tiempo de respuesta",
            "valor": tiempo_respuesta_medio,
            "unidad": "días",
            "detalle": f"Promedio de {len(respuesta_dias)} respuesta(s) del usuario",
            "semaforo": _semaforo(
                tiempo_respuesta_medio, bueno_min=3, malo_max=10, invertido=True
            )
            if tiempo_respuesta_medio is not None
            else "warn",
            "interpretacion": "Cuánto tarda el usuario en aprobar o denegar cuando TIC le pide mantenimiento.",
        },
        {
            "id": "cierre",
            "titulo": "Solicitudes cerradas",
            "valor": tasa_cierre,
            "unidad": "%",
            "detalle": f"{por_estado.get(ESTADO_SOL_ATENDIDA, 0)} atendidas de {total_sol} en total",
            "semaforo": _semaforo(tasa_cierre or 0, bueno_min=50, malo_max=20),
            "interpretacion": "Qué porcentaje de las solicitudes ya quedó resuelto.",
        },
        {
            "id": "aprobacion",
            "titulo": "Aprobaciones vs denegadas",
            "valor": tasa_aprobacion,
            "unidad": "%",
            "detalle": f"{aprobadas_n} aprobadas y {denegadas_n} denegadas",
            "semaforo": "ok" if tasa_aprobacion is not None else "warn",
            "interpretacion": "De las veces que el usuario respondió, cuántas fueron a favor del mantenimiento.",
        },
        {
            "id": "backlog",
            "titulo": "Pendientes por atender",
            "valor": backlog,
            "unidad": "",
            "detalle": "Incluye pendientes, en espera de respuesta, aprobadas y denegadas aún vigentes",
            "semaforo": _semaforo(float(backlog), bueno_min=5, malo_max=20, invertido=True),
            "interpretacion": "Cuántas solicitudes siguen abiertas y requieren seguimiento de TIC.",
        },
        {
            "id": "evidencias",
            "titulo": "Solicitudes con fotos",
            "valor": pct_evidencias,
            "unidad": "%",
            "detalle": f"{con_adjuntos} de {total_sol} trajeron evidencias",
            "semaforo": _semaforo(pct_evidencias or 0, bueno_min=40, malo_max=10),
            "interpretacion": "Qué tan seguido los usuarios adjuntan fotos al pedir mantenimiento.",
        },
        {
            "id": "chat_area",
            "titulo": "Mensajes del chat de área",
            "valor": msg_area,
            "unidad": "",
            "detalle": f"{total_msg} mensaje(s) en total (área + susurro)",
            "semaforo": "ok" if msg_area > 0 else "warn",
            "interpretacion": "Mensajes enviados dentro del chat de cada área.",
        },
        {
            "id": "susurro",
            "titulo": "Mensajes privados (susurro)",
            "valor": ratio_susurro,
            "unidad": "%",
            "detalle": f"{msg_susurro} de {total_msg} fueron privados",
            "semaforo": "ok" if total_msg == 0 or (ratio_susurro or 0) < 70 else "warn",
            "interpretacion": "Qué proporción del chat son conversaciones privadas entre personas de distintas áreas.",
        },
    ]

    return {
        "kpis": kpis,
        "por_estado": por_estado,
        "total_solicitudes": total_sol,
        "chat_por_area": sorted(chat_por_area.items(), key=lambda x: (-x[1], x[0].lower())),
        "cobertura": cobertura,
        "desde": desde,
        "hasta": hasta,
    }


def or_pagina_not_offline():
    from sqlalchemy import or_

    return or_(
        UserPresence.pagina_actual.is_(None),
        UserPresence.pagina_actual != PRESENCE_OFFLINE_MARKER,
    )


def panel_usabilidad(desde_str: str | None = None, hasta_str: str | None = None) -> dict:
    desde = _parse_fecha(desde_str)
    hasta = _parse_fecha(hasta_str)
    return {
        "sus": agregar_sus(),
        "ops": kpis_operativos(desde, hasta),
        "filtro_desde": desde_str or "",
        "filtro_hasta": hasta_str or "",
    }
