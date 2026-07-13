"""Prueba conexión MySQL con variables de .env (no imprime la contraseña)."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

import os

import pymysql


def _strip_env_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == v[-1] == "'") or (v[0] == v[-1] == '"')):
        return v[1:-1]
    return v


def main() -> int:
    user = os.environ.get("MYSQL_USER", "")
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    database = os.environ.get("MYSQL_DATABASE", "mtto_equipos")
    raw_pass = os.environ.get("MYSQL_PASSWORD", "")

    app_pass = _strip_env_quotes(raw_pass)

    print(f"Usuario: {user!r}  Host: {host!r}  Base: {database!r}")
    print(f"Contraseña en .env: {len(raw_pass)} caracteres (raw)")
    print(f"Contraseña que usa la app: {len(app_pass)} caracteres (sin comillas externas)")
    if raw_pass != app_pass:
        print("  -> Se quitaron comillas del valor en .env (normal si puso 'clave' entre comillas)")

    try:
        pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=app_pass,
            database=database,
            connect_timeout=8,
        )
        print("OK: conexión MySQL correcta.")
        return 0
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else None
        print(f"FALLO ({code}): {e}")
        if code == 1045:
            print(
                "\nMySQL rechazó usuario/contraseña. Compruebe en Workbench que "
                f"'{user}'@'localhost' existe y que MYSQL_PASSWORD en .env "
                "coincide exactamente (sin espacios extra)."
            )
        elif code == 2003:
            print("\nNo hay servidor MySQL en ese host/puerto (servicio detenido o puerto distinto).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
