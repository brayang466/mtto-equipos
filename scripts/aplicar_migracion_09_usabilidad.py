"""Crea tabla usabilidad_encuestas (SUS). Uso: python scripts/aplicar_migracion_09_usabilidad.py"""
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


def _table_exists(cur, database: str, table: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """,
        (database, table),
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
            if not _table_exists(cur, database, "usabilidad_encuestas"):
                cur.execute(
                    """
                    CREATE TABLE usabilidad_encuestas (
                      id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                      user_id BIGINT UNSIGNED NOT NULL,
                      q1 TINYINT UNSIGNED NOT NULL,
                      q2 TINYINT UNSIGNED NOT NULL,
                      q3 TINYINT UNSIGNED NOT NULL,
                      q4 TINYINT UNSIGNED NOT NULL,
                      q5 TINYINT UNSIGNED NOT NULL,
                      q6 TINYINT UNSIGNED NOT NULL,
                      q7 TINYINT UNSIGNED NOT NULL,
                      q8 TINYINT UNSIGNED NOT NULL,
                      q9 TINYINT UNSIGNED NOT NULL,
                      q10 TINYINT UNSIGNED NOT NULL,
                      score DECIMAL(5,2) NOT NULL COMMENT 'SUS 0-100',
                      creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (id),
                      UNIQUE KEY uk_usabilidad_user (user_id),
                      CONSTRAINT fk_usabilidad_user
                        FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                print("Tabla usabilidad_encuestas creada.")
            else:
                print("Tabla usabilidad_encuestas ya existe.")
        conn.commit()
    except pymysql.Error as e:
        conn.rollback()
        print(f"Error SQL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print("Migración 09 aplicada (usabilidad SUS).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
