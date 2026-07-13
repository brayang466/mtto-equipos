"""Chat interno del equipo (por área y susurros entre usuarios)."""
from __future__ import annotations

from sqlalchemy import and_, or_

from app.constants import CHAT_TIPO_AREA, CHAT_TIPO_SUSURRO
from app.datetime_utils import format_chat_datetime
from app.extensions import db
from app.models import ChatMensaje, User

CHAT_HISTORY_LIMIT = 80
CHAT_POLL_MESSAGES_LIMIT = 40


def normalizar_area(area: str | None) -> str:
    return (area or "").strip() or "Sin área"


def _base_query(user_id: int, area: str, modo: str, peer_id: int | None):
    if modo == CHAT_TIPO_SUSURRO and peer_id:
        return ChatMensaje.query.filter(
            ChatMensaje.tipo == CHAT_TIPO_SUSURRO,
            or_(
                and_(ChatMensaje.user_id == user_id, ChatMensaje.destinatario_id == peer_id),
                and_(ChatMensaje.user_id == peer_id, ChatMensaje.destinatario_id == user_id),
            ),
        )
    return ChatMensaje.query.filter(
        ChatMensaje.tipo == CHAT_TIPO_AREA,
        ChatMensaje.area == normalizar_area(area),
    )


def crear_mensaje_area(user_id: int, area: str, texto: str) -> ChatMensaje:
    msg = ChatMensaje(
        user_id=user_id,
        texto=texto[:500],
        tipo=CHAT_TIPO_AREA,
        area=normalizar_area(area),
    )
    db.session.add(msg)
    db.session.commit()
    db.session.refresh(msg)
    return msg


def crear_mensaje_susurro(user_id: int, destinatario_id: int, texto: str) -> ChatMensaje | None:
    if destinatario_id == user_id:
        return None
    dest = db.session.get(User, destinatario_id)
    if dest is None or not dest.activo:
        return None
    msg = ChatMensaje(
        user_id=user_id,
        texto=texto[:500],
        tipo=CHAT_TIPO_SUSURRO,
        destinatario_id=destinatario_id,
    )
    db.session.add(msg)
    db.session.commit()
    db.session.refresh(msg)
    return msg


def mensajes_desde(user_id: int, area: str, modo: str, peer_id: int | None, msg_id: int) -> list[ChatMensaje]:
    if modo == CHAT_TIPO_SUSURRO and not peer_id:
        return []
    return (
        _base_query(user_id, area, modo, peer_id)
        .filter(ChatMensaje.id > msg_id)
        .order_by(ChatMensaje.id.asc())
        .limit(CHAT_POLL_MESSAGES_LIMIT)
        .all()
    )


def historial_reciente(user_id: int, area: str, modo: str, peer_id: int | None) -> list[ChatMensaje]:
    if modo == CHAT_TIPO_SUSURRO and not peer_id:
        return []
    return (
        _base_query(user_id, area, modo, peer_id)
        .order_by(ChatMensaje.id.desc())
        .limit(CHAT_HISTORY_LIMIT)
        .all()[::-1]
    )


def portal_usuarios_chat_payload() -> tuple[list[dict], int]:
    from app.presence_service import all_portal_users_payload

    return all_portal_users_payload()


def mensaje_a_dict(m: ChatMensaje, current_user_id: int) -> dict:
    peer_name = None
    if m.tipo == CHAT_TIPO_SUSURRO:
        if m.user_id == current_user_id and m.destinatario:
            peer_name = m.destinatario.username
        elif m.autor:
            peer_name = m.autor.username
    return {
        "id": m.id,
        "user_id": m.user_id,
        "username": m.autor.username if m.autor else "?",
        "texto": m.texto,
        "tipo": m.tipo,
        "area": m.area,
        "destinatario_id": m.destinatario_id,
        "peer_username": peer_name,
        "creado_en": format_chat_datetime(m.creado_en),
        "mine": m.user_id == current_user_id,
    }
