"""
NO ejecute este archivo en MySQL Workbench: es código Python, no SQL.
Ejecútelo en PowerShell o CMD desde la carpeta del proyecto:
  python scripts/import_inventario_csv.py
En Workbench solo abra y ejecute archivos .sql (por ejemplo database/verificar_datos.sql).

Importa el inventario de equipos desde el CSV oficial hacia MySQL.

Excluye filas cuyo campo OBSERVACIONES (primera columna con ese nombre) indique
baja de equipo (dado de baja, baja de equipo, etc.).

Variables de entorno:
  MYSQL_HOST      (default: 127.0.0.1)
  MYSQL_PORT      (default: 3306)
  MYSQL_USER
  MYSQL_PASSWORD
  MYSQL_DATABASE  (default: mtto_equipos)

Uso:
  pip install -r requirements.txt
  (MySQL 8: hace falta el paquete "cryptography" para caching_sha2_password; va en requirements.txt)

  set MYSQL_USER=root
  set MYSQL_PASSWORD=...
  python scripts/import_inventario_csv.py

  PowerShell: si la clave tiene $ o ", use comillas simples:
  $env:MYSQL_PASSWORD = 'MiClave$Segura'

  Si no define MYSQL_PASSWORD, el script pedirá la contraseña de forma oculta.

  python scripts/import_inventario_csv.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import getpass
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import pymysql
    from pymysql.err import OperationalError
except ImportError:
    print("Instale dependencias: pip install -r requirements.txt", file=sys.stderr)
    raise

# Índices de columnas según cabecera del CSV (fila que empieza por "Numero inventario")
COL = {
    "numero_inventario": 0,
    "numero_contable": 1,
    "codigo_contable": 2,
    "departamento": 3,
    "area": 4,
    "usuario": 5,
    "cargo": 6,
    "descripcion": 13,
    "marca_referencia": 14,
    "service_tag": 15,
    "serial_cpu": 16,
    "observaciones": 58,
    "fecha_adquisicion": 59,
}

BAJA_PAT = re.compile(
    r"dado\s+de\s+baja|dada\s+de\s+baja|dar\s+de\s+baja|"
    r"baja\s+de\s+equipo|equipo\s+dado\s+de\s+baja|se\s+da\s+de\s+baja|"
    r"baja\s+por|se\s+dar[aá]\s+de\s+baja|disposici[oó]n\s+para\s+donaci",
    re.IGNORECASE | re.UNICODE,
)


def find_header_row(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows):
        if row and row[0].strip().lower() == "numero inventario":
            return i
    raise ValueError("No se encontró la fila de encabezados con 'Numero inventario'.")


def parse_fecha_adquisicion(raw: str) -> date | None:
    s = (raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}", s):
        return date(int(s), 1, 1)
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            try:
                return date(y, d, mo)
            except ValueError:
                return None
    return None


def trim(s: str | None, max_len: int) -> str | None:
    if s is None:
        return None
    t = s.strip()
    if not t:
        return None
    return t[:max_len]


def collect_import_rows(csv_path: Path) -> tuple[list[tuple], dict[str, int]]:
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        rows = list(csv.reader(f))
    hi = find_header_row(rows)
    records: list[tuple] = []
    stats = {"importar": 0, "omitidos_baja": 0, "omitidos_formato": 0}
    for row in rows[hi + 1 :]:
        if not row:
            continue
        inv_raw = row[COL["numero_inventario"]].strip() if len(row) > COL["numero_inventario"] else ""
        if not inv_raw.isdigit():
            continue
        if len(row) <= COL["fecha_adquisicion"]:
            stats["omitidos_formato"] += 1
            continue
        obs = row[COL["observaciones"]] if len(row) > COL["observaciones"] else ""
        if BAJA_PAT.search(obs or ""):
            stats["omitidos_baja"] += 1
            continue
        fd = parse_fecha_adquisicion(row[COL["fecha_adquisicion"]])
        records.append(
            (
                inv_raw,
                trim(row[COL["numero_contable"]], 64),
                trim(row[COL["codigo_contable"]], 64),
                trim(row[COL["departamento"]], 255),
                trim(row[COL["area"]], 255),
                trim(row[COL["usuario"]], 512),
                trim(row[COL["cargo"]], 255),
                trim(row[COL["descripcion"]], 255),
                trim(row[COL["marca_referencia"]], 512),
                trim(row[COL["service_tag"]], 255),
                trim(row[COL["serial_cpu"]], 255),
                fd,
                (obs or None),
            )
        )
        stats["importar"] += 1
    return records, stats


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    default_csv = root / "INVENTARIOS RELACION DE SISTEMAS.xls - EQUIPO COMPUTO.csv"
    p = argparse.ArgumentParser(description="Importar inventario CSV a MySQL.")
    p.add_argument("--csv", type=Path, default=default_csv, help="Ruta al CSV")
    p.add_argument("--dry-run", action="store_true", help="Solo contar, sin escribir en BD")
    args = p.parse_args()

    if not args.csv.is_file():
        print(f"No existe el archivo: {args.csv}", file=sys.stderr)
        sys.exit(1)

    records, stats = collect_import_rows(args.csv)
    print(f"Equipos a importar (sin bajas en OBSERVACIONES): {stats['importar']}")
    print(f"Omitidos por baja en observaciones: {stats['omitidos_baja']}")
    print(f"Filas descartadas por formato (sin columnas suficientes): {stats['omitidos_formato']}")

    if args.dry_run:
        return

    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    database = os.environ.get("MYSQL_DATABASE", "mtto_equipos")
    if not user:
        print("Defina MYSQL_USER (y MYSQL_PASSWORD si aplica).", file=sys.stderr)
        sys.exit(1)
    if password is None or password == "":
        password = getpass.getpass(f"Contraseña MySQL para '{user}': ")

    print(
        f"Conectando a: usuario={user!r} host={host!r} port={port} base_de_datos={database!r}\n"
        "(Debe coincidir con la conexión de MySQL Workbench: mismo host, puerto y esquema.)\n"
    )

    sql = """
    INSERT INTO equipos (
      numero_inventario, numero_contable, codigo_contable, departamento, area,
      usuario, cargo, descripcion, marca_referencia, service_tag, serial_cpu,
      fecha_adquisicion, observaciones
    ) VALUES (
      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
      numero_contable = VALUES(numero_contable),
      codigo_contable = VALUES(codigo_contable),
      departamento = VALUES(departamento),
      area = VALUES(area),
      usuario = VALUES(usuario),
      cargo = VALUES(cargo),
      descripcion = VALUES(descripcion),
      marca_referencia = VALUES(marca_referencia),
      service_tag = VALUES(service_tag),
      serial_cpu = VALUES(serial_cpu),
      fecha_adquisicion = VALUES(fecha_adquisicion),
      observaciones = VALUES(observaciones)
    """

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            autocommit=False,
        )
    except OperationalError as e:
        if e.args and e.args[0] == 1045:
            print(
                "\nMySQL rechazó usuario o contraseña (error 1045).\n"
                "- Use la misma clave con la que entra en MySQL Workbench para ESE usuario.\n"
                "- En PowerShell, con caracteres $ \" ` en la clave, use comillas simples:\n"
                "    $env:MYSQL_PASSWORD = 'su_clave_aqui'\n"
                "- O ejecute de nuevo sin MYSQL_PASSWORD y escriba la clave cuando se la pida.\n",
                file=sys.stderr,
            )
        raise

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            db_now = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'equipos'"
            )
            table_exists = cur.fetchone()[0]
            if not table_exists:
                print(
                    f"ERROR: En la base '{db_now}' no existe la tabla 'equipos'. "
                    "Ejecute en Workbench el script database/01_crear_base_y_tabla.sql en ESTE servidor.",
                    file=sys.stderr,
                )
                conn.close()
                sys.exit(1)
            for tup in records:
                cur.execute(sql, tup)
        conn.commit()
        print(f"Listo: {len(records)} sentencias INSERT/UPDATE ejecutadas y confirmadas (COMMIT).")
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            db_after = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM equipos")
            total = cur.fetchone()[0]
        print(f"Verificación en el servidor: DATABASE()={db_after!r} | filas en equipos: {total}")
        if total == 0 and len(records) > 0:
            print(
                "\nADVERTENCIA: El conteo en 'equipos' es 0 pero se intentó importar filas. "
                "Compruebe que Workbench usa el mismo host/puerto (p. ej. 127.0.0.1:3306) y la misma instancia de MySQL.",
                file=sys.stderr,
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
