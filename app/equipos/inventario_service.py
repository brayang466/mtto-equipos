"""Actualización y baja de equipos en inventario (superadmin)."""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

from flask import current_app

from app.constants import AREAS_LABORALES
from app.extensions import db
from app.equipos.forms import EquipoEditForm

if TYPE_CHECKING:
    from app.models import Equipo


def _strip_opt(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s or None


def _norm_area_compare(s: str) -> str:
    """Normaliza para comparar: mayúsculas, sin tildes ni diacríticos."""
    t = (s or "").strip().upper()
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def area_canonica_si_coincide(valor_inventario: str | None) -> str | None:
    """
    Si el texto del inventario coincide con alguna entrada de AREAS_LABORALES
    (misma letras ignorando mayúsculas y tildes), devuelve el texto oficial del catálogo.
    """
    if not (valor_inventario or "").strip():
        return None
    n = _norm_area_compare(valor_inventario)
    for oficial in AREAS_LABORALES:
        if _norm_area_compare(oficial) == n:
            return oficial
    return None


def choices_area_inventario(area_actual: str | None) -> list[tuple[str, str]]:
    """
    Opciones del select: lista de áreas oficiales una sola vez.
    Solo añade «(valor actual en inventario)» si el texto en BD no corresponde a ninguna área del catálogo.
    """
    cur = (area_actual or "").strip()
    canon = area_canonica_si_coincide(cur)
    choices: list[tuple[str, str]] = [("", "Seleccione…")]
    seen_valores: set[str] = set()

    if cur and canon is None and cur not in AREAS_LABORALES:
        choices.append((cur, f"{cur} (valor actual en inventario)"))
        seen_valores.add(cur)

    for a in AREAS_LABORALES:
        if a not in seen_valores:
            choices.append((a, a))
    return choices


def populate_equipo_edit_form(form: EquipoEditForm, equipo: Equipo) -> None:
    form.area.choices = choices_area_inventario(equipo.area)
    form.departamento.data = equipo.departamento
    raw_area = (equipo.area or "").strip()
    canon = area_canonica_si_coincide(raw_area)
    if canon:
        form.area.data = canon
    elif raw_area:
        form.area.data = raw_area
    else:
        form.area.data = None
    form.usuario.data = equipo.usuario
    form.cargo.data = equipo.cargo


def apply_equipo_edit_form(form: EquipoEditForm, equipo: Equipo) -> None:
    area_val = (form.area.data or "").strip()
    if area_val not in AREAS_LABORALES:
        raise ValueError("Área no válida.")
    equipo.departamento = _strip_opt(form.departamento.data)
    equipo.area = area_val
    equipo.usuario = _strip_opt(form.usuario.data)
    equipo.cargo = _strip_opt(form.cargo.data)


def eliminar_equipo(equipo: Equipo) -> None:
    """Elimina el equipo, sus solicitudes y archivos de evidencia en disco."""
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    for sol in equipo.solicitudes_mantenimiento.all():
        for adj in sol.adjuntos.all():
            path = (upload_root / adj.nombre_archivo).resolve()
            try:
                path.relative_to(upload_root)
            except ValueError:
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
    db.session.delete(equipo)
    db.session.commit()
