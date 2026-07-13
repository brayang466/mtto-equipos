"""Exportación de solicitudes y evidencias para superadmin."""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, datetime
from pathlib import Path

from flask import Response, current_app

from app.models import SolicitudAdjunto, SolicitudMantenimiento


def _parse_fecha(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def solicitudes_en_rango(desde: date | None, hasta: date | None) -> list[SolicitudMantenimiento]:
    q = SolicitudMantenimiento.query.join(SolicitudMantenimiento.equipo)
    if desde:
        q = q.filter(SolicitudMantenimiento.fecha_solicitud >= desde)
    if hasta:
        q = q.filter(SolicitudMantenimiento.fecha_solicitud <= hasta)
    return q.order_by(
        SolicitudMantenimiento.fecha_solicitud.asc(),
        SolicitudMantenimiento.id.asc(),
    ).all()


def respuesta_legible(val: str | None) -> str:
    if val == "aprobada":
        return "Aprobada"
    if val == "denegada":
        return "Denegada"
    return "—"


def generar_csv_solicitudes(desde: date | None, hasta: date | None) -> Response:
    rows = solicitudes_en_rango(desde, hasta)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Fecha solicitud",
            "ID",
            "Inventario",
            "N.º contable",
            "Departamento",
            "Área equipo",
            "Usuario equipo",
            "Registrado por",
            "Área registrador",
            "Origen",
            "Estado",
            "Fecha mantenimiento",
            "Respuesta usuario",
            "Comentario respuesta",
            "Observaciones",
            "Adjuntos",
            "Nombres archivos",
            "Registrado en sistema",
        ]
    )
    for s in rows:
        eq = s.equipo
        reg = s.registrado_por
        adjuntos = list(s.adjuntos)
        writer.writerow(
            [
                s.fecha_solicitud.strftime("%d/%m/%Y") if s.fecha_solicitud else "",
                s.id,
                eq.numero_inventario if eq else "",
                eq.numero_contable if eq else "",
                eq.departamento if eq else "",
                eq.area if eq else "",
                eq.usuario if eq else "",
                reg.username if reg else "",
                reg.area if reg else "",
                s.tipo_origen or "",
                s.estado or "",
                s.fecha_mantenimiento.strftime("%d/%m/%Y") if s.fecha_mantenimiento else "",
                respuesta_legible(s.respuesta_usuario),
                (s.comentario_respuesta or "").replace("\n", " ").strip(),
                (s.observaciones or "").replace("\n", " ").strip(),
                len(adjuntos),
                "; ".join(a.nombre_original for a in adjuntos),
                s.creado_en.strftime("%d/%m/%Y %H:%M") if s.creado_en else "",
            ]
        )
    nombre = f"solicitudes_{desde or 'inicio'}_{hasta or 'hoy'}.csv"
    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


def generar_zip_evidencias(desde: date | None, hasta: date | None) -> Response | tuple[None, str]:
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    rows = solicitudes_en_rango(desde, hasta)
    buf = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for s in rows:
            if not s.fecha_solicitud:
                continue
            fecha_carpeta = s.fecha_solicitud.strftime("%Y-%m-%d")
            inv = s.equipo.numero_inventario if s.equipo else str(s.equipo_id)
            carpeta = f"{fecha_carpeta}/solicitud_{s.id}_inv_{inv}"
            for adj in s.adjuntos:
                path = (upload_root / adj.nombre_archivo).resolve()
                try:
                    path.relative_to(upload_root)
                except ValueError:
                    continue
                if not path.is_file():
                    continue
                arcname = f"{carpeta}/{adj.nombre_original}"
                zf.write(path, arcname=arcname)
                added += 1
    if added == 0:
        return None, "No hay evidencias en el rango de fechas indicado."
    buf.seek(0)
    nombre = f"evidencias_{desde or 'inicio'}_{hasta or 'hoy'}.zip"
    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    ), None


def parse_rango_export() -> tuple[date | None, date | None]:
    from flask import request

    return _parse_fecha(request.args.get("desde")), _parse_fecha(request.args.get("hasta"))
