"""Presencia de usuarios (última actividad) para panel lateral."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import request
from sqlalchemy import or_

from app.datetime_utils import format_ultimo_acceso, now_colombia_naive
from app.extensions import db
from app.models import User, UserPresence

PRESENCE_OFFLINE_MARKER = "__offline__"
PRESENCE_ONLINE_SECONDS = 25
PRESENCE_RECENT_OFFLINE_SECONDS = 1800


def _now() -> datetime:
    return now_colombia_naive()


def _user_is_online(presence: UserPresence | None) -> bool:
    if presence is None:
        return False
    if presence.pagina_actual == PRESENCE_OFFLINE_MARKER:
        return False
    cutoff = _now() - timedelta(seconds=PRESENCE_ONLINE_SECONDS)
    return presence.last_seen >= cutoff


def touch_presence(user_id: int) -> None:
    path = (request.path or "")[:255] if request else ""
    row = db.session.get(UserPresence, user_id)
    now = _now()
    if row is None:
        db.session.add(UserPresence(user_id=user_id, last_seen=now, pagina_actual=path or None))
    else:
        row.last_seen = now
        row.pagina_actual = path or None
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def mark_user_offline(user_id: int) -> None:
    """Marca al usuario como desconectado de inmediato."""
    row = db.session.get(UserPresence, user_id)
    now = _now()
    if row is None:
        db.session.add(
            UserPresence(
                user_id=user_id,
                last_seen=now,
                pagina_actual=PRESENCE_OFFLINE_MARKER,
            )
        )
    else:
        row.last_seen = now
        row.pagina_actual = PRESENCE_OFFLINE_MARKER
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _is_online_filter():
    return or_(
        UserPresence.pagina_actual.is_(None),
        UserPresence.pagina_actual != PRESENCE_OFFLINE_MARKER,
    )


def list_online_users(limit: int = 30) -> list[UserPresence]:
    cutoff = _now() - timedelta(seconds=PRESENCE_ONLINE_SECONDS)
    return (
        UserPresence.query.filter(UserPresence.last_seen >= cutoff)
        .filter(_is_online_filter())
        .join(User)
        .filter(User.activo.is_(True))
        .order_by(UserPresence.last_seen.desc())
        .limit(limit)
        .all()
    )


def list_recent_offline_users(limit: int = 20) -> list[UserPresence]:
    """Usuarios que ya no están en línea pero tuvieron actividad reciente."""
    now = _now()
    online_cutoff = now - timedelta(seconds=PRESENCE_ONLINE_SECONDS)
    offline_cutoff = now - timedelta(seconds=PRESENCE_RECENT_OFFLINE_SECONDS)
    return (
        UserPresence.query.filter(UserPresence.last_seen >= offline_cutoff)
        .filter(
            or_(
                UserPresence.pagina_actual == PRESENCE_OFFLINE_MARKER,
                UserPresence.last_seen < online_cutoff,
            )
        )
        .join(User)
        .filter(User.activo.is_(True))
        .order_by(UserPresence.last_seen.desc())
        .limit(limit)
        .all()
    )


def presence_user_dict(p: UserPresence, *, online: bool) -> dict:
    return {
        "id": p.user_id,
        "username": p.usuario.username,
        "area": (p.usuario.area or "").strip() or "Sin área",
        "online": online,
        "ultimo_acceso": None if online else format_ultimo_acceso(p.last_seen),
        "last_seen": p.last_seen.isoformat() if p.last_seen else None,
    }


def all_portal_users_payload() -> tuple[list[dict], int]:
    """Todos los usuarios activos del portal con estado de conexión."""
    users = User.query.filter(User.activo.is_(True)).order_by(User.area.asc(), User.username.asc()).all()
    if not users:
        return [], 0

    user_ids = [u.id for u in users]
    pres_rows = UserPresence.query.filter(UserPresence.user_id.in_(user_ids)).all()
    pres_by_id = {p.user_id: p for p in pres_rows}

    payload: list[dict] = []
    online_count = 0
    for u in users:
        p = pres_by_id.get(u.id)
        online = _user_is_online(p)
        if online:
            online_count += 1
        payload.append(
            {
                "id": u.id,
                "username": u.username,
                "area": (u.area or "").strip() or "Sin área",
                "online": online,
                "ultimo_acceso": None if online else format_ultimo_acceso(p.last_seen if p else None),
            }
        )

    payload.sort(key=lambda x: (x["area"].lower(), 0 if x["online"] else 1, x["username"].lower()))
    return payload, online_count


def count_pending_approvals(user_id: int) -> int:
    from app.constants import ESTADO_SOL_PENDIENTE_APROBACION
    from app.models import SolicitudMantenimiento

    return (
        SolicitudMantenimiento.query.filter_by(
            usuario_aprobador_id=user_id,
            estado=ESTADO_SOL_PENDIENTE_APROBACION,
        ).count()
    )
