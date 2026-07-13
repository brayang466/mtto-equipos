from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app.constants import AREAS_LABORALES, ESTADOS_SOLICITUD_CHOICES, ROLE_SUPERADMIN, ROLE_USER
from app.validators import corporate_email, fecha_mantenimiento_coherente, fecha_solicitud_rango, password_policy, username_format


def _strip_lower_email(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower() or None


def _strip_opt(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _coerce_select_int(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


class EquipoEditForm(FlaskForm):
    """Solo asignación organizativa: departamento, área, cargo y usuario."""

    departamento = StringField("Departamento", filters=[_strip_opt], validators=[Optional(), Length(max=255)])
    area = SelectField(
        "Área (inventario)",
        coerce=str,
        validators=[DataRequired(message="Seleccione el área del equipo.")],
    )
    cargo = StringField("Cargo", filters=[_strip_opt], validators=[Optional(), Length(max=255)])
    usuario = StringField("Usuario asignado", filters=[_strip_opt], validators=[Optional(), Length(max=512)])
    guardar = SubmitField("Guardar cambios")


class EliminarEquipoForm(FlaskForm):
    confirmar = BooleanField(
        "Confirmo eliminar este equipo del inventario (incluye sus solicitudes de mantenimiento)",
        validators=[DataRequired(message="Debe marcar la casilla de confirmación.")],
    )
    eliminar = SubmitField("Eliminar equipo del inventario")


class Mtto2026Form(FlaskForm):
    mtto_realizado_1s_2026 = BooleanField("Mantenimiento realizado — 1.er semestre 2026")
    mtto_realizado_2s_2026 = BooleanField("Mantenimiento realizado — 2.do semestre 2026")
    guardar = SubmitField("Guardar cambios")


class SolicitudMantenimientoForm(FlaskForm):
    fecha_solicitud = DateField(
        "Fecha de solicitud",
        validators=[DataRequired(message="Indique la fecha de solicitud."), fecha_solicitud_rango],
        format="%Y-%m-%d",
    )
    fecha_mantenimiento = DateField(
        "Fecha prevista para el mantenimiento",
        validators=[Optional(), fecha_mantenimiento_coherente],
        format="%Y-%m-%d",
    )
    observaciones = TextAreaField(
        "Observaciones",
        validators=[Optional(), Length(max=8000, message="Las observaciones superan el máximo permitido.")],
        render_kw={"rows": 4, "placeholder": "Describa el estado del equipo o el trabajo requerido…"},
    )
    enviar = SubmitField("Registrar solicitud")


class SolicitudTicForm(FlaskForm):
    usuario_aprobador_id = SelectField(
        "Usuario que debe aprobar",
        coerce=_coerce_select_int,
        validators=[DataRequired(message="Seleccione al usuario asignado al equipo.")],
    )
    fecha_solicitud = DateField(
        "Fecha de solicitud",
        validators=[DataRequired(message="Indique la fecha."), fecha_solicitud_rango],
        format="%Y-%m-%d",
    )
    fecha_mantenimiento = DateField(
        "Fecha propuesta de mantenimiento",
        validators=[Optional(), fecha_mantenimiento_coherente],
        format="%Y-%m-%d",
    )
    observaciones = TextAreaField(
        "Mensaje para el usuario",
        validators=[Optional(), Length(max=8000)],
        render_kw={"rows": 4, "placeholder": "Indique el motivo del mantenimiento preventivo…"},
    )
    enviar = SubmitField("Enviar solicitud al usuario")


class AdminUserCreateForm(FlaskForm):
    username = StringField(
        "Usuario",
        filters=[lambda v: (v or "").strip().lower() or None],
        validators=[
            DataRequired(message="Ingrese el usuario."),
            Length(min=3, max=80),
            username_format,
        ],
    )
    email = StringField(
        "Correo",
        filters=[_strip_lower_email],
        validators=[
            DataRequired(message="Ingrese el correo."),
            Email(message="Correo no válido."),
            Length(max=255),
            corporate_email,
        ],
    )
    area = SelectField(
        "Área",
        choices=[(a, a) for a in AREAS_LABORALES],
        validators=[DataRequired(message="Seleccione el área.")],
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
    crear = SubmitField("Crear usuario")


class AdminUserEditForm(FlaskForm):
    email = StringField(
        "Correo",
        filters=[_strip_lower_email],
        validators=[
            DataRequired(message="Ingrese el correo."),
            Email(message="Correo no válido."),
            Length(max=255),
            corporate_email,
        ],
    )
    area = SelectField(
        "Área",
        choices=[(a, a) for a in AREAS_LABORALES],
        validators=[DataRequired(message="Seleccione el área.")],
    )
    role = SelectField(
        "Rol",
        choices=[(ROLE_USER, "Usuario"), (ROLE_SUPERADMIN, "Superadmin (TIC)")],
        validators=[DataRequired()],
    )
    activo = BooleanField("Cuenta activa")
    nueva_password = PasswordField(
        "Nueva contraseña (opcional)",
        validators=[Optional(), password_policy(128)],
    )
    guardar = SubmitField("Guardar cambios")


class SolicitudAdminEditForm(FlaskForm):
    fecha_solicitud = DateField(
        "Fecha de solicitud",
        validators=[DataRequired(message="Indique la fecha de solicitud."), fecha_solicitud_rango],
        format="%Y-%m-%d",
    )
    fecha_mantenimiento = DateField(
        "Fecha de mantenimiento",
        validators=[Optional(), fecha_mantenimiento_coherente],
        format="%Y-%m-%d",
    )
    fecha_respuesta_usuario = DateField(
        "Fecha respuesta del usuario",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    estado = SelectField(
        "Estado",
        choices=ESTADOS_SOLICITUD_CHOICES,
        validators=[DataRequired()],
    )
    respuesta_usuario = SelectField(
        "Respuesta del usuario",
        choices=[("", "— Sin respuesta —"), ("aprobada", "Aprobada"), ("denegada", "Denegada")],
        validators=[Optional()],
    )
    observaciones = TextAreaField(
        "Observaciones / mensaje",
        validators=[Optional(), Length(max=8000)],
        render_kw={"rows": 4},
    )
    comentario_respuesta = TextAreaField(
        "Comentario de respuesta",
        validators=[Optional(), Length(max=8000)],
        render_kw={"rows": 3},
    )
    guardar = SubmitField("Guardar cambios")


class SolicitudEliminarForm(FlaskForm):
    confirmar = BooleanField(
        "Confirmo eliminar esta solicitud y sus evidencias adjuntas",
        validators=[DataRequired(message="Debe marcar la casilla de confirmación.")],
    )
    eliminar = SubmitField("Eliminar solicitud")
