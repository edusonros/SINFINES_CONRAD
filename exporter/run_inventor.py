from pathlib import Path

try:
    import win32com.client as win32com
except ModuleNotFoundError:
    win32com = None

ILOGIC_RULE = "01_Tornillo_Sinfin"
ASSEMBLY_PATH = Path(
    r"C:\edusonros_projects\SINFINES_CONRAD\iLogic\Tornillo Sinfin_v001.iam"
)


def run_inventor():
    if win32com is None:
        raise RuntimeError("Falta pywin32. Instala con: pip install pywin32")

    inv = win32com.Dispatch("Inventor.Application")
    inv.Visible = True

    doc = inv.Documents.Open(str(ASSEMBLY_PATH), True)
    doc.Activate()

    inv.RunRule("01_Tornillo_Sinfin")

    doc.Update()
    doc.Save2(True)
