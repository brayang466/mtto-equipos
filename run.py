"""
Arranque en desarrollo. Carga SIEMPRE el archivo `.env` en esta misma carpeta
(no usa `.env.example` salvo que usted lo copie a `.env`).
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
_ENV_PATH = ROOT / ".env"

if not _ENV_PATH.is_file():
    print(
        "\n[!] No existe el archivo .env en la carpeta del proyecto.\n"
        "    Copie .env.example → .env y edite los valores (solo .env se lee al ejecutar).\n",
        file=sys.stderr,
    )

# override=True: el .env del proyecto gana sobre variables globales de Windows
# (si no, un MYSQL_USER=root del sistema anula lo que ponga en .env).
load_dotenv(_ENV_PATH, override=True)

from urllib.parse import urlparse

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = app.config["FLASK_HOST"]
    port = app.config["FLASK_PORT"]
    app_url = app.config["APP_URL"]
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_user = urlparse(db_uri).username or "(vacío)"
    db_host = urlparse(db_uri).hostname or "?"
    db_name = (urlparse(db_uri).path or "").strip("/") or "?"
    print(
        f"\n  Mtto equipos — configuración cargada desde: {_ENV_PATH}\n"
        f"    Escucha en:  http://{host}:{port}/\n"
        f"    APP_URL:     {app_url}/\n"
        f"    MySQL (URI): usuario={db_user!r}  host={db_host!r}  base={db_name!r}\n"
        f"  Use en el navegador (enlaces y pie de página): {app_url}/\n"
    )
    app.run(
        debug=app.config["FLASK_DEBUG"],
        host=host,
        port=port,
    )
