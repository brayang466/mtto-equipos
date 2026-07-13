from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from werkzeug.security import generate_password_hash

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user
from sqlalchemy import Integer, cast, or_

from app.constants import ESTADO_SOL_ATENDIDA, ESTADO_SOL_APROBADA, ESTADO_SOL_PENDIENTE, ROLE_SUPERADMIN, ROLE_USER
from app.equipos.forms import (
    AdminUserCreateForm,
    AdminUserEditForm,
    EliminarEquipoForm,
    EquipoEditForm,
    Mtto2026Form,
    SolicitudAdminEditForm,
    SolicitudEliminarForm,
    SolicitudMantenimientoForm,
    SolicitudTicForm,
)
from app.equipos.inventario_service import (
    apply_equipo_edit_form,
    choices_area_inventario,
    eliminar_equipo,
    populate_equipo_edit_form,
)
from app.extensions import db
from app.mail import enviar_correos_nueva_solicitud, mail_solicitud_atendida, mail_solicitud_pendiente_aprobacion
from app.models import Equipo, SolicitudAdjunto, SolicitudMantenimiento, User, UserPresence
from app.solicitud_export import generar_csv_solicitudes, generar_zip_evidencias, parse_rango_export
from app.solicitud_service import (
    aplicar_edicion_admin_solicitud,
    choices_usuario_aprobador,
    crear_solicitud_con_adjuntos,
    crear_solicitud_tic,
    eliminar_solicitud_completa,
    puede_marcar_atendida,
    preparar_evidencias,
    solicitud_detalle_context,
    usuarios_aprobadores_por_equipo,
)

bp = Blueprint("equipos", __name__, url_prefix="/equipos")


@bp.context_processor
def _inject_solicitud_ui():
    from app.solicitud_service import (
        denegada_sigue_abierta,
        etiqueta_estado_solicitud,
        puede_marcar_atendida,
        respuesta_usuario_legible,
    )

    return {
        "denegada_sigue_abierta": denegada_sigue_abierta,
        "etiqueta_estado_solicitud": etiqueta_estado_solicitud,
        "puede_marcar_atendida": puede_marcar_atendida,
        "respuesta_usuario_legible": respuesta_usuario_legible,
    }


@bp.before_request
def _requiere_superadmin() -> None:
    from flask import redirect, url_for
    from flask_login import current_user

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.full_path))
    if getattr(current_user, "role", None) != ROLE_SUPERADMIN:
        flash("No tiene permiso para acceder al inventario o solicitudes internas.", "warning")
        return redirect(url_for("main.inicio"))


def _safe_equipos_list_return(raw: str | None) -> str | None:
    """Solo rutas de listado /equipos (con query opcional); evita redirecciones abiertas."""
    if not raw or not isinstance(raw, str):
        return None
    u = raw.strip()
    if not u.startswith("/") or u.startswith("//"):
        return None
    if any(c in u for c in ("\n", "\r")):
        return None
    parsed = urlparse(u)
    path = (parsed.path or "").rstrip("/") or "/"
    if path != "/equipos":
        return None
    out = parsed.path or "/equipos/"
    if parsed.query:
        out = f"{out}?{parsed.query}"
    return out


def _safe_solicitudes_list_return(raw: str | None) -> str | None:
    """Solo /equipos/solicitudes con query opcional (para conservar filtros al volver desde detalle)."""
    if not raw or not isinstance(raw, str):
        return None
    u = raw.strip()
    if not u.startswith("/") or u.startswith("//"):
        return None
    if any(c in u for c in ("\n", "\r")):
        return None
    parsed = urlparse(u)
    path = (parsed.path or "").rstrip("/") or "/"
    if path != "/equipos/solicitudes":
        return None
    out = parsed.path or "/equipos/solicitudes"
    if parsed.query:
        out = f"{out}?{parsed.query}"
    return out


