from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import Integer, cast, or_

from app.equipos.forms import Mtto2026Form
from app.extensions import db
from app.models import Equipo

bp = Blueprint("equipos", __name__, url_prefix="/equipos")


@bp.route("/")
def lista():
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
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
    return render_template("equipos/lista.html", pagination=pagination, q=q)


@bp.route("/<int:equipo_id>", methods=["GET", "POST"])
def detalle(equipo_id: int):
    equipo = db.session.get(Equipo, equipo_id)
    if equipo is None:
        flash("Equipo no encontrado.", "warning")
        return redirect(url_for("equipos.lista"))

    form = Mtto2026Form()
    if request.method == "GET":
        form.mtto_realizado_1s_2026.data = bool(equipo.mtto_realizado_1s_2026)
        form.mtto_realizado_2s_2026.data = bool(equipo.mtto_realizado_2s_2026)

    if form.validate_on_submit():
        equipo.mtto_realizado_1s_2026 = bool(form.mtto_realizado_1s_2026.data)
        equipo.mtto_realizado_2s_2026 = bool(form.mtto_realizado_2s_2026.data)
        db.session.commit()
        flash("Registro de mantenimiento 2026 actualizado.", "success")
        return redirect(url_for("equipos.detalle", equipo_id=equipo.id))

    return render_template("equipos/detalle.html", equipo=equipo, form=form)
