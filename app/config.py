import os
from urllib.parse import quote_plus


def _env_bool(key: str, default: str = "true") -> bool:
    return os.environ.get(key, default).lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-cambie-esto-en-produccion")

    # Servidor de desarrollo (run.py)
    FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "5001"))
    FLASK_DEBUG = _env_bool("FLASK_DEBUG", "true")

    # URL pública de la app (enlaces absolutos, futuras notificaciones, etc.)
    # Si FLASK_HOST es 0.0.0.0, defina APP_URL explícitamente (ej. http://192.168.1.10:5001)
    APP_URL = (os.environ.get("APP_URL") or f"http://127.0.0.1:{FLASK_PORT}").rstrip("/")

    _db_user = os.environ.get("MYSQL_USER", "")
    _db_pass = os.environ.get("MYSQL_PASSWORD", "")
    _db_host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    _db_port = os.environ.get("MYSQL_PORT", "3306")
    _db_name = os.environ.get("MYSQL_DATABASE", "mtto_equipos")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"mysql+pymysql://{quote_plus(_db_user)}:{quote_plus(_db_pass)}@{_db_host}:{_db_port}/{_db_name}?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_ENABLED = True
