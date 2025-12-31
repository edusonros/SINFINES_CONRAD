# utils/catalogs.py
import os
from openpyxl import load_workbook

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XLSX = os.path.join(BASE_DIR, "data", "Lista de Planos.xlsx")


def _fmt_mm(x) -> str:
    """Convierte 60.3 -> '60,3' (estilo ES) sin ceros raros."""
    if x is None:
        return ""
    s = f"{float(x):.3f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def load_catalogs(xlsx_path: str = DEFAULT_XLSX) -> dict:
    wb = load_workbook(xlsx_path, data_only=True)

    # LISTA_MATERIALES (col A)
    ws = wb["LISTA_MATERIALES"]
    materials = []
    for r in range(1, 200):
        v = ws.cell(r, 1).value
        if v:
            materials.append(str(v).strip())

    # LISTA_EJE_TUBO: A=OD, B=thk, C=ID
    ws = wb["LISTA_EJE_TUBO"]
    tubes = []
    for r in range(2, 5000):
        od = ws.cell(r, 1).value
        thk = ws.cell(r, 2).value
        _id = ws.cell(r, 3).value
        if od is None or thk is None:
            continue
        tubes.append({"od": float(od), "thk": float(thk),
                     "id": float(_id) if _id is not None else None})

    eje_od = sorted({t["od"] for t in tubes})
    espesores_by_od = {}
    for od in eje_od:
        espesores_by_od[_fmt_mm(od)] = sorted(
            {_fmt_mm(t["thk"]) for t in tubes if t["od"] == od})

    # CAT_RODAMIENTOS: B=Referencia, C=d_mm
    ws = wb["CAT_RODAMIENTOS"]
    rodamientos = []
    for r in range(2, 2000):
        ref = ws.cell(r, 2).value
        dmm = ws.cell(r, 3).value
        Dmm = ws.cell(r, 4).value
        Bmm = ws.cell(r, 5).value
        if not ref or dmm is None:
            continue
        rodamientos.append({
            "ref": str(ref).strip(),
            "d": float(dmm),
            "D": float(Dmm) if Dmm is not None else None,
            "B": float(Bmm) if Bmm is not None else None,
        })

    # DIAMETROS Y PASOS: A=diam espira, B=pasos, C=espesor chapa
    ws = wb["DIAMETROS Y PASOS"]
    diam_espira = sorted({float(ws.cell(r, 1).value)
                         for r in range(2, 500) if ws.cell(r, 1).value is not None})
    pasos = sorted({float(ws.cell(r, 2).value)
                   for r in range(2, 500) if ws.cell(r, 2).value is not None})
    espesores_chapa = sorted({float(ws.cell(r, 3).value) for r in range(
        2, 500) if ws.cell(r, 3).value is not None})

    return {
        "materials": materials,
        "eje_od": [_fmt_mm(x) for x in eje_od],
        "espesores_by_od": espesores_by_od,
        "rodamientos": rodamientos,
        "diam_espira": [_fmt_mm(x) for x in diam_espira],
        "pasos": [_fmt_mm(x) for x in pasos],
        "espesores_chapa": [_fmt_mm(x) for x in espesores_chapa],
    }


def filter_rodamientos_por_eje(rodamientos: list, eje_od_mm_text: str) -> list:
    """Devuelve refs con d_mm < Øtubo_eje."""
    if not eje_od_mm_text:
        return []
    eje_od = float(eje_od_mm_text.replace(",", "."))
    out = [r["ref"] for r in rodamientos if r["d"] < eje_od]
    return out
