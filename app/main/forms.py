from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, RadioField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.constants import SUS_LIKERT_CHOICES, SUS_QUESTIONS
from app.validators import fecha_mantenimiento_coherente, fecha_solicitud_rango


class SolicitudUsuarioForm(FlaskForm):
    numero_inventario = SelectField(
        "Equipo (inventario de su área)",
        coerce=str,
        validators=[DataRequired(message="Seleccione el equipo de la lista.")],
    )
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
        render_kw={"rows": 4, "placeholder": "Describa el problema o el trabajo requerido…"},
    )
    enviar = SubmitField("Enviar solicitud")


class RespuestaAprobacionForm(FlaskForm):
    decision = RadioField(
        "Su respuesta",
        choices=[("aprobada", "Aprobar mantenimiento"), ("denegada", "Denegar solicitud")],
        validators=[DataRequired(message="Seleccione aprobar o denegar.")],
    )
    fecha_mantenimiento = DateField(
        "Fecha en la que puede recibir el mantenimiento",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    comentario = TextAreaField(
        "Comentario (opcional)",
        validators=[Optional(), Length(max=2000)],
        render_kw={"rows": 3, "placeholder": "Indique disponibilidad u observaciones…"},
    )
    enviar = SubmitField("Enviar respuesta")


class UsabilidadSusForm(FlaskForm):
    """Encuesta SUS: 10 ítems Likert 1–5."""

    q1 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q2 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q3 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q4 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q5 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q6 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q7 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q8 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q9 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    q10 = RadioField(validators=[DataRequired(message="Responda esta pregunta.")], choices=SUS_LIKERT_CHOICES)
    enviar = SubmitField("Enviar encuesta")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, label in SUS_QUESTIONS:
            getattr(self, field_name).label.text = label
