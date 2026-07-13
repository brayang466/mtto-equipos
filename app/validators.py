"""
Validadores reutilizables (registro, solicitudes, fechas).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from flask_wtf import FlaskForm
from wtforms.validators import ValidationError

_USERNAME_RE = re.compile(r"^[a-zñáéíóúü]+(\.[a-zñáéíóúü]+)+$", re.IGNORECASE)
_WEAK_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "12345678",
        "qwerty12",
        "colbeef1",
        "pricetag1",
    }
)


def password_policy(max_len: int = 128) -> callable:
    """Devuelve validador WTForms para contraseña corporativa."""

    def _validate(form: FlaskForm, field) -> None:
        pw = field.data or ""
        if len(pw) < 8:
            raise ValidationError("Mínimo 8 caracteres.")
        if len(pw) > max_len:
            raise ValidationError(f"Máximo {max_len} caracteres.")
        if not re.search(r"[A-ZÁÉÍÓÚÑ]", pw):
            raise ValidationError("Debe incluir al menos una letra mayúscula.")
        if not re.search(r"[^\w\s]", pw):
            raise ValidationError("Debe incluir al menos un símbolo (por ejemplo * # ! ? _).")
        if re.search(r"\s", pw):
            raise ValidationError("No use espacios en la contraseña.")
        if pw.lower() in _WEAK_PASSWORDS:
            raise ValidationError("Elija una contraseña menos predecible.")

    return _validate


def username_format(form: FlaskForm, field) -> None:
    v = (field.data or "").strip().lower()
    if not v:
        return
    if not _USERNAME_RE.match(v):
        raise ValidationError("Use el formato nombre.apellido (solo letras y un punto, sin espacios).")


def corporate_email(form: FlaskForm, field) -> None:
    e = (field.data or "").strip().lower()
    if not e:
        return
    if "@" not in e or e.count("@") != 1:
        raise ValidationError("El correo no es válido.")
    local, _, domain = e.partition("@")
    if len(local) < 2:
        raise ValidationError("El correo no es válido.")
    if not e.endswith("@colbeef.com"):
        raise ValidationError("Debe registrar su correo corporativo terminado en @colbeef.com.")


def numero_inventario_format(form: FlaskForm, field) -> None:
    raw = (field.data or "").strip()
    if not raw:
        return
    compact = re.sub(r"\s+", "", raw)
    if len(compact) > 32:
        raise ValidationError("Máximo 32 caracteres (sin contar espacios extra).")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9\-./]{0,30}[A-Za-z0-9]$|^[A-Za-z0-9]{1,32}$", compact):
        raise ValidationError("Use solo letras, números, guiones o puntos (sin caracteres especiales raros).")


def fecha_solicitud_rango(form: FlaskForm, field) -> None:
    """La solicitud no puede quedar en el futuro lejano ni demasiado en el pasado."""
    if not field.data:
        return
    today = date.today()
    if field.data > today:
        raise ValidationError("La fecha de solicitud no puede ser futura.")
    limite = today - timedelta(days=365)
    if field.data < limite:
        raise ValidationError("La fecha de solicitud es demasiado antigua (máximo 1 año atrás).")
def fecha_mantenimiento_coherente(form: FlaskForm, field) -> None:
    """Si hay fecha de mantenimiento, no debe ser anterior a la fecha de solicitud."""
    if not field.data:
        return
    fs = form.fecha_solicitud.data
    if fs and field.data < fs:
        raise ValidationError("La fecha prevista de mantenimiento no puede ser anterior a la fecha de solicitud.")


def flash_form_errors(form: FlaskForm, category: str = "warning", max_items: int = 6) -> None:
    """Muestra un resumen en flash cuando validate_on_submit falla."""
    from flask import flash

    if not form.errors:
        return
    msgs: list[str] = []
    for _fname, errs in form.errors.items():
        msgs.extend(str(e) for e in errs)
    text = " · ".join(msgs[:max_items])
    if len(msgs) > max_items:
        text += " …"
    flash(f"Revise el formulario: {text}", category)
