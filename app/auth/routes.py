from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.forms import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from app.auth.tokens import make_password_reset_token, read_password_reset_token
from app.extensions import db
from app.mail import mail_password_reset
from app.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(target: str | None) -> str | None:
    if not target or not isinstance(target, str):
        return None
    t = target.strip()
    if not t.startswith("/") or t.startswith("//"):
        return None
    if any(c in t for c in ("\n", "\r")):
        return None
    return t


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    form = LoginForm()
    if request.method == "POST":
        if form.validate_on_submit():
            username = (form.username.data or "").strip().lower()
            try:
                user = User.query.filter_by(username=username, activo=True).first()
                if user and check_password_hash(user.password_hash, form.password.data):
                    login_user(user, remember=True)
                    flash("Sesión iniciada.", "success")
                    nxt = _safe_next(request.args.get("next"))
                    return redirect(nxt or url_for("main.inicio"))
                flash("Usuario o contraseña incorrectos.", "danger")
            except OperationalError:
                db.session.rollback()
                flash("No hay conexión con la base de datos. Intente de nuevo en unos segundos.", "danger")
        elif form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    if current_user.is_authenticated:
        try:
            from app.presence_service import mark_user_offline

            mark_user_offline(current_user.id)
        except Exception:
            db.session.rollback()
        logout_user()
        flash("Sesión cerrada.", "logout")
    return redirect(url_for("auth.login"))


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    form = RegisterForm()
    if request.method == "POST":
        if form.validate_on_submit():
            u = (form.username.data or "").strip().lower()
            e = (form.email.data or "").strip().lower()
            if User.query.filter_by(username=u).first():
                flash("Ese usuario ya está registrado.", "warning")
            else:
                user = User(
                    username=u,
                    email=e,
                    password_hash=generate_password_hash(form.password.data),
                    area=form.area.data,
                    role="user",
                )
                db.session.add(user)
                db.session.commit()
                flash("Cuenta creada. Ya puede iniciar sesión.", "success")
                return redirect(url_for("auth.login"))
        elif form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)
    return render_template("auth/register.html", form=form)


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    form = ForgotPasswordForm()
    if request.method == "POST":
        if form.validate_on_submit():
            from flask import current_app

            username = (form.username.data or "").strip().lower()
            email = (form.email.data or "").strip().lower()
            user = User.query.filter_by(username=username, email=email, activo=True).first()
            if user:
                if current_app.config.get("MAIL_ENABLED"):
                    token = make_password_reset_token(current_app.config["SECRET_KEY"], user.id)
                    reset_url = url_for("auth.reset_password", token=token, _external=True)
                    if not mail_password_reset(user.email, reset_url, username=user.username):
                        flash("No se pudo enviar el correo. Intente más tarde o contacte a TIC.", "danger")
                        return render_template("auth/forgot.html", form=form)
                else:
                    flash(
                        "La recuperación por correo no está activada en el servidor (MAIL_ENABLED=false). "
                        "Contacte a TIC.",
                        "warning",
                    )
            flash(
                "Si el usuario y el correo coinciden con una cuenta activa, recibirá un enlace para restablecer la contraseña.",
                "info",
            )
            return redirect(url_for("auth.login"))
        elif form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)
    return render_template("auth/forgot.html", form=form)


@bp.route("/restablecer/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    from flask import current_app

    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    user_id = read_password_reset_token(current_app.config["SECRET_KEY"], token)
    if not user_id:
        flash("El enlace no es válido o ha expirado. Solicite uno nuevo.", "danger")
        return redirect(url_for("auth.recuperar"))
    user = db.session.get(User, user_id)
    if user is None or not user.activo:
        flash("No se encontró la cuenta.", "danger")
        return redirect(url_for("auth.login"))
    form = ResetPasswordForm()
    if request.method == "POST":
        if form.validate_on_submit():
            user.password_hash = generate_password_hash(form.password.data)
            db.session.commit()
            flash(f"Contraseña actualizada para {user.username}. Inicie sesión con la nueva clave.", "success")
            return redirect(url_for("auth.login"))
        elif form.is_submitted():
            from app.validators import flash_form_errors

            flash_form_errors(form)
    return render_template("auth/reset.html", form=form, reset_user=user)
