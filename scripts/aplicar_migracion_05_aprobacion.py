"""
Aprobación TIC + tabla presencia_usuarios.
Uso: python scripts/aplicar_migracion_05_aprobacion.py
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


def _column_exists(cur, database: str, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (database, table, column),
    )
    return bool((cur.fetchone() or [0])[0])


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
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
        )
    except pymysql.Error as e:
        print(f"Error de conexión: {e}", file=sys.stderr)
        return 1

    try:
        with conn.cursor() as cur:
            if not _column_exists(cur, database, "solicitudes_mantenimiento", "tipo_origen"):
                cur.execute(
                    """
                    ALTER TABLE solicitudes_mantenimiento
                      ADD COLUMN tipo_origen VARCHAR(20) NOT NULL DEFAULT 'usuario'
                        COMMENT 'usuario | tic' AFTER registrado_por_user_id
                    """
                )
                print("Columna tipo_origen agregada.")
            if not _column_exists(cur, database, "solicitudes_mantenimiento", "usuario_aprobador_id"):
                cur.execute(
                    """
                    ALTER TABLE solicitudes_mantenimiento
                      ADD COLUMN usuario_aprobador_id BIGINT UNSIGNED NULL AFTER tipo_origen
                    """
                )
                print("Columna usuario_aprobador_id agregada.")
            if not _column_exists(cur, database, "solicitudes_mantenimiento", "fecha_respuesta_usuario"):
                cur.execute(
                    """
                    ALTER TABLE solicitudes_mantenimiento
                      ADD COLUMN fecha_respuesta_usuario DATE NULL AFTER fecha_mantenimiento,
                      ADD COLUMN respuesta_usuario VARCHAR(20) NULL AFTER fecha_respuesta_usuario,
                      ADD COLUMN comentario_respuesta TEXT NULL AFTER respuesta_usuario
                    """
                )
                print("Columnas de respuesta de usuario agregadas.")
            if not _column_exists(cur, database, "solicitudes_mantenimiento", "usuario_aprobador_id"):
                pass
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
                    WHERE CONSTRAINT_SCHEMA = %s AND TABLE_NAME = 'solicitudes_mantenimiento'
                      AND CONSTRAINT_NAME = 'fk_sol_aprobador'
                    """,
                    (database,),
                )
                if not (cur.fetchone() or [0])[0]:
                    try:
                        cur.execute(
                            """
                            ALTER TABLE solicitudes_mantenimiento
                              ADD KEY idx_sol_aprobador (usuario_aprobador_id),
                              ADD CONSTRAINT fk_sol_aprobador
                                FOREIGN KEY (usuario_aprobador_id) REFERENCES usuarios (id) ON DELETE SET NULL
                            """
                        )
                    except pymysql.Error:
                        cur.execute(
                            "ALTER TABLE solicitudes_mantenimiento ADD KEY idx_sol_aprobador (usuario_aprobador_id)"
                        )

            if not _table_exists(cur, database, "presencia_usuarios"):
                cur.execute(
                    """
                    CREATE TABLE presencia_usuarios (
                      user_id BIGINT UNSIGNED NOT NULL,
                      last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      pagina_actual VARCHAR(255) NULL,
                      PRIMARY KEY (user_id),
                      KEY idx_presencia_last_seen (last_seen),
                      CONSTRAINT fk_presencia_user FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                print("Tabla presencia_usuarios creada.")
        conn.commit()
    except pymysql.Error as e:
        conn.rollback()
        print(f"Error SQL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print("Migración 05 aplicada (aprobación TIC + presencia).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
