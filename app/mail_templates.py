"""
Plantillas HTML para correos (multipart: texto plano + HTML con estilos en línea).
"""
from __future__ import annotations

from datetime import date, datetime
from html import escape

from app.models import SolicitudMantenimiento


def _subject_solicitud(accion: str, solicitud_id: int, inv: str | int) -> str:
    """Asunto uniforme: contexto · número de solicitud · inventario."""
    return f"[Mtto equipos] Solicitud #{solicitud_id} · {accion} · inv. {inv}"
def _fmt_date(d: date | None) -> str:
    if d is None:
        return "—"
    return d.strftime("%d/%m/%Y")


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M")


def _estado_legible(estado: str | None) -> str:
    if estado == "pendiente":
        return "Pendiente de atención por TIC"
    if estado == "pendiente_aprobacion":
        return "Pendiente de aprobación del usuario"
    if estado == "aprobada":
        return "Aprobada por el usuario"
    if estado == "denegada":
        return "Denegada por el usuario"
    if estado == "atendida":
        return "Atendida"
    return escape(estado or "—")


def _wrap_html(title: str, inner_html: str, footer_note: str | None = None) -> str:
    foot = (
        f'<p style="margin:20px 0 0;font-size:12px;color:#64748b;line-height:1.5;">{footer_note}</p>'
        if footer_note
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0b1220;font-family:Segoe UI,system-ui,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:linear-gradient(165deg,#0b1220 0%,#0f172a 100%);padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" style="max-width:560px;background:rgba(30,41,59,0.95);border-radius:16px;border:1px solid rgba(56,189,248,0.35);overflow:hidden;box-shadow:0 20px 50px rgba(2,6,23,0.5);">
<tr><td style="background:linear-gradient(90deg,#0ea5e9,#6366f1);padding:14px 22px;">
<p style="margin:0;font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.9);">Mtto equipos</p>
<h1 style="margin:6px 0 0;font-size:18px;font-weight:800;color:#fff;line-height:1.25;">{escape(title)}</h1>
</td></tr>
<tr><td style="padding:22px 22px 8px;color:#e2e8f0;font-size:15px;line-height:1.55;">
{inner_html}
{foot}
</td></tr>
<tr><td style="padding:14px 22px 20px;border-top:1px solid rgba(148,163,184,0.2);">
<p style="margin:0;font-size:11px;color:#64748b;">Colbeef · Sistema interno de mantenimiento de equipos de cómputo.<br>
Este mensaje se generó automáticamente; no utilice “Responder” salvo que su buzón esté configurado para ello.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _cta_button(href: str, label: str) -> str:
    h = escape(href, quote=True)
    return f"""<table role="presentation" cellspacing="0" cellpadding="0" style="margin:20px 0 0;">
<tr><td style="border-radius:12px;background:linear-gradient(135deg,#0ea5e9,#6366f1);">
<a href="{h}" style="display:inline-block;padding:12px 22px;font-size:14px;font-weight:800;color:#fff;text-decoration:none;border-radius:12px;">{escape(label)}</a>
</td></tr>
</table>"""


def _detail_row(label: str, value: str, *, value_is_html: bool = False) -> str:
    cell = value if value_is_html else escape(value)
    return f"""<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 10px;">
<tr><td style="width:42%;vertical-align:top;padding:6px 10px 6px 0;font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.04em;">{escape(label)}</td>
<td style="vertical-align:top;padding:6px 0;color:#f1f5f9;font-size:14px;font-weight:600;">{cell}</td></tr></table>"""


def solicitud_nueva_tic(
    solicitud: SolicitudMantenimiento,
    panel_url: str,
    equipo_detalle_url: str | None,
) -> tuple[str, str]:
    s = solicitud
    eq = s.equipo
    inv = eq.numero_inventario if eq else "?"
    reg = s.registrado_por
    if reg:
        reg_html = f"{escape(reg.username)} <span style=\"color:#94a3b8;font-weight:500;\">({escape(reg.email)})</span>"
        if getattr(reg, "area", None):
            reg_html += f"<br><span style=\"font-size:13px;color:#94a3b8;\">Área registrada: {escape(reg.area)}</span>"
    else:
        reg_html = "<span style=\"color:#94a3b8;\">Registrada desde el panel de administración (sin usuario de portal).</span>"

    dept = escape(eq.departamento) if eq and eq.departamento else "—"
    usuario_eq = escape(eq.usuario) if eq and eq.usuario else "—"
    desc = escape(eq.descripcion) if eq and eq.descripcion else "—"
    obs = escape(s.observaciones) if s.observaciones else "<span style=\"color:#94a3b8;font-style:italic;\">Sin texto adicional.</span>"
    n_adj = s.adjuntos.count()

    intro = (
        "<p style=\"margin:0 0 16px;\">Hay una <strong style=\"color:#7dd3fc;\">nueva solicitud de mantenimiento preventivo/correctivo</strong> "
        "registrada en el portal. Revise los datos y atienda según la prioridad del área.</p>"
    )

    rows = "".join(
        [
            _detail_row("ID solicitud", str(s.id)),
            _detail_row("N.º inventario", escape(inv)),
            _detail_row("Usuario del equipo (inventario)", usuario_eq),
            _detail_row("Departamento", dept),
            _detail_row("Descripción del bien", desc),
            _detail_row("Registrada por (portal)", reg_html, value_is_html=True),
            _detail_row("Estado", _estado_legible(s.estado), value_is_html=True),
            _detail_row("Fecha de solicitud", escape(_fmt_date(s.fecha_solicitud))),
            _detail_row("Fecha deseada de mantenimiento", escape(_fmt_date(s.fecha_mantenimiento))),
            _detail_row("Evidencias adjuntas", f"{n_adj} archivo(s) de imagen" if n_adj else "Sin archivos"),
        ]
    )

    obs_box = f"""<div style="margin:16px 0 0;padding:14px 16px;background:rgba(2,6,23,0.45);border-radius:12px;border:1px solid rgba(56,189,248,0.25);">
<p style="margin:0 0 8px;font-size:12px;font-weight:800;color:#38bdf8;text-transform:uppercase;">Detalle / observaciones del solicitante</p>
<p style="margin:0;white-space:pre-wrap;color:#e2e8f0;font-size:14px;">{obs}</p></div>"""

    actions = _cta_button(panel_url, "Abrir listado de solicitudes")
    if equipo_detalle_url:
        actions += _cta_button(equipo_detalle_url, "Ver ficha del equipo en inventario")

    inner = intro + rows + obs_box + actions

    plain = "\n".join(
        [
            "Nueva solicitud de mantenimiento (Mtto equipos)",
            "",
            f"ID solicitud: {s.id}",
            f"Inventario: {inv}",
            f"Departamento: {eq.departamento if eq else '—'}",
            f"Usuario del equipo: {eq.usuario if eq else '—'}",
            f"Descripción: {eq.descripcion if eq else '—'}",
            f"Registrada por: {reg.username if reg else '—'} ({reg.email if reg else ''})",
            f"Estado: {s.estado}",
            f"Fecha solicitud: {_fmt_date(s.fecha_solicitud)}",
            f"Fecha prevista mantenimiento: {_fmt_date(s.fecha_mantenimiento)}",
            f"Adjuntos: {n_adj}",
            "",
            f"Observaciones:\n{s.observaciones or '—'}",
            "",
            f"Panel solicitudes: {panel_url}",
        ]
        + ([f"Ficha equipo: {equipo_detalle_url}"] if equipo_detalle_url else [])
    )

    html = _wrap_html(
        "Nueva solicitud de mantenimiento",
        inner,
        "Use los botones desde la red interna. Si no ve estilos, abra el enlace en el navegador.",
    )
    return plain, html


def solicitud_confirmacion_usuario(solicitud: SolicitudMantenimiento, app_url: str) -> tuple[str, str]:
    s = solicitud
    eq = s.equipo
    inv = eq.numero_inventario if eq else "?"
    intro = (
        "<p style=\"margin:0 0 16px;\">Le confirmamos que su solicitud quedó <strong style=\"color:#6ee7b7;\">registrada correctamente</strong> "
        "en el sistema. El área de <strong>Tecnología</strong> ha recibido el mismo aviso con el detalle y las evidencias (si las envió).</p>"
    )
    rows = "".join(
        [
            _detail_row("ID de seguimiento", str(s.id)),
            _detail_row("Equipo (inventario)", escape(inv)),
            _detail_row("Fecha de solicitud", escape(_fmt_date(s.fecha_solicitud))),
            _detail_row("Fecha indicada para el mantenimiento", escape(_fmt_date(s.fecha_mantenimiento))),
            _detail_row("Archivos adjuntos", f"{s.adjuntos.count()} imagen(es)"),
        ]
    )
    next_steps = (
        '<p style="margin:18px 0 0;font-size:14px;color:#cbd5e1;">Cuando TIC marque la solicitud como '
        '<strong>atendida</strong>, recibirá otro correo en esta misma dirección. '
        "Mientras tanto puede consultar el estado con su área de sistemas.</p>"
    )

    inner = intro + rows + next_steps + _cta_button(app_url.rstrip("/") + "/", "Ir al portal — Mtto equipos")

    plain = "\n".join(
        [
            "Solicitud registrada correctamente.",
            "",
            f"ID de seguimiento: {s.id}",
            f"Inventario: {inv}",
            f"Fecha solicitud: {_fmt_date(s.fecha_solicitud)}",
            f"Fecha prevista mantenimiento: {_fmt_date(s.fecha_mantenimiento)}",
            "",
            "TIC ha sido notificado. Recibirá otro mensaje cuando la solicitud sea atendida.",
            f"Portal: {app_url}",
        ]
    )
    html = _wrap_html("Solicitud registrada", inner, None)
    return plain, html


def solicitud_pendiente_aprobacion_usuario(
    solicitud: SolicitudMantenimiento, aprobar_url: str
) -> tuple[str, str]:
    s = solicitud
    eq = s.equipo
    inv = eq.numero_inventario if eq else "?"
    intro = (
        "<p style=\"margin:0 0 16px;\">El área de <strong>Tecnología</strong> solicita su "
        "<strong>aprobación</strong> para realizar mantenimiento preventivo en el equipo asignado. "
        "Ingrese al portal para <strong>aprobar o denegar</strong> e indicar la fecha en que puede recibir el servicio.</p>"
    )
    rows = "".join(
        [
            _detail_row("Solicitud", str(s.id)),
            _detail_row("Inventario", escape(str(inv))),
            _detail_row("Descripción", escape((eq.descripcion if eq else None) or "—")),
            _detail_row("Fecha propuesta por TIC", escape(_fmt_date(s.fecha_mantenimiento))),
            _detail_row("Observaciones", escape((s.observaciones or "—")[:500])),
        ]
    )
    inner = intro + rows + _cta_button(aprobar_url, "Responder solicitud")

    plain = "\n".join(
        [
            f"Solicitud #{s.id} · Inventario {inv} · Requiere su aprobación",
            f"Fecha propuesta por TIC: {_fmt_date(s.fecha_mantenimiento)}",
            f"Responder en: {aprobar_url}",
        ]
    )
    html = _wrap_html("Aprobación de mantenimiento", inner, None)
    return plain, html


def solicitud_respuesta_aprobacion_tic(
    solicitud: SolicitudMantenimiento, panel_url: str
) -> tuple[str, str]:
    """Aviso a TIC cuando el usuario aprueba o deniega mantenimiento solicitado."""
    s = solicitud
    eq = s.equipo
    inv = eq.numero_inventario if eq else "?"
    aprobador = s.usuario_aprobador
    aprobador_txt = escape(aprobador.username) if aprobador else "—"
    aprobada = s.respuesta_usuario == "aprobada"
    fecha_usuario = s.fecha_respuesta_usuario or s.fecha_mantenimiento
    titulo = (
        "Usuario aprobó el mantenimiento"
        if aprobada
        else "Usuario denegó el mantenimiento"
    )
    color = "#6ee7b7" if aprobada else "#fca5a5"

    intro = (
        f"<p style=\"margin:0 0 16px;\">El usuario <strong>{aprobador_txt}</strong> "
        f"<strong style=\"color:{color};\">{'aprobó' if aprobada else 'denegó'}</strong> "
        f"la solicitud de mantenimiento <strong>#{s.id}</strong> del inventario <strong>{escape(str(inv))}</strong>.</p>"
    )

    fecha_label = (
        "Fecha acordada de mantenimiento"
        if aprobada
        else "Fecha indicada por el usuario (vigente hasta)"
    )

    rows = "".join(
        [
            _detail_row("ID solicitud", str(s.id)),
            _detail_row("N.º inventario", escape(str(inv))),
            _detail_row("N.º contable", escape((eq.numero_contable if eq else None) or "—")),
            _detail_row("Departamento", escape((eq.departamento if eq else None) or "—")),
            _detail_row("Área", escape((eq.area if eq else None) or "—")),
            _detail_row("Usuario asignado", escape((eq.usuario if eq else None) or "—")),
            _detail_row("Descripción", escape((eq.descripcion if eq else None) or "—")),
            _detail_row("Marca / referencia", escape((eq.marca_referencia if eq else None) or "—")),
            _detail_row("Service tag", escape((eq.service_tag if eq else None) or "—")),
            _detail_row("Decisión", "Aprobada" if aprobada else "Denegada"),
            _detail_row(fecha_label, escape(_fmt_date(fecha_usuario))),
            _detail_row("Comentario del usuario", escape((s.comentario_respuesta or "—")[:800])),
        ]
    )

    inner = intro + rows + _cta_button(panel_url, "Ver solicitudes en panel TIC")

    accion_plain = "Aprobada por el usuario" if aprobada else "Denegada por el usuario"
    plain_lines = [
        f"Solicitud #{s.id} · Inventario {inv} · {accion_plain}",
        "",
        f"Usuario: {aprobador.username if aprobador else '—'}",
        f"{fecha_label}: {_fmt_date(fecha_usuario)}",
        f"Comentario: {s.comentario_respuesta or '—'}",
        "",
        f"Panel: {panel_url}",
    ]
    html = _wrap_html(titulo, inner, None)
    return "\n".join(plain_lines), html


def solicitud_atendida_usuario(solicitud: SolicitudMantenimiento, app_url: str) -> tuple[str, str]:
    s = solicitud
    eq = s.equipo
    inv = eq.numero_inventario if eq else "?"
    intro = (
        "<p style=\"margin:0 0 16px;\">Su solicitud de mantenimiento fue marcada como "
        "<strong style=\"color:#6ee7b7;\">ATENDIDA</strong> en el sistema. Si el trabajo aún no se reflejó en su equipo, "
        "comuníquese con TIC citando el ID de solicitud.</p>"
    )
    rows = "".join(
        [
            _detail_row("ID solicitud", str(s.id)),
            _detail_row("Inventario", escape(str(inv))),
            _detail_row("Fecha de solicitud", escape(_fmt_date(s.fecha_solicitud))),
            _detail_row("Fecha/hora de cierre registrada", escape(_fmt_dt(s.atendido_en))),
        ]
    )
    inner = intro + rows + _cta_button(app_url.rstrip("/") + "/", "Abrir portal — nueva solicitud")

    plain = "\n".join(
        [
            "Su solicitud fue marcada como ATENDIDA.",
            "",
            f"ID: {s.id} · Inventario: {inv}",
            f"Fecha solicitud: {_fmt_date(s.fecha_solicitud)}",
            f"Cierre registrado: {_fmt_dt(s.atendido_en)}",
            "",
            f"Portal: {app_url}",
        ]
    )
    html = _wrap_html("Solicitud atendida", inner, None)
    return plain, html


def password_reset(reset_url: str, username: str | None = None) -> tuple[str, str]:
    cuenta = f" para la cuenta <strong>{username}</strong>" if username else ""
    intro = (
        f"<p style=\"margin:0 0 16px;\">Recibimos una petición para <strong>restablecer la contraseña</strong>{cuenta} en "
        "<strong>Mtto equipos</strong>. Si fue usted, use el botón (válido por tiempo limitado).</p>"
    )
    warn = """<p style="margin:16px 0 0;padding:12px 14px;background:rgba(120,53,15,0.35);border-radius:10px;border:1px solid rgba(251,191,36,0.4);font-size:13px;color:#fde68a;">
Si <strong>no</strong> solicitó este cambio, ignore este mensaje; su contraseña actual no se modifica hasta que pulse el enlace.</p>"""
    inner = intro + _cta_button(reset_url, "Restablecer contraseña") + warn

    plain_lines = ["Restablecer contraseña — Mtto equipos", ""]
    if username:
        plain_lines.append(f"Cuenta: {username}")
        plain_lines.append("")
    plain_lines.extend(
        [
            "Abra el enlace (válido por tiempo limitado):",
            reset_url,
            "",
            "Si no solicitó el cambio, ignore este mensaje.",
        ]
    )
    plain = "\n".join(plain_lines)
    html = _wrap_html("Restablecer contraseña", inner, None)
    return plain, html
