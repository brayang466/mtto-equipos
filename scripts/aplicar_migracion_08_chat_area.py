"""Añade tipo/area/destinatario a chat_mensajes. Uso: python scripts/aplicar_migracion_08_chat_area.py"""
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


def _column_exists(cur, database: str, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (database, table, column),
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
            if not _column_exists(cur, database, "chat_mensajes", "tipo"):
                cur.execute(
                    """
                    ALTER TABLE chat_mensajes
                      ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'area'
                        COMMENT 'area | susurro' AFTER texto
                    """
                )
                print("Columna tipo añadida.")
            if not _column_exists(cur, database, "chat_mensajes", "area"):
                cur.execute(
                    """
                    ALTER TABLE chat_mensajes
                      ADD COLUMN area VARCHAR(64) NULL COMMENT 'Área laboral del canal' AFTER tipo
                    """
                )
                print("Columna area añadida.")
            if not _column_exists(cur, database, "chat_mensajes", "destinatario_id"):
                cur.execute(
                    """
                    ALTER TABLE chat_mensajes
                      ADD COLUMN destinatario_id BIGINT UNSIGNED NULL
                        COMMENT 'Usuario destino en susurro' AFTER area
                    """
                )
                print("Columna destinatario_id añadida.")
            cur.execute(
                """
                UPDATE chat_mensajes cm
                JOIN usuarios u ON u.id = cm.user_id
                SET cm.tipo = 'area', cm.area = u.area
                WHERE cm.area IS NULL OR cm.tipo IS NULL OR cm.tipo = ''
                """
            )
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'chat_mensajes' AND INDEX_NAME = 'idx_chat_area'
                """,
                (database,),
            )
            if not (cur.fetchone() or [0])[0]:
                cur.execute(
                    "ALTER TABLE chat_mensajes ADD KEY idx_chat_area (tipo, area, id)"
                )
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'chat_mensajes' AND INDEX_NAME = 'idx_chat_susurro'
                """,
                (database,),
            )
            if not (cur.fetchone() or [0])[0]:
                cur.execute(
                    """
                    ALTER TABLE chat_mensajes
                      ADD KEY idx_chat_susurro (tipo, destinatario_id, user_id, id)
                    """
                )
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'chat_mensajes'
                  AND CONSTRAINT_NAME = 'fk_chat_destinatario'
                """,
                (database,),
            )
            if not (cur.fetchone() or [0])[0]:
                cur.execute(
                    """
                    ALTER TABLE chat_mensajes
                      ADD CONSTRAINT fk_chat_destinatario
                      FOREIGN KEY (destinatario_id) REFERENCES usuarios (id) ON DELETE CASCADE
                    """
                )
        conn.commit()
    except pymysql.Error as e:
        conn.rollback()
        print(f"Error SQL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print("Migración 08 aplicada (chat área / susurro).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
