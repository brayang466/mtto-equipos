"""
Crea las tablas solicitudes_mantenimiento y solicitudes_adjuntos (migración 03).
Uso desde la raíz del proyecto:
  python scripts/aplicar_migracion_03_solicitudes.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

import pymysql  # noqa: E402


def _pw() -> str:
    p = os.environ.get("MYSQL_PASSWORD", "") or ""
    if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
        return p[1:-1]
    return p


def main() -> int:
    sql_path = ROOT / "database" / "03_solicitudes_mantenimiento.sql"
    if not sql_path.is_file():
        print(f"No se encuentra {sql_path}", file=sys.stderr)
        return 1

    raw = sql_path.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
    cleaned = "\n".join(lines)
    chunks = [c.strip() for c in cleaned.split(";") if c.strip()]

    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ.get("MYSQL_USER", "")
    password = _pw()
    database = os.environ.get("MYSQL_DATABASE", "mtto_equipos")

    if not user:
        print("Defina MYSQL_USER y MYSQL_PASSWORD en .env", file=sys.stderr)
        return 1

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
        )
    except pymysql.Error as e:
        print(f"Error de conexión MySQL: {e}", file=sys.stderr)
        return 1

    try:
        with conn.cursor() as cur:
            for stmt in chunks:
                cur.execute(stmt)
        conn.commit()
    except pymysql.Error as e:
        conn.rollback()
        print(f"Error ejecutando migración: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print("Migración 03 aplicada correctamente (tablas solicitudes_*).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