@bp.route("/")
def lista():
    q = (request.args.get("q") or "").strip()[:200]
    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1
    per_page = 30

    query = Equipo.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Equipo.numero_inventario.like(like),
                Equipo.numero_contable.like(like),
                Equipo.departamento.like(like),
                Equipo.area.like(like),
                Equipo.usuario.like(like),
                Equipo.descripcion.like(like),
                Equipo.marca_referencia.like(like),
            )
        )
    query = query.order_by(cast(Equipo.numero_inventario, Integer).asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("equipos/lista.html", pagination=pagination, q=q, total_equipos=pagination.total)


@bp.route("/<int:equipo_id>/solicitud-tic", methods=["GET", "POST"])
def solicitud_tic(equipo_id: int):
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        flash("Equipo no encontrado.", "warning")
        return redirect(url_for("equipos.lista"))

    list_next = _safe_equipos_list_return(request.values.get("next"))
    back_url = list_next or url_for("equipos.lista")

    usuarios = usuarios_aprobadores_por_equipo(equipo)
    form = SolicitudTicForm()
    form.usuario_aprobador_id.choices = choices_usuario_aprobador(usuarios)

    if request.method == "GET" and not form.fecha_solicitud.data:
        form.fecha_solicitud.data = date.today()

    if request.method == "POST":
        form.usuario_aprobador_id.choices = choices_usuario_aprobador(usuarios)
        if form.validate_on_submit():
            uid = form.usuario_aprobador_id.data
            if not uid:
                flash("Seleccione al usuario que debe aprobar la solicitud.", "warning")
            elif uid not in {u.id for u in usuarios}:
                flash("Seleccione un usuario válido del área del equipo.", "warning")
            else:
                obs = (form.observaciones.data or "").strip() or None
                solicitud, err = crear_solicitud_tic(
                    equipo,
                    form.fecha_solicitud.data,
                    form.fecha_mantenimiento.data,
                    obs,
                    current_user.id,
                    uid,
                )
                if err:
                    flash(err, "danger")
                else:
                    aprobador = db.session.get(User, uid)
                    if current_app.config.get("MAIL_ENABLED") and aprobador and aprobador.email:
                        if mail_solicitud_pendiente_aprobacion(aprobador.email, solicitud):
                            flash(
                                f"Solicitud enviada a {aprobador.username}. Se notificó por correo para aprobar o denegar.",
                                "success",
                            )
                        else:
                            flash(
                                "Solicitud registrada, pero no se pudo enviar el correo al usuario.",
                                "warning",
                            )
                    else:
                        flash(
                            f"Solicitud enviada a {aprobador.username if aprobador else 'usuario'}. "
                            "Debe aprobar o denegar desde el portal.",
                            "success",
                        )
                    return redirect(back_url)
        elif form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)

    return render_template(
        "equipos/solicitud_tic.html",
        equipo=equipo,
        form=form,
        back_url=back_url,
        list_next_hidden=list_next,
        usuarios_area=len(usuarios),
    )


@bp.route("/solicitudes")
def solicitudes_lista():
    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1
    equipo_id = request.args.get("equipo_id", type=int)
    per_page = 25

    q = SolicitudMantenimiento.query.join(Equipo).order_by(SolicitudMantenimiento.creado_en.desc())
    if equipo_id:
        q = q.filter(SolicitudMantenimiento.equipo_id == equipo_id)
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    back_url = _safe_equipos_list_return(request.args.get("next")) or url_for("equipos.lista")
    sol_return = _safe_solicitudes_list_return(request.full_path)
    return render_template(
        "equipos/solicitudes_lista.html",
        pagination=pagination,
        equipo_filtro=equipo_id,
        back_url=back_url,
        sol_return=sol_return,
        export_desde=request.args.get("desde", ""),
        export_hasta=request.args.get("hasta", ""),
    )


@bp.route("/solicitudes/exportar")
def solicitudes_exportar():
    desde, hasta = parse_rango_export()
    formato = (request.args.get("formato") or "csv").strip().lower()
    if formato == "zip":
        result = generar_zip_evidencias(desde, hasta)
        if isinstance(result, tuple) and result[1]:
            flash(result[1], "warning")
            return redirect(
                url_for(
                    "equipos.solicitudes_lista",
                    desde=request.args.get("desde", ""),
                    hasta=request.args.get("hasta", ""),
                )
            )
        return result[0] if isinstance(result, tuple) else result
    return generar_csv_solicitudes(desde, hasta)


