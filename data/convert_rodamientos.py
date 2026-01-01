# tools/convert_rodamientos.py
"""
Convierte data/rodamientos.csv -> data/rodamientos.json (+ data/rodamientos_norm.csv)

Entrada esperada (cabeceras, pueden variar levemente):
  Serie, Referencia, d_mm, D_mm.1, B_mm
Ejemplo:
  22208, SKF 22208 E, 40, 80, 23

- "Serie" se usa como ref (clave corta, p.ej. 22208)
- "Referencia" se usa como name (lo que quieres ver en el desplegable: 'SKF 22208 E')
"""
import csv
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
IN_CSV = BASE_DIR / "data" / "rodamientos.csv"
OUT_JSON = BASE_DIR / "data" / "rodamientos.json"
OUT_CSV = BASE_DIR / "data" / "rodamientos_norm.csv"


def _detect_delimiter(sample: str) -> str:
    # Excel ES suele exportar con ';'
    if sample.count(";") > sample.count(","):
        return ";"
    return ","


def _to_float(x):
    if x is None:
        return None
    s = str(x).strip().replace(",", ".").replace("?", "")
    if not s:
        return None
    return float(s)


def main():
    if not IN_CSV.exists():
        raise FileNotFoundError(f"No existe: {IN_CSV}")

    with IN_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        delim = _detect_delimiter(sample)
        reader = csv.DictReader(f, delimiter=delim)

        items = []
        for row in reader:
            serie = (row.get("Serie") or row.get("serie") or row.get("SERIE") or "").strip()
            name = (row.get("Referencia") or row.get("referencia") or row.get("REF") or "").strip()

            # tolerar nombres alternativos de columnas
            d = row.get("d_mm") or row.get("d") or row.get("d_mm ") or row.get("d_mm\t")
            D = row.get("D_mm.1") or row.get("D_mm") or row.get("D") or row.get("D_mm ")
            B = row.get("B_mm") or row.get("B") or row.get("B_mm ")

            if not serie and not name:
                continue

            item = {
                "ref": serie if serie else name,
                "name": name if name else serie,
                "d": _to_float(d),
                "D": _to_float(D),
                "B": _to_float(B),
            }
            items.append(item)

    # ordenar por d y ref
    def key(it):
        d = it["d"] if it["d"] is not None else 1e18
        return (d, str(it.get("ref", "")))

    items.sort(key=key)

    OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV normalizado
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ref", "name", "d", "D", "B"])
        for it in items:
            w.writerow([it["ref"], it["name"], it["d"], it["D"], it["B"]])

    print(f"[OK] JSON: {OUT_JSON}")
    print(f"[OK] CSV : {OUT_CSV}")
    print(f"[OK] Items: {len(items)}")


if __name__ == "__main__":
    main()
