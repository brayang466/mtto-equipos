"""Constantes de dominio (áreas laborales, roles)."""

AREAS_LABORALES: tuple[str, ...] = (
    "ADMINISTRACIÓN",
    "CONTABILIDAD",
    "COMPRAS",
    "TESORERIA",
    "PLANILLAJE",
    "COMERCIAL",
    "TIC",
    "CALIDAD",
    "OPERACIONES",
    "DESPOSTE",
    "SST",
    "CALIDAD DESPOSTE",
)

ROLE_USER = "user"
ROLE_SUPERADMIN = "superadmin"

ESTADO_SOL_PENDIENTE = "pendiente"
ESTADO_SOL_ATENDIDA = "atendida"
ESTADO_SOL_PENDIENTE_APROBACION = "pendiente_aprobacion"
ESTADO_SOL_APROBADA = "aprobada"
ESTADO_SOL_DENEGADA = "denegada"

TIPO_ORIGEN_USUARIO = "usuario"
TIPO_ORIGEN_TIC = "tic"

RESPUESTA_APROBADA = "aprobada"
RESPUESTA_DENEGADA = "denegada"

CHAT_TIPO_AREA = "area"
CHAT_TIPO_SUSURRO = "susurro"

ESTADOS_SOLICITUD_CHOICES: tuple[tuple[str, str], ...] = (
    (ESTADO_SOL_PENDIENTE, "Pendiente"),
    (ESTADO_SOL_PENDIENTE_APROBACION, "Pendiente aprobación"),
    (ESTADO_SOL_APROBADA, "Aprobada"),
    (ESTADO_SOL_DENEGADA, "Denegada"),
    (ESTADO_SOL_ATENDIDA, "Atendida"),
)

# Preguntas SUS (System Usability Scale) — Likert 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo)
SUS_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("q1", "Me gustaría usar este sistema con frecuencia."),
    ("q2", "El sistema me parece innecesariamente complicado."),
    ("q3", "El sistema me pareció fácil de usar."),
    ("q4", "Creo que necesitaría ayuda de alguien de sistemas para usarlo."),
    ("q5", "Las funciones del sistema están bien organizadas entre sí."),
    ("q6", "Hay demasiadas inconsistencias en este sistema."),
    ("q7", "La mayoría de las personas aprendería a usarlo rápidamente."),
    ("q8", "Me resultó engorroso usar el sistema."),
    ("q9", "Me sentí seguro/a al usarlo."),
    ("q10", "Tuve que aprender muchas cosas antes de poder manejarlo."),
)

SUS_LIKERT_CHOICES: tuple[tuple[str, str], ...] = (
    ("1", "1 — No estoy de acuerdo"),
    ("2", "2 — Poco de acuerdo"),
    ("3", "3 — Ni de acuerdo ni en desacuerdo"),
    ("4", "4 — De acuerdo"),
    ("5", "5 — Muy de acuerdo"),
)
