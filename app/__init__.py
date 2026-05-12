from flask import Flask

from app.config import Config
from app.extensions import csrf, db


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def inject_globals() -> dict:
        return {
            "app_url": app.config.get("APP_URL", ""),
            "app_name": "Mtto equipos",
        }

    from app.main.routes import bp as main_bp
    from app.equipos.routes import bp as equipos_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(equipos_bp)

    return app
