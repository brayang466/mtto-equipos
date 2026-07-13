"""
Envío de correos vía SMTP (smtplib). Variables en .env — ver .env.example.
Mensajes en multipart: texto plano + HTML (plantillas en mail_templates.py).
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

from app.mail_templates import (
    _subject_solicitud,
    password_reset as tpl_password_reset,
    solicitud_atendida_usuario,
    solicitud_confirmacion_usuario,
    solicitud_nueva_tic,
    solicitud_pendiente_aprobacion_usuario,
    solicitud_respuesta_aprobacion_tic,
)
from app.models import SolicitudMantenimiento


def _format_from_header() -> str:
    name = (current_app.config.get("MAIL_FROM_NAME") or "").strip()
    addr = (
        current_app.config.get("MAIL_DEFAULT_SENDER")
        or current_app.config.get("MAIL_USERNAME")
        or ""
    ).strip()
    if name and addr:
        return f"{name} <{addr}>"
    return addr or "noreply@localhost"


def _smtp_ssl_context() -> ssl.SSLContext:
    verify = bool(current_app.config.get("MAIL_SSL_VERIFY", True))
    if verify:
        return ssl.create_default_context()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _send_email(to_addrs: list[str], subject: str, body_plain: str, body_html: str | None = None) -> bool:
    if not current_app.config.get("MAIL_ENABLED"):
        current_app.logger.debug("MAIL_ENABLED=false: no se envía correo.")
        return True

    host = (current_app.config.get("MAIL_SERVER") or "").strip()
    sender = _format_from_header()
    if not host or not sender:
        current_app.logger.warning("Correo: falta MAIL_SERVER o remitente.")
        return False

    to_clean = [t.strip() for t in to_addrs if t and t.strip()]
    if not to_clean:
        return False

    port = int(current_app.config.get("MAIL_PORT") or 587)
    use_tls = bool(current_app.config.get("MAIL_USE_TLS"))
    use_ssl = bool(current_app.config.get("MAIL_USE_SSL"))
    timeout = int(current_app.config.get("MAIL_TIMEOUT") or 25)
    user = (current_app.config.get("MAIL_USERNAME") or "").strip()
    password = (current_app.config.get("MAIL_PASSWORD") or "").strip()
    ctx = _smtp_ssl_context()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to_clean)
    msg.set_content(body_plain)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls(context=ctx)
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
    except (OSError, smtplib.SMTPException, Exception) as exc:
        current_app.logger.exception("Fallo SMTP: %s", exc)
        return False

    current_app.logger.info("Correo enviado a %s", to_clean)
    return True


def enviar_correos_nueva_solicitud(solicitud: SolicitudMantenimiento) -> None:
    """Aviso a TI + confirmación al usuario que registró (si aplica)."""
    if not current_app.config.get("MAIL_ENABLED"):
        return
    notify_solicitud_creada(solicitud)
    u = solicitud.registrado_por
    if u and u.email:
        mail_confirmacion_usuario_solicitud(u.email, solicitud)


def notify_solicitud_creada(solicitud: SolicitudMantenimiento) -> bool:
    """Aviso a TI (MAIL_NOTIFY_TO) con resumen HTML de la solicitud."""
    to_addr = (current_app.config.get("MAIL_NOTIFY_TO") or "").strip()
    if not to_addr:
        current_app.logger.warning("MAIL_NOTIFY_TO vacío.")
        return False

    base = (current_app.config.get("APP_URL") or "").rstrip("/")
    panel_url = f"{base}/equipos/solicitudes"
    eq = solicitud.equipo
    equipo_url = f"{base}/equipos/{eq.id}" if eq else None

    inv = eq.numero_inventario if eq else "?"
    subject = _subject_solicitud("Nueva solicitud de usuario", solicitud.id, inv)

    plain, html = solicitud_nueva_tic(solicitud, panel_url, equipo_url)
    return _send_email([to_addr], subject, plain, html)


def mail_confirmacion_usuario_solicitud(user_email: str, solicitud: SolicitudMantenimiento) -> bool:
    app_url = (current_app.config.get("APP_URL") or "").rstrip("/") + "/"
    eq = solicitud.equipo
    inv = eq.numero_inventario if eq else "?"
    subject = _subject_solicitud("Registro confirmado", solicitud.id, inv)
    plain, html = solicitud_confirmacion_usuario(solicitud, app_url)
    return _send_email([user_email], subject, plain, html)


def mail_solicitud_atendida(user_email: str, solicitud: SolicitudMantenimiento) -> bool:
    app_url = (current_app.config.get("APP_URL") or "").rstrip("/") + "/"
    eq = solicitud.equipo
    inv = eq.numero_inventario if eq else "?"
    subject = _subject_solicitud("Marcada como atendida", solicitud.id, inv)
    plain, html = solicitud_atendida_usuario(solicitud, app_url)
    return _send_email([user_email], subject, plain, html)


def mail_password_reset(user_email: str, reset_url: str, username: str | None = None) -> bool:
    subject = "[Mtto equipos] Restablecer contraseña"
    plain, html = tpl_password_reset(reset_url, username=username)
    return _send_email([user_email], subject, plain, html)


def mail_tic_respuesta_aprobacion(solicitud: SolicitudMantenimiento) -> bool:
    """Aviso a TIC cuando un usuario aprueba o deniega mantenimiento."""
    to_addr = (current_app.config.get("MAIL_NOTIFY_TO") or "").strip()
    if not to_addr:
        current_app.logger.warning("MAIL_NOTIFY_TO vacío.")
        return False

    base = (current_app.config.get("APP_URL") or "").rstrip("/")
    panel_url = f"{base}/equipos/solicitudes"
    eq = solicitud.equipo
    inv = eq.numero_inventario if eq else "?"
    aprobada = solicitud.respuesta_usuario == "aprobada"
    accion = "Aprobada por el usuario" if aprobada else "Denegada por el usuario"
    subject = _subject_solicitud(accion, solicitud.id, inv)

    plain, html = solicitud_respuesta_aprobacion_tic(solicitud, panel_url)
    return _send_email([to_addr], subject, plain, html)


def mail_solicitud_pendiente_aprobacion(user_email: str, solicitud: SolicitudMantenimiento) -> bool:
    base = (current_app.config.get("APP_URL") or "").rstrip("/")
    aprobar_url = f"{base}/mis-aprobaciones"
    eq = solicitud.equipo
    inv = eq.numero_inventario if eq else "?"
    subject = _subject_solicitud("Requiere su aprobación", solicitud.id, inv)
    plain, html = solicitud_pendiente_aprobacion_usuario(solicitud, aprobar_url)
    return _send_email([user_email], subject, plain, html)