@bp.route("/solicitudes/<int:solicitud_id>/editar", methods=["GET", "POST"])
def solicitud_editar(solicitud_id: int):
    sol = db.session.get(SolicitudMantenimiento, solicitud_id)
    if sol is None:
        abort(404)
    form = SolicitudAdminEditForm()
    if request.method == "GET":
        form.fecha_solicitud.data = sol.fecha_solicitud
        form.fecha_mantenimiento.data = sol.fecha_mantenimiento
        form.fecha_respuesta_usuario.data = sol.fecha_respuesta_usuario
        form.estado.data = sol.estado
        form.observaciones.data = sol.observaciones
        form.comentario_respuesta.data = sol.comentario_respuesta
        form.respuesta_usuario.data = sol.respuesta_usuario or ""
    elif form.validate_on_submit():
        try:
            aplicar_edicion_admin_solicitud(
                sol,
                fecha_solicitud=form.fecha_solicitud.data,
                fecha_mantenimiento=form.fecha_mantenimiento.data,
                fecha_respuesta_usuario=form.fecha_respuesta_usuario.data,
                estado=form.estado.data,
                observaciones=(form.observaciones.data or "").strip() or None,
                comentario_respuesta=(form.comentario_respuesta.data or "").strip() or None,
                respuesta_usuario=(form.respuesta_usuario.data or "").strip() or None,
            )
            flash("Solicitud actualizada.", "success")
            return redirect(url_for("equipos.solicitudes_lista"))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("solicitud_editar")
            flash("No se pudo guardar la solicitud.", "danger")
    elif form.is_submitted():
        from app.validators import flash_form_errors

        flash_form_errors(form)
    return render_template(
        "equipos/solicitud_editar.html",
        sol=sol,
        form=form,
        back_url=url_for("equipos.solicitudes_lista"),
    )


@bp.route("/solicitudes/<int:solicitud_id>/eliminar", methods=["GET", "POST"])
def solicitud_eliminar(solicitud_id: int):
    sol = db.session.get(SolicitudMantenimiento, solicitud_id)
    if sol is None:
        abort(404)
    form = SolicitudEliminarForm()
    if form.validate_on_submit():
        try:
            eliminar_solicitud_completa(sol)
            flash("Solicitud eliminada.", "success")
            return redirect(url_for("equipos.solicitudes_lista"))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("solicitud_eliminar")
            flash("No se pudo eliminar la solicitud.", "danger")
    return render_template(
        "equipos/solicitud_eliminar.html",
        sol=sol,
        form=form,
        back_url=url_for("equipos.solicitudes_lista"),
    )


@bp.route("/solicitudes/<int:solicitud_id>/resumen")
def solicitud_resumen(solicitud_id: int):
    sol = db.session.get(SolicitudMantenimiento, solicitud_id)
    if sol is None:
        abort(404)
    ctx = solicitud_detalle_context(sol)
    return render_template("equipos/_solicitud_resumen.html", **ctx)


@bp.route("/adjuntos/<int:adjunto_id>")
def adjunto_ver(adjunto_id: int):
    adj = db.session.get(SolicitudAdjunto, adjunto_id)
    if adj is None:
        abort(404)
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    path = (upload_root / adj.nombre_archivo).resolve()
    try:
        path.relative_to(upload_root)
    except ValueError:
        abort(404)
    if not path.is_file():
        abort(404)
    return send_from_directory(
        str(upload_root),
        adj.nombre_archivo,
        mimetype=adj.mime or "application/octet-stream",
        as_attachment=False,
        download_name=adj.nombre_original,
    )


@bp.route("/<int:equipo_id>/solicitud-mantenimiento", methods=["GET", "POST"])
def solicitud_nueva(equipo_id: int):
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        flash("Equipo no encontrado.", "warning")
        return redirect(url_for("equipos.lista"))

    list_next = _safe_equipos_list_return(request.values.get("next"))
    detalle_kwargs: dict = {"equipo_id": equipo.id}
    if list_next:
        detalle_kwargs["next"] = list_next
    back_url = url_for("equipos.detalle", **detalle_kwargs)

    form = SolicitudMantenimientoForm()
    if request.method == "GET" and not form.fecha_solicitud.data:
        form.fecha_solicitud.data = date.today()

    def _render_sol_form():
        return render_template(
            "equipos/solicitud_nueva.html",
            equipo=equipo,
            form=form,
            back_url=back_url,
            list_next_hidden=list_next,
        )

    if request.method == "POST":
        if form.validate_on_submit():
            files = request.files.getlist("evidencias")
            prepared, err = preparar_evidencias(files)
            if err:
                flash(err, "warning")
                return _render_sol_form()

            obs = (form.observaciones.data or "").strip() or None
            solicitud, err2 = crear_solicitud_con_adjuntos(
                equipo,
                form.fecha_solicitud.data,
                form.fecha_mantenimiento.data,
                obs,
                prepared,
                current_user.id,
            )
            if err2:
                flash(err2, "danger")
                return _render_sol_form()

            enviar_correos_nueva_solicitud(solicitud)
            flash("Solicitud de mantenimiento registrada.", "success")

            redir_kwargs: dict = {"equipo_id": equipo.id}
            if list_next:
                redir_kwargs["next"] = list_next
            return redirect(url_for("equipos.detalle", **redir_kwargs))
        if form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)
            return _render_sol_form()

    return _render_sol_form()


