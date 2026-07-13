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
