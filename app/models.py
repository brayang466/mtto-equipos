from __future__ import annotations

from sqlalchemy import func

from app.extensions import db


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

    def __repr__(self) -> str:
        return f"<Equipo {self.numero_inventario}>"