@bp.route("/solicitudes/<int:solicitud_id>/marcar-atendida", methods=["POST"])
def solicitud_marcar_atendida(solicitud_id: int):
    from flask_wtf.csrf import validate_csrf
    from wtforms.validators import ValidationError

    try:
        validate_csrf(request.form.get("csrf_token"))
    except ValidationError:
        flash("Sesión de seguridad expirada. Recargue la página e intente de nuevo.", "danger")
        return redirect(url_for("equipos.solicitudes_lista"))

    sol = db.session.get(SolicitudMantenimiento, solicitud_id)
    if sol is None:
        flash("Solicitud no encontrada.", "warning")
        return redirect(url_for("equipos.solicitudes_lista"))
    if not puede_marcar_atendida(sol):
        flash("Esta solicitud ya no puede marcarse como atendida.", "info")
        return redirect(url_for("equipos.solicitudes_lista"))

    from app.datetime_utils import now_colombia_naive

    sol.estado = ESTADO_SOL_ATENDIDA
    sol.atendido_en = now_colombia_naive()
    db.session.commit()

    msg = "Solicitud marcada como atendida."
    category: str = "success"
    u = sol.registrado_por
    if current_app.config.get("MAIL_ENABLED") and u and u.email:
        if not mail_solicitud_atendida(u.email, sol):
            msg = "Estado actualizado, pero no se pudo enviar el correo al usuario."
            category = "warning"
        else:
            msg = "Solicitud marcada como atendida; se notificó al usuario por correo."
    flash(msg, category)

    return redirect(url_for("equipos.solicitudes_lista"))


@bp.route("/<int:equipo_id>/editar", methods=["GET", "POST"])
def editar(equipo_id: int):
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        flash("Equipo no encontrado.", "warning")
        return redirect(url_for("equipos.lista"))

    list_next = _safe_equipos_list_return(request.values.get("next"))
    back_url = url_for("equipos.detalle", equipo_id=equipo.id, **({"next": list_next} if list_next else {}))

    form = EquipoEditForm()
    delete_form = EliminarEquipoForm(prefix="del")
    form.area.choices = choices_area_inventario(equipo.area)

    if request.method == "GET":
        populate_equipo_edit_form(form, equipo)

    if request.method == "POST":
        form.area.choices = choices_area_inventario(equipo.area)
        if delete_form.eliminar.data and delete_form.validate_on_submit():
            inv = equipo.numero_inventario
            try:
                eliminar_equipo(equipo)
            except Exception:
                db.session.rollback()
                flash("No se pudo eliminar el equipo. Intente de nuevo.", "danger")
                return redirect(url_for("equipos.editar", equipo_id=equipo_id, next=list_next))
            flash(f"Equipo {inv} eliminado del inventario.", "success")
            return redirect(list_next or url_for("equipos.lista"))

        if form.guardar.data and form.validate_on_submit():
            try:
                apply_equipo_edit_form(form, equipo)
            except ValueError:
                flash("Seleccione un área válida del listado.", "warning")
                return render_template(
                    "equipos/editar.html",
                    equipo=equipo,
                    form=form,
                    delete_form=delete_form,
                    back_url=back_url,
                    list_next_hidden=list_next,
                    n_solicitudes=equipo.solicitudes_mantenimiento.count(),
                )
            db.session.commit()
            flash("Asignación del equipo actualizada (departamento, área, cargo y usuario).", "success")
            if list_next:
                return redirect(url_for("equipos.detalle", equipo_id=equipo.id, next=list_next))
            return redirect(url_for("equipos.detalle", equipo_id=equipo.id))

        if form.is_submitted() and form.guardar.data:
            from app.validators import flash_form_errors

            flash_form_errors(form)
        elif delete_form.is_submitted() and delete_form.eliminar.data:
            from app.validators import flash_form_errors

            flash_form_errors(delete_form, category="danger")
            populate_equipo_edit_form(form, equipo)

    n_sol = equipo.solicitudes_mantenimiento.count()
    return render_template(
        "equipos/editar.html",
        equipo=equipo,
        form=form,
        delete_form=delete_form,
        back_url=back_url,
        list_next_hidden=list_next,
        n_solicitudes=n_sol,
    )


