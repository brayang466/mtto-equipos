"""Quita UNIQUE de email en usuarios y restaura superadmin. Uso: python scripts/aplicar_migracion_07_email_duplicado.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

import pymysql  # noqa: E402

SUPERADMIN_HASH = (
    "scrypt:32768:8:1$sKkoCyHLDvXz9neg$"
    "ddc6664bb36366e3eb974894d8acc0cbd7cf57231893f383bfb00456a27442e670a01646a06557f4c395139710e49f162004ddac541ee268690e47b711cf7e74"
)


def _pw() -> str:
    p = os.environ.get("MYSQL_PASSWORD", "") or ""
    if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
        return p[1:-1]
    return p


def _index_exists(cur, database: str, table: str, index: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        (database, table, index),
    )
    return bool((cur.fetchone() or [0])[0])


def main() -> int:
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ.get("MYSQL_USER", "")
    password = _pw()
    database = os.environ.get("MYSQL_DATABASE", "mtto_equipos")
    if not user:
        print("Defina MYSQL_USER en .env", file=sys.stderr)
        return 1
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database, charset="utf8mb4"
        )
    except pymysql.Error as e:
        print(f"Error de conexión: {e}", file=sys.stderr)
        return 1
    try:
        with conn.cursor() as cur:
            if _index_exists(cur, database, "usuarios", "uk_usuarios_email"):
                cur.execute("ALTER TABLE usuarios DROP INDEX uk_usuarios_email")
                print("Índice uk_usuarios_email eliminado (correos duplicados permitidos).")
            else:
                print("uk_usuarios_email ya no existe.")

            cur.execute(
                """
                INSERT INTO usuarios (username, email, password_hash, area, role, activo)
                VALUES (%s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                  email = VALUES(email),
                  password_hash = VALUES(password_hash),
                  area = VALUES(area),
                  role = VALUES(role),
                  activo = VALUES(activo)
                """,
                ("brayan.gomez", "tecnologia@colbeef.com", SUPERADMIN_HASH, "TIC", "superadmin"),
            )
            print("Superadmin brayan.gomez restaurado (clave: Pricetag1**).")
        conn.commit()
    except pymysql.Error as e:
        conn.rollback()
        print(f"Error SQL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print("Migración 07 aplicada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
