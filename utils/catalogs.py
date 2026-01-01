# utils/catalogs.py
"""
Catálogos (listas desplegables) para la definición del sinfín.

Fuente principal: data/catalogos.json (generado a partir de CSV/Excel).
Así evitamos depender de openpyxl y de fórmulas/validaciones de Excel.

Estructura esperada del JSON (ejemplo):
{
  "materials": ["S355J2+N", ...],
  "eje_od": ["60,3", "76,1", ...],
  "espesores_by_od": {"60,3": ["2", "3"], ...},
  "diam_espira": ["200", "250", ...],
  "pasos": ["100", "150", ...],
  "espesores_chapa": ["3", "4", ...],
  "tipo_disposicion": ["COAXIAL", ...],
  "posicion_motor": ["B3", "B6", ...],
  "giro": ["DERECHAS", "IZQUIERDAS"],
  "rodamientos": [{"ref":"SKF 22211 E","d":55,"D":100,"B":25}, ...],
  "eje_dim": ["40","45","50", ...]
}
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSON = os.path.join(BASE_DIR, "data", "catalogos.json")


def load_catalogs(json_path: str = DEFAULT_JSON) -> Dict[str, Any]:
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"No existe el catálogo JSON: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Garantiza claves mínimas (para evitar KeyError)
    data.setdefault("materials", [])
    data.setdefault("eje_od", [])
    data.setdefault("espesores_by_od", {})
    data.setdefault("diam_espira", [])
    data.setdefault("pasos", [])
    data.setdefault("espesores_chapa", [])
    data.setdefault("tipo_disposicion", [])
    data.setdefault("posicion_motor", [])
    data.setdefault("giro", [])
    data.setdefault("rodamientos", [])
    data.setdefault("eje_dim", [])

    return data


def _to_float_mm(text: str) -> float | None:
    if text is None:
        return None
    s = str(text).strip().replace(" ", "")
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def espesores_for_od(catalogs: Dict[str, Any], eje_od_mm_text: str) -> List[str]:
    """
    Devuelve la lista de espesores (strings) para un Ø exterior (string).
    OJO: la clave del dict suele ir como '60,3' (coma).
    """
    if not catalogs:
        return []
    od = (eje_od_mm_text or "").strip()
    if not od:
        return []
    # Normaliza: si viene con punto, prueba también con coma
    by = catalogs.get("espesores_by_od", {}) or {}
    if od in by:
        return list(by.get(od) or [])
    od_alt = od.replace(".", ",")
    if od_alt in by:
        return list(by.get(od_alt) or [])
    return []


def rodamientos_refs(catalogs: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for r in (catalogs or {}).get("rodamientos", []) or []:
        ref = r.get("ref")
        if ref and ref not in out:
            out.append(ref)
    return out


def get_rodamiento_by_ref(catalogs: Dict[str, Any], ref: str) -> Dict[str, Any] | None:
    ref = (ref or "").strip()
    if not ref:
        return None
    for r in (catalogs or {}).get("rodamientos", []) or []:
        if (r.get("ref") or "").strip() == ref:
            return r
    return None


def filter_rodamientos_por_eje(rodamientos: List[Dict[str, Any]], eje_od_mm_text: str) -> List[str]:
    """
    Devuelve referencias filtradas según Ø del tubo eje.
    Regla SIMPLE:
      - si el rodamiento tiene 'd' (diámetro interior), se admite si d < Ø_eje
      - si no hay 'd', se devuelve igualmente.
    """
    if not rodamientos:
        return []

    eje_od = _to_float_mm(eje_od_mm_text)
    if eje_od is None:
        return [r.get("ref") for r in rodamientos if r.get("ref")]

    refs: List[str] = []
    for r in rodamientos:
        ref = r.get("ref")
        if not ref:
            continue

        d_val = r.get("d", None)
        try:
            d = float(d_val) if d_val is not None else None
        except Exception:
            d = None

        if d is None or d < eje_od:
            refs.append(ref)

    # quitar duplicados manteniendo orden
    out: List[str] = []
    seen = set()
    for x in refs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