@bp.route("/<int:equipo_id>", methods=["GET", "POST"])
def detalle(equipo_id: int):
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        flash("Equipo no encontrado.", "warning")
        return redirect(url_for("equipos.lista"))

    list_next = _safe_equipos_list_return(request.values.get("next"))
    back_url = list_next or url_for("equipos.lista")

    form = Mtto2026Form()
    if request.method == "GET":
        form.mtto_realizado_1s_2026.data = bool(equipo.mtto_realizado_1s_2026)
        form.mtto_realizado_2s_2026.data = bool(equipo.mtto_realizado_2s_2026)

    if request.method == "POST":
        if form.validate_on_submit():
            equipo.mtto_realizado_1s_2026 = bool(form.mtto_realizado_1s_2026.data)
            equipo.mtto_realizado_2s_2026 = bool(form.mtto_realizado_2s_2026.data)
            db.session.commit()
            flash("Registro de mantenimiento 2026 actualizado.", "success")
            preserved = _safe_equipos_list_return(request.form.get("next"))
            if preserved:
                return redirect(
                    url_for("equipos.detalle", equipo_id=equipo.id, next=preserved)
                )
            return redirect(url_for("equipos.detalle", equipo_id=equipo.id))
        if form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)

    solicitudes = (
        SolicitudMantenimiento.query.filter_by(equipo_id=equipo.id)
        .order_by(SolicitudMantenimiento.creado_en.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "equipos/detalle.html",
        equipo=equipo,
        form=form,
        back_url=back_url,
        list_next_hidden=list_next,
        solicitudes=solicitudes,
    )


@bp.route("/usuarios")
def usuarios_lista():
    q = (request.args.get("q") or "").strip()[:200]
    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1
    per_page = 25

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                User.username.like(like),
                User.email.like(like),
                User.area.like(like),
            )
        )
    query = query.order_by(User.username.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    user_ids = [u.id for u in pagination.items]
    pres_map: dict[int, UserPresence] = {}
    if user_ids:
        for p in UserPresence.query.filter(UserPresence.user_id.in_(user_ids)).all():
            pres_map[p.user_id] = p

    from app.datetime_utils import format_ultimo_acceso
    from app.presence_service import _user_is_online

    rows = []
    for u in pagination.items:
        p = pres_map.get(u.id)
        online = _user_is_online(p) if u.activo else False
        if online:
            ultimo = "Conectado"
        elif p:
            ultimo = format_ultimo_acceso(p.last_seen)
        else:
            ultimo = "Sin conexión"
        rows.append({"user": u, "ultimo_acceso": ultimo, "online": online})

    return render_template(
        "equipos/usuarios_lista.html",
        pagination=pagination,
        rows=rows,
        q=q,
    )


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
def usuario_nuevo():
    form = AdminUserCreateForm()
    if form.validate_on_submit():
        username = (form.username.data or "").strip().lower()
        email = (form.email.data or "").strip().lower()
        if User.query.filter_by(username=username).first():
            flash("Ese usuario ya existe.", "danger")
        else:
            user = User(
                username=username,
                email=email,
                area=form.area.data,
                role=ROLE_USER,
                activo=True,
                password_hash=generate_password_hash(form.password.data),
            )
            db.session.add(user)
            try:
                db.session.commit()
                flash(f"Usuario {username} creado.", "success")
                return redirect(url_for("equipos.usuarios_lista"))
            except Exception:
                db.session.rollback()
                flash("No se pudo crear el usuario.", "danger")
    elif form.is_submitted():
        from app.validators import flash_form_errors

        flash_form_errors(form)
    return render_template("equipos/usuario_form.html", form=form, titulo="Nuevo usuario", es_nuevo=True)


@bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
def usuario_editar(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        flash("Usuario no encontrado.", "warning")
        return redirect(url_for("equipos.usuarios_lista"))

    form = AdminUserEditForm(obj=user)
    if request.method == "GET":
        form.activo.data = bool(user.activo)

    if form.validate_on_submit():
        if user.id == current_user.id and not form.activo.data:
            flash("No puede desactivar su propia cuenta.", "warning")
        elif user.id == current_user.id and form.role.data != ROLE_SUPERADMIN:
            flash("No puede quitarse el rol de superadmin a usted mismo.", "warning")
        else:
            email = (form.email.data or "").strip().lower()
            user.email = email
            user.area = form.area.data
            user.role = form.role.data
            if user.id != current_user.id:
                user.activo = bool(form.activo.data)
            pwd = (form.nueva_password.data or "").strip()
            if pwd:
                user.password_hash = generate_password_hash(pwd)
            try:
                db.session.commit()
                flash("Usuario actualizado.", "success")
                return redirect(url_for("equipos.usuarios_lista"))
            except Exception:
                db.session.rollback()
                flash("No se pudo guardar.", "danger")
    elif form.is_submitted():
        from app.validators import flash_form_errors

        flash_form_errors(form)

    return render_template(
        "equipos/usuario_form.html",
        form=form,
        titulo=f"Editar: {user.username}",
        es_nuevo=False,
        user_obj=user,
    )
