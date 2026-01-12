# utils/catalogs.py
"""
Carga catálogos desde JSON (data/catalogos.json) y helpers de filtrado.

Estructura esperada en catalogos.json (mínimo):
{
  "materials": [...],
  "diam_espira": [...],
  "pasos": [...],
  "espesores_chapa": [...],
  "distancia_testeros": [...],
  "rodamientos": [ {"ref":"22208","name":"SKF 22208 E","d":40,"D":80,"B":23}, ... ],
  "rodamiento_names": ["SKF 22208 E", ...]   # opcional, se puede derivar
  "eje_od": [[...],
  "espesores_by_od": { "60,3": ["2","3"], ... },
  "metricas_tornillos": ["M8",...],
  "tipo_disposicion": [...],
  "posicion_motor": [...] 
}
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSON = os.path.join(BASE_DIR, "data", "catalogos.json")


def load_catalogs(json_path: str = DEFAULT_JSON) -> Dict[str, Any]:
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"No existe el JSON de catálogos: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalizaciones suaves (para evitar KeyError)
    data.setdefault("materials", [])
    data.setdefault("diam_espira", [])
    data.setdefault("pasos", [])
    data.setdefault("espesores_chapa", [])
    data.setdefault("distancia_testeros", [])
    data.setdefault("eje_od", [])
    data.setdefault("espesores_by_od", {})
    data.setdefault("metricas_tornillos", [])
    data.setdefault("rodamientos", [])

    if "rodamiento_names" not in data or not isinstance(data["rodamiento_names"], list):
        data["rodamiento_names"] = [
            (r.get("name") or r.get("ref") or "").strip()
            for r in data.get("rodamientos", [])
            if (r.get("name") or r.get("ref"))
        ]

    # mapa name->rodamiento (para acceder rápido a d/D/B si hace falta)
    data["_rod_by_name"] = {
        (r.get("name") or r.get("ref") or "").strip(): r
        for r in data.get("rodamientos", [])
        if (r.get("name") or r.get("ref"))
    }

    return data


def _to_float(text: str) -> Optional[float]:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def tubo_id_mm(eje_od_mm_text: str, eje_thk_mm_text: str) -> Optional[float]:
    """Devuelve Ø interior del tubo eje (mm) si se puede calcular."""
    od = _to_float(eje_od_mm_text)
    thk = _to_float(eje_thk_mm_text)
    if od is None or thk is None:
        return None
    return od - 2.0 * thk


def mecanizado_diff_mm(eje_od_mm_text: str, eje_thk_mm_text: str) -> Optional[float]:
    """
    Devuelve la diferencia OD-ID (mm) para validar el mecanizado.
    La regla requiere 4 mm <= diferencia <= 6 mm.
    """
    od = _to_float(eje_od_mm_text)
    thk = _to_float(eje_thk_mm_text)
    if od is None or thk is None:
        return None
    id_mm = od - 2.0 * thk
    return od - id_mm


def is_mecanizado_ok(
    eje_od_mm_text: str,
    eje_thk_mm_text: str,
    min_diff_mm: float = 4.0,
    max_diff_mm: float = 6.0,
) -> bool:
    """Valida si la diferencia OD-ID está dentro del rango permitido."""
    diff = mecanizado_diff_mm(eje_od_mm_text, eje_thk_mm_text)
    return diff is not None and min_diff_mm <= diff <= max_diff_mm


def filter_espesores_por_od(catalogs: Dict[str, Any], eje_od_mm_text: str) -> List[str]:
    """Devuelve espesores disponibles para el OD seleccionado."""
    od = (eje_od_mm_text or "").strip()
    espes = catalogs.get("espesores_by_od", {}).get(od, [])
    return list(espes) if isinstance(espes, list) else []


def filter_rodamientos_por_tubo(catalogs: Dict[str, Any], eje_od_mm_text: str, eje_thk_mm_text: str) -> List[str]:
    """
    Filtra rodamientos en base al tubo eje.
    Regla:
      - si se conoce Ø interior (od - 2*thk) => d == Ø interior (±0.1 mm)
      - si no, pero hay Ø exterior => d < Ø exterior (regla "suave")
      - si no hay datos => devuelve todos
    Devuelve nombres (rodamiento_names).
    """
    rodamientos = catalogs.get("rodamientos", []) or []
    if not rodamientos:
        return []

    od = _to_float(eje_od_mm_text)
    tid = tubo_id_mm(eje_od_mm_text, eje_thk_mm_text)

    out: List[str] = []
    if tid is not None:
        for r in rodamientos:
            d = r.get("d", None)
            name = (r.get("name") or r.get("ref") or "").strip()
            if not name or d is None:
                continue
            try:
                d = float(d)
            except Exception:
                continue
            if abs(d - tid) <= 0.1:
                out.append(name)

    elif od is not None:
        for r in rodamientos:
            d = r.get("d", None)
            name = (r.get("name") or r.get("ref") or "").strip()
            if not name or d is None:
                continue
            try:
                d = float(d)
            except Exception:
                continue
            if d < od:
                out.append(name)

    else:
        out = [
            (r.get("name") or r.get("ref") or "").strip()
            for r in rodamientos
            if (r.get("name") or r.get("ref"))
        ]

    # quitar duplicados manteniendo orden
    seen = set()
    uniq: List[str] = []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq
