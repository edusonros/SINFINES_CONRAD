import csv
import math
from pathlib import Path
import json
from pathlib import Path


ILOGIC_DIR = Path(r"C:\edusonros_projects\SINFINES_CONRAD\iLogic")
CSV_PATH = ILOGIC_DIR / "params.csv"
ASSEMBLY_PATH = Path(
    r"C:\edusonros_projects\SINFINES_CONRAD\Design\Tornillo_Sinfin_v001.iam"
)


def _to_float(x, *, field=""):
    s = str(x).strip().replace(",", ".")
    if not s:
        raise ValueError(f"Campo vacío: {field}")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"No se puede convertir a número ({field}): {x!r}")


def export_params_to_json(definicion: dict, json_path: Path) -> Path:
    payload = {"global": definicion}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json_path


def fnum(x, default=None) -> float:
    if x is None or str(x).strip() == "":
        if default is None:
            raise ValueError("Número vacío")
        return float(default)
    return float(str(x).strip().replace(",", "."))


def export_params_to_csv(definicion: dict):
    """
    definicion = JSON completo del sinfín
    """

    # --- Datos base desde la app ---
    L_app = fnum(definicion["longitud_entre_testeros"])
    paso = fnum(definicion["paso_espira"])
    espesor_testero = fnum(definicion.get("espesor_testero", 10), default=10)

    diam_tubo_ext = fnum(definicion["diametro_tubo"])
    espesor_tubo = fnum(definicion["espesor_tubo"])
    diam_espira = fnum(definicion["diametro_espira"])
    espesor_chapa = fnum(definicion["espesor_chapa"])

    # --- Correcciones industriales ---
    HOLGURA_MANGONES = 100  # 50 + 50

    L_inventor = L_app - (2 * espesor_testero) - HOLGURA_MANGONES
    num_espiras = L_inventor / paso

    params = {
        "Largo": round(L_inventor, 2),
        "DiametroExterior": diam_tubo_ext,
        "Espesor": espesor_tubo,
        "DiametroInterior": diam_tubo_ext - 2 * espesor_tubo,
        "DiametroExteriorEspira": diam_espira,
        "Espesor_Chapa": espesor_chapa,
        "Paso_Espira": paso,
        "Num_Espiras": int(math.floor(num_espiras)),
        "Mangon_Diametro": 50,
        "Mangon_Longitud": 60,
    }

    ILOGIC_DIR.mkdir(exist_ok=True)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for k, v in params.items():
            writer.writerow([k, v])

    return CSV_PATH
