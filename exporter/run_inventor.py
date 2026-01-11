from pathlib import Path

ILOGIC_RULE = "01_Tornillo_Sinfin"
ASSEMBLY_PATH = Path(
    r"C:\edusonros_projects\SINFINES_CONRAD\iLogic\Tornillo Sinfin_v001.iam")


def run_inventor():
    if win32com is None:
        raise RuntimeError("Falta pywin32. Instala con: pip install pywin32")

    import win32com.client

    inv = win32com.client.Dispatch("Inventor.Application")
    inv.Visible = True  # TRUE como pediste

    doc = inv.Documents.Open(str(ASSEMBLY_PATH), True)

    # Ejecutar regla iLogic
    # Si tu regla está en el IAM, esta llamada funciona:
    inv.RunRule(ILOGIC_RULE)

    # Opcional: guardar
    doc.Update()
    doc.Save2(True)
