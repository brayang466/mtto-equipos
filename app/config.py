import os
from urllib.parse import quote_plus


def _env_bool(key: str, default: str = "true") -> bool:
    return os.environ.get(key, default).lower() in ("1", "true", "yes", "on")


def _strip_env_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == v[-1] == "'") or (v[0] == v[-1] == '"')):
        return v[1:-1]
    return v


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-cambie-esto-en-produccion")

    FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "5001"))
    FLASK_DEBUG = _env_bool("FLASK_DEBUG", "true")

    APP_URL = (os.environ.get("APP_URL") or f"http://127.0.0.1:{FLASK_PORT}").rstrip("/")

    _db_user = os.environ.get("MYSQL_USER", "")
    _db_pass = _strip_env_quotes(os.environ.get("MYSQL_PASSWORD", ""))
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

    # Aviso de inactividad (solo usuarios autenticados en el front)
    SESSION_IDLE_MINUTES = int(os.environ.get("SESSION_IDLE_MINUTES", "10"))

    UPLOAD_RELATIVE = os.environ.get("UPLOAD_RELATIVE", "uploads_solicitudes")
    MAX_UPLOAD_FILES = int(os.environ.get("MAX_UPLOAD_FILES", "12"))
    MAX_UPLOAD_BYTES_PER_FILE = int(os.environ.get("MAX_UPLOAD_BYTES_PER_FILE", str(5 * 1024 * 1024)))
    ALLOWED_IMAGE_EXTENSIONS = frozenset(
        x.strip().lower()
        for x in os.environ.get("ALLOWED_IMAGE_EXTENSIONS", "png,jpg,jpeg,webp,gif").split(",")
        if x.strip()
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(40 * 1024 * 1024)))

    # --- Correo (SMTP). Variables en .env (ver .env.example) ---
    MAIL_ENABLED = _env_bool("MAIL_ENABLED", "false")
    MAIL_SERVER = (os.environ.get("MAIL_SERVER") or os.environ.get("MAIL_HOST") or "").strip()
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", "true")
    MAIL_USE_SSL = _env_bool("MAIL_USE_SSL", "false")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = _strip_env_quotes(os.environ.get("MAIL_PASSWORD", ""))
    MAIL_DEFAULT_SENDER = (os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("MAIL_FROM") or "").strip()
    MAIL_FROM_NAME = (os.environ.get("MAIL_FROM_NAME") or "").strip()
    MAIL_NOTIFY_TO = (os.environ.get("MAIL_NOTIFY_TO") or "tecnologia@colbeef.com").strip()
    MAIL_TIMEOUT = int(os.environ.get("MAIL_TIMEOUT", "10"))
    MAIL_SSL_VERIFY = _env_bool("MAIL_SSL_VERIFY", "true")
