from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField


class Mtto2026Form(FlaskForm):
    mtto_realizado_1s_2026 = BooleanField("Mantenimiento realizado — 1.er semestre 2026")
    mtto_realizado_2s_2026 = BooleanField("Mantenimiento realizado — 2.do semestre 2026")
    guardar = SubmitField("Guardar cambios")
