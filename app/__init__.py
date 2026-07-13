from pathlib import Path

from flask import Flask

from app.config import Config
from app.extensions import csrf, db, login_manager


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    upload_dir = Path(app.instance_path) / app.config["UPLOAD_RELATIVE"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_dir.resolve())

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    @app.before_request
    def _track_presence() -> None:
        from flask_login import current_user

        if current_user.is_authenticated:
            try:
                from app.presence_service import touch_presence

                touch_presence(current_user.id)
            except Exception:
                db.session.rollback()

    @app.context_processor
    def inject_globals() -> dict:
        from flask_login import current_user

        idle_min = int(app.config.get("SESSION_IDLE_MINUTES") or 10)
        online_users = []
        pending_approvals = 0
        if current_user.is_authenticated:
            try:
                if not current_user.is_superadmin():
                    from app.presence_service import count_pending_approvals

                    pending_approvals = count_pending_approvals(current_user.id)
            except Exception:
                db.session.rollback()
        return {
            "app_url": app.config.get("APP_URL", ""),
            "app_name": "Mtto equipos",
            "session_idle_ms": max(1, idle_min) * 60 * 1000,
            "pending_approvals_count": pending_approvals,
        }

    from app.auth.routes import bp as auth_bp
    from app.equipos.routes import bp as equipos_bp
    from app.main.routes import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(equipos_bp)

    return app
