"""Fechas y horas en zona horaria de Colombia (America/Bogota, UTC-5 sin DST)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo

    TZ_COLOMBIA = ZoneInfo("America/Bogota")
except Exception:
    TZ_COLOMBIA = timezone(timedelta(hours=-5))


def now_colombia() -> datetime:
    return datetime.now(TZ_COLOMBIA)


def now_colombia_naive() -> datetime:
    """Hora actual Colombia sin tzinfo (compatible con columnas DATETIME de MySQL)."""
    return now_colombia().replace(tzinfo=None)


def as_colombia(dt: datetime | None) -> datetime | None:
    """Interpreta un datetime de BD como hora Colombia y devuelve aware en Bogotá."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ_COLOMBIA)
    return dt.astimezone(TZ_COLOMBIA)


def format_chat_datetime(dt: datetime | None) -> str:
    loc = as_colombia(dt)
    if not loc:
        return ""
    return loc.strftime("%d/%m %H:%M")


def format_ultimo_acceso(dt: datetime | None) -> str:
    """Hora de última conexión (solo para usuarios desconectados)."""
    if dt is None:
        return "Sin conexión"
    loc = as_colombia(dt)
    now = now_colombia()
    if loc.date() == now.date():
        return loc.strftime("%H:%M")
    return loc.strftime("%d/%m %H:%M")
