from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app.constants import AREAS_LABORALES
from app.validators import corporate_email, password_policy, username_format


def _strip_lower_email(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower() or None


def _strip_inventario(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class LoginForm(FlaskForm):
    username = StringField(
        "Usuario",
        filters=[lambda v: (v or "").strip().lower() or None],
        validators=[
            DataRequired(message="Ingrese su usuario."),
            Length(min=3, max=80, message="El usuario debe tener entre 3 y 80 caracteres."),
            username_format,
        ],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="Ingrese su contraseña."), Length(max=128, message="Contraseña demasiado larga.")],
    )
    submit = SubmitField("Entrar")


class RegisterForm(FlaskForm):
    username = StringField(
        "Usuario (nombre.apellido)",
        filters=[lambda v: (v or "").strip().lower() or None],
        validators=[
            DataRequired(message="Ingrese un usuario."),
            Length(min=3, max=80, message="Entre 3 y 80 caracteres."),
            username_format,
        ],
    )
    email = StringField(
        "Correo corporativo",
        filters=[_strip_lower_email],
        validators=[
            DataRequired(message="Ingrese su correo."),
            Email(message="Formato de correo no válido."),
            Length(max=255, message="Correo demasiado largo."),
            corporate_email,
        ],
    )
    area = SelectField(
        "Área",
        choices=[("", "Seleccione…")] + [(a, a) for a in AREAS_LABORALES],
        validators=[DataRequired(message="Seleccione un área.")],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="Ingrese una contraseña."), password_policy(128)],
    )
    password2 = PasswordField(
        "Confirmar contraseña",
        validators=[
            DataRequired(message="Confirme la contraseña."),
            EqualTo("password", message="Las contraseñas no coinciden."),
        ],
    )
    submit = SubmitField("Crear cuenta")


class ForgotPasswordForm(FlaskForm):
    username = StringField(
        "Usuario",
        filters=[lambda v: (v or "").strip().lower() or None],
        validators=[
            DataRequired(message="Ingrese su usuario."),
            Length(min=3, max=80, message="Entre 3 y 80 caracteres."),
            username_format,
        ],
    )
    email = StringField(
        "Correo corporativo",
        filters=[_strip_lower_email],
        validators=[
            DataRequired(message="Ingrese el correo de su cuenta."),
            Email(message="Formato de correo no válido."),
            Length(max=255),
            corporate_email,
        ],
    )
    submit = SubmitField("Enviar enlace de recuperación")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "Nueva contraseña",
        validators=[DataRequired(message="Ingrese la nueva contraseña."), password_policy(128)],
    )
    password2 = PasswordField(
        "Confirmar contraseña",
        validators=[
            DataRequired(message="Confirme la contraseña."),
            EqualTo("password", message="Las contraseñas no coinciden."),
        ],
    )
    submit = SubmitField("Guardar contraseña")
