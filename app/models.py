from __future__ import annotations

from flask_login import UserMixin
from sqlalchemy import func

from app.constants import ESTADO_SOL_PENDIENTE, ROLE_SUPERADMIN, TIPO_ORIGEN_USUARIO
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.now())

    solicitudes_registradas = db.relationship(
        "SolicitudMantenimiento",
        back_populates="registrado_por",
        foreign_keys="SolicitudMantenimiento.registrado_por_user_id",
    )
    solicitudes_por_aprobar = db.relationship(
        "SolicitudMantenimiento",
        back_populates="usuario_aprobador",
        foreign_keys="SolicitudMantenimiento.usuario_aprobador_id",
    )
    presencia = db.relationship("UserPresence", back_populates="usuario", uselist=False)
    encuesta_usabilidad = db.relationship(
        "UsabilidadEncuesta",
        back_populates="usuario",
        uselist=False,
    )

    def is_superadmin(self) -> bool:
        return self.role == ROLE_SUPERADMIN and self.activo

    @property
    def is_active(self) -> bool:  # Flask-Login
        return bool(self.activo)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Equipo(db.Model):
    __tablename__ = "equipos"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    numero_inventario = db.Column(db.String(32), nullable=False, unique=True)
    numero_contable = db.Column(db.String(64))
    codigo_contable = db.Column(db.String(64))
    departamento = db.Column(db.String(255))
    area = db.Column(db.String(255))
    usuario = db.Column(db.String(512))
    cargo = db.Column(db.String(255))
    descripcion = db.Column(db.String(255))
    marca_referencia = db.Column(db.String(512))
    service_tag = db.Column(db.String(255))
    serial_cpu = db.Column(db.String(255))
    fecha_adquisicion = db.Column(db.Date)
    observaciones = db.Column(db.Text)
    mtto_realizado_1s_2026 = db.Column(db.Boolean, nullable=False, default=False)
    mtto_realizado_2s_2026 = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.now())
    actualizado_en = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    solicitudes_mantenimiento = db.relationship(
        "SolicitudMantenimiento",
        back_populates="equipo",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Equipo {self.numero_inventario}>"


class SolicitudMantenimiento(db.Model):
    __tablename__ = "solicitudes_mantenimiento"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    equipo_id = db.Column(
        db.BigInteger,
        db.ForeignKey("equipos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registrado_por_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo_origen = db.Column(db.String(20), nullable=False, default=TIPO_ORIGEN_USUARIO)
    usuario_aprobador_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fecha_solicitud = db.Column(db.Date, nullable=False)
    fecha_mantenimiento = db.Column(db.Date, nullable=True)
    fecha_respuesta_usuario = db.Column(db.Date, nullable=True)
    respuesta_usuario = db.Column(db.String(20), nullable=True)
    comentario_respuesta = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(20), nullable=False, default=ESTADO_SOL_PENDIENTE)
    atendido_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.now())

    equipo = db.relationship("Equipo", back_populates="solicitudes_mantenimiento")
    registrado_por = db.relationship(
        "User",
        back_populates="solicitudes_registradas",
        foreign_keys=[registrado_por_user_id],
    )
    usuario_aprobador = db.relationship(
        "User",
        back_populates="solicitudes_por_aprobar",
        foreign_keys=[usuario_aprobador_id],
    )
    adjuntos = db.relationship(
        "SolicitudAdjunto",
        back_populates="solicitud",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SolicitudMantenimiento {self.id} equipo={self.equipo_id}>"


class SolicitudAdjunto(db.Model):
    __tablename__ = "solicitudes_adjuntos"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    solicitud_id = db.Column(
        db.BigInteger,
        db.ForeignKey("solicitudes_mantenimiento.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre_archivo = db.Column(db.String(255), nullable=False)
    nombre_original = db.Column(db.String(512), nullable=False)
    mime = db.Column(db.String(128))
    tamano_bytes = db.Column(db.BigInteger)

    solicitud = db.relationship("SolicitudMantenimiento", back_populates="adjuntos")

    def __repr__(self) -> str:
        return f"<SolicitudAdjunto {self.id}>"


class UserPresence(db.Model):
    __tablename__ = "presencia_usuarios"

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_seen = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    pagina_actual = db.Column(db.String(255))

    usuario = db.relationship("User", back_populates="presencia")

    def __repr__(self) -> str:
        return f"<UserPresence user={self.user_id}>"


class ChatMensaje(db.Model):
    __tablename__ = "chat_mensajes"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    texto = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="area")
    area = db.Column(db.String(64), nullable=True)
    destinatario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.now())

    autor = db.relationship("User", foreign_keys=[user_id])
    destinatario = db.relationship("User", foreign_keys=[destinatario_id])

    def __repr__(self) -> str:
        return f"<ChatMensaje {self.id}>"


class UsabilidadEncuesta(db.Model):
    """Respuesta SUS (System Usability Scale) por usuario."""

    __tablename__ = "usabilidad_encuestas"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    q1 = db.Column(db.SmallInteger, nullable=False)
    q2 = db.Column(db.SmallInteger, nullable=False)
    q3 = db.Column(db.SmallInteger, nullable=False)
    q4 = db.Column(db.SmallInteger, nullable=False)
    q5 = db.Column(db.SmallInteger, nullable=False)
    q6 = db.Column(db.SmallInteger, nullable=False)
    q7 = db.Column(db.SmallInteger, nullable=False)
    q8 = db.Column(db.SmallInteger, nullable=False)
    q9 = db.Column(db.SmallInteger, nullable=False)
    q10 = db.Column(db.SmallInteger, nullable=False)
    score = db.Column(db.Numeric(5, 2), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.now())
    actualizado_en = db.Column(
        db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    usuario = db.relationship("User", back_populates="encuesta_usabilidad")

    def __repr__(self) -> str:
        return f"<UsabilidadEncuesta user={self.user_id} score={self.score}>"
