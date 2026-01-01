# app/sinfin_window.py
import os
import json
import csv
import tkinter as tk
from tkinter import ttk, messagebox

from utils.db import (
    connect,
    list_tareas_por_proceso,
    get_estado_tarea,
    set_estado_tarea,
    get_sinfin_definicion,
    set_sinfin_definicion,
)
from utils.progress import sinfin_progress, estado_from_pct


# =========================================================
# Catálogos (JSON + CSV)
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../SINFINES_CONRAD
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_CATALOG_JSON = os.path.join(DATA_DIR, "catalogos.json")
DEFAULT_EJE_TUBO_CSV = os.path.join(DATA_DIR, "Lista_eje_tubo.csv")  # Ø exterior + espesor


def _to_float(x) -> float | None:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _fmt_mm(x) -> str:
    """Formatea mm: 60.3 -> '60,3' y 60.0 -> '60'."""
    f = _to_float(x)
    if f is None:
        return ""
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.1f}".replace(".", ",")


def _load_eje_tubo_csv(csv_path: str) -> tuple[list[str], dict[str, list[str]]]:
    """
    Lee Lista_eje_tubo.csv con columnas:
      - col 1: Ø exterior (mm)
      - col 2: espesor (mm)
    Soporta separador ';' o ','.
    """
    if not os.path.exists(csv_path):
        return [], {}

    # detectar delimitador
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        sample = f.read(2048)
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","

    eje_od_set: set[str] = set()
    espesores_by_od: dict[str, list[str]] = {}

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        # saltar cabecera si existe
        rows = list(reader)

    # si la primera fila tiene texto, la tratamos como cabecera
    start = 1 if rows and any(not _to_float(c) for c in rows[0][:2]) else 0

    for r in rows[start:]:
        if len(r) < 2:
            continue
        od = _to_float(r[0])
        thk = _to_float(r[1])
        if od is None or thk is None:
            continue

        od_s = _fmt_mm(od)
        thk_s = _fmt_mm(thk)

        eje_od_set.add(od_s)
        espesores_by_od.setdefault(od_s, [])
        if thk_s and thk_s not in espesores_by_od[od_s]:
            espesores_by_od[od_s].append(thk_s)

    def _num_key(s: str) -> float:
        try:
            return float(s.replace(",", "."))
        except Exception:
            return 0.0

    eje_od = sorted(list(eje_od_set), key=_num_key)
    for k in espesores_by_od:
        espesores_by_od[k] = sorted(espesores_by_od[k], key=_num_key)

    return eje_od, espesores_by_od


def load_catalogs_json(
    json_path: str = DEFAULT_CATALOG_JSON,
    eje_tubo_csv_path: str = DEFAULT_EJE_TUBO_CSV
) -> dict:
    """
    Carga catálogos desde data/catalogos.json y completa eje_od/espesores_by_od desde data/Lista_eje_tubo.csv
    (para poder filtrar espesor de tubo por Ø exterior).
    """
    data: dict = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    # normalizar claves
    if not isinstance(data, dict):
        data = {}

    # Completar eje_od / espesores_by_od desde CSV si falta en JSON
    eje_od = data.get("eje_od") or []
    espesores_by_od = data.get("espesores_by_od") or {}

    if not eje_od or not espesores_by_od:
        eje_od_csv, espesores_by_od_csv = _load_eje_tubo_csv(eje_tubo_csv_path)
        if eje_od_csv:
            eje_od = eje_od_csv
        if espesores_by_od_csv:
            espesores_by_od = espesores_by_od_csv

    data["eje_od"] = eje_od
    data["espesores_by_od"] = espesores_by_od

    # Defaults “por si acaso”
    data.setdefault("materials", ["S275JR", "S355J2+N"])
    data.setdefault("diam_espira", [])
    data.setdefault("pasos", [])
    data.setdefault("espesores_chapa", [])
    data.setdefault("tipo_disposicion", ["COAXIAL", "ORTOGONAL", "PENDULAR"])
    data.setdefault("posicion_motor", ["B3", "B6", "B7", "B8", "V5", "V6", "OTRA"])
    data.setdefault("giro", ["DERECHAS", "IZQUIERDAS"])
    data.setdefault("rodamientos", [])
    data.setdefault("eje_dim", [])

    return data


def _find_rodamiento_by_name(rodamientos: list[dict], name: str) -> dict | None:
    name = (name or "").strip()
    if not name:
        return None
    for r in rodamientos:
        if (r.get("name") or "").strip() == name:
            return r
    return None


# =========================================================
# UI
# =========================================================
class SinfinWindow(tk.Toplevel):
    def __init__(self, parent, sinfin_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.sinfin_id = sinfin_id
        self.on_updated_callback = on_updated_callback

        self.title("Sinfín – Definición / Progreso")
        self.geometry("1120x720")
        self.configure(bg="#1e1e1e")

        # --------- catálogos ---------
        try:
            self.catalogs = load_catalogs_json()
        except Exception as e:
            self.catalogs = load_catalogs_json(json_path="__missing__")
            messagebox.showwarning(
                "Catálogos",
                f"No he podido cargar catálogos.\n\nDetalle: {e}\n\n"
                f"Revisa que exista: {DEFAULT_CATALOG_JSON}\n"
                f"y (para eje/espesor): {DEFAULT_EJE_TUBO_CSV}"
            )

        # --------- vars definición (GENERAL) ---------
        self.v_material = tk.StringVar(value="S355J2+N")
        self.v_camisa_tipo = tk.StringVar(value="ARTESA")   # ARTESA | CIRCULAR
        self.v_sentido = tk.StringVar(value="DERECHAS")     # DERECHAS | IZQUIERDAS
        self.v_long_test = tk.StringVar()                   # libre (sin validación)

        # --------- vars definición (TORNILLO) ---------
        self.v_eje_od = tk.StringVar()
        self.v_eje_thk = tk.StringVar()
        self.v_diam_espira = tk.StringVar()
        self.v_paso_1 = tk.StringVar()
        self.v_paso_2 = tk.StringVar()
        self.v_tornilleria = tk.StringVar()

        # --------- vars definición (CONDUCCIÓN) ---------
        self.v_rodamiento_ref = tk.StringVar()   # Ej: "SKF 22211 E"
        self.v_rodamiento_dim = tk.StringVar()   # Ej: "d=55  D=100  B=25"
        self.v_pos_motor = tk.StringVar()

        # --------- vars progreso ---------
        self.vars_checks = {}  # tarea_id -> IntVar

        # widgets (para refrescos)
        self.cb_mat: ttk.Combobox | None = None
        self.cb_eje_od: ttk.Combobox | None = None
        self.cb_thk: ttk.Combobox | None = None
        self.cb_diam_espira: ttk.Combobox | None = None
        self.cb_p1: ttk.Combobox | None = None
        self.cb_p2: ttk.Combobox | None = None
        self.cb_rod: ttk.Combobox | None = None
        self.cb_pos_motor: ttk.Combobox | None = None

        self._build_ui()
        self.load_all()

    # ---------------- UI ----------------
    def _build_ui(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=12)

        self.tab_def = tk.Frame(self.nb, bg="#1e1e1e")
        self.tab_prog = tk.Frame(self.nb, bg="#1e1e1e")
        self.nb.add(self.tab_def, text="Definición")
        self.nb.add(self.tab_prog, text="Progreso")

        self._build_def_tab()
        self._build_progress_tab()

    # ---------------- DEFINICIÓN ----------------
    def _build_def_tab(self):
        # Top bar
        top = tk.Frame(self.tab_def, bg="#1e1e1e")
        top.pack(fill="x", padx=10, pady=(10, 8))

        tk.Label(
            top, text="DEFINICIÓN DEL SINFÍN",
            fg="white", bg="#1e1e1e",
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        ttk.Button(top, text="💾 Guardar definición",
                   command=self.save_definition).pack(side="right", padx=6)
        ttk.Button(top, text="🔄 Recargar", command=self.load_definition).pack(
            side="right", padx=6)

        body = tk.Frame(self.tab_def, bg="#1e1e1e")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        # Izquierda: secciones
        left = tk.Frame(body, bg="#1e1e1e", width=230)
        left.pack(side="left", fill="y")

        tk.Label(left, text="Secciones", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        self.v_section = tk.StringVar(value="GENERAL")

        def add_section(text, value):
            ttk.Radiobutton(
                left, text=text, value=value,
                variable=self.v_section,
                command=self._show_section
            ).pack(anchor="w", pady=3)

        add_section("General", "GENERAL")
        add_section("Parte 001 – Tornillo", "TORNILLO")
        add_section("Parte 002 – Camisa", "CAMISA")
        add_section("Parte 003 – Conducción", "CONDUCCION")
        add_section("Parte 004 – Conducido", "CONDUCIDO")

        # Separador vertical
        tk.Frame(body, bg="#333333", width=2).pack(side="left", fill="y", padx=10)

        # Derecha: contenido
        self.right = tk.Frame(body, bg="#1e1e1e")
        self.right.pack(side="left", fill="both", expand=True)

        # Frames de secciones
        self.f_general = tk.Frame(self.right, bg="#1e1e1e")
        self.f_tornillo = tk.Frame(self.right, bg="#1e1e1e")
        self.f_camisa = tk.Frame(self.right, bg="#1e1e1e")
        self.f_conduccion = tk.Frame(self.right, bg="#1e1e1e")
        self.f_conducido = tk.Frame(self.right, bg="#1e1e1e")

        for f in (self.f_general, self.f_tornillo, self.f_camisa, self.f_conduccion, self.f_conducido):
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_def_general(self.f_general)
        self._build_def_tornillo(self.f_tornillo)
        self._build_def_camisa(self.f_camisa)
        self._build_def_conduccion(self.f_conduccion)
        self._build_def_conducido(self.f_conducido)

        self._show_section()

        # Aplicar catálogos a combos (una vez creados)
        self._apply_catalog_values()

    def _show_section(self):
        sec = self.v_section.get()
        mapping = {
            "GENERAL": self.f_general,
            "TORNILLO": self.f_tornillo,
            "CAMISA": self.f_camisa,
            "CONDUCCION": self.f_conduccion,
            "CONDUCIDO": self.f_conducido,
        }
        for k, f in mapping.items():
            if k == sec:
                f.lift()

    def _grid_form_row(self, parent, r, label, widget):
        tk.Label(parent, text=label, fg="#cccccc", bg="#1e1e1e",
                 font=("Segoe UI", 10)).grid(row=r, column=0, sticky="w", pady=8)
        widget.grid(row=r, column=1, sticky="we", pady=8)
        return r + 1

    def _build_def_general(self, parent):
        tk.Label(parent, text="GENERAL", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        parent.grid_columnconfigure(1, weight=1)
        r = 1

        self.cb_mat = ttk.Combobox(parent, textvariable=self.v_material, state="readonly")
        r = self._grid_form_row(parent, r, "Material", self.cb_mat)

        # Camisa tipo
        box_cam = tk.Frame(parent, bg="#1e1e1e")
        ttk.Radiobutton(box_cam, text="Artesa", value="ARTESA", variable=self.v_camisa_tipo).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(box_cam, text="Tubo circular", value="CIRCULAR", variable=self.v_camisa_tipo).pack(side="left")
        r = self._grid_form_row(parent, r, "Forma de la camisa", box_cam)

        # Giro
        box_giro = tk.Frame(parent, bg="#1e1e1e")
        ttk.Radiobutton(box_giro, text="A derechas", value="DERECHAS", variable=self.v_sentido).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(box_giro, text="A izquierdas", value="IZQUIERDAS", variable=self.v_sentido).pack(side="left")
        r = self._grid_form_row(parent, r, "Sentido de giro", box_giro)

        ent_L = ttk.Entry(parent, textvariable=self.v_long_test)
        r = self._grid_form_row(parent, r, "Longitud entre testeros (mm) [libre]", ent_L)

        tk.Label(
            parent,
            text="(Posición motorreductor se define en Conducción.)",
            fg="#777777", bg="#1e1e1e", font=("Segoe UI", 9)
        ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_def_tornillo(self, parent):
        tk.Label(parent, text="PARTE 001 – TORNILLO", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        parent.grid_columnconfigure(1, weight=1)
        r = 1

        self.cb_eje_od = ttk.Combobox(parent, textvariable=self.v_eje_od, state="readonly")
        self.cb_eje_od.bind("<<ComboboxSelected>>", lambda e: self._on_eje_od_changed())
        r = self._grid_form_row(parent, r, "Ø exterior tubo eje (mm)", self.cb_eje_od)

        self.cb_thk = ttk.Combobox(parent, textvariable=self.v_eje_thk, state="readonly")
        self.cb_thk.bind("<<ComboboxSelected>>", lambda e: self._on_eje_thk_changed())
        r = self._grid_form_row(parent, r, "Espesor tubo eje (mm)", self.cb_thk)

        self.cb_diam_espira = ttk.Combobox(parent, textvariable=self.v_diam_espira, state="readonly")
        r = self._grid_form_row(parent, r, "Ø exterior espira (mm)", self.cb_diam_espira)

        self.cb_p1 = ttk.Combobox(parent, textvariable=self.v_paso_1, state="readonly")
        r = self._grid_form_row(parent, r, "Paso 1 (mm)", self.cb_p1)

        self.cb_p2 = ttk.Combobox(parent, textvariable=self.v_paso_2, state="readonly")
        r = self._grid_form_row(parent, r, "Paso 2 (mm) [opcional]", self.cb_p2)

        ent_tor = ttk.Entry(parent, textvariable=self.v_tornilleria)
        r = self._grid_form_row(parent, r, "Tornillería (nº tornillos)", ent_tor)

    def _build_def_camisa(self, parent):
        tk.Label(parent, text="PARTE 002 – CAMISA", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        tk.Label(
            parent,
            text="(Aquí meteremos: distancia entre testeros, espesores chapa, bocas, ventana inspección, etc.)",
            fg="#777777", bg="#1e1e1e", font=("Segoe UI", 9)
        ).pack(anchor="w")

    def _build_def_conduccion(self, parent):
        tk.Label(parent, text="PARTE 003 – CONDUCCIÓN", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        parent.grid_columnconfigure(1, weight=1)
        r = 1

        self.cb_rod = ttk.Combobox(parent, textvariable=self.v_rodamiento_ref, state="readonly")
        self.cb_rod.bind("<<ComboboxSelected>>", lambda e: self._on_rodamiento_selected())
        r = self._grid_form_row(parent, r, "Rodamiento (referencia)", self.cb_rod)

        ent_dim = ttk.Entry(parent, textvariable=self.v_rodamiento_dim, state="readonly")
        r = self._grid_form_row(parent, r, "Dimensiones (d / D / B)", ent_dim)

        self.cb_pos_motor = ttk.Combobox(parent, textvariable=self.v_pos_motor, state="readonly")
        r = self._grid_form_row(parent, r, "Posición motorreductor-eje", self.cb_pos_motor)

    def _build_def_conducido(self, parent):
        tk.Label(parent, text="PARTE 004 – CONDUCIDO", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        tk.Label(
            parent,
            text="(Pendiente: brida, prensaestopas, bancada, rodamiento, sellado...)",
            fg="#777777", bg="#1e1e1e", font=("Segoe UI", 9)
        ).pack(anchor="w")

    def _apply_catalog_values(self):
        # GENERAL
        if self.cb_mat:
            self.cb_mat["values"] = self.catalogs.get("materials", [])
            if self.v_material.get().strip() and self.v_material.get() not in self.cb_mat["values"]:
                # si el valor no está, lo dejamos pero el combo seguirá funcionando
                pass

        # TORNILLO
        if self.cb_eje_od:
            self.cb_eje_od["values"] = self.catalogs.get("eje_od", [])

        if self.cb_diam_espira:
            self.cb_diam_espira["values"] = self.catalogs.get("diam_espira", [])

        if self.cb_p1:
            self.cb_p1["values"] = self.catalogs.get("pasos", [])

        if self.cb_p2:
            self.cb_p2["values"] = self.catalogs.get("pasos", [])

        # CONDUCCIÓN
        if self.cb_pos_motor:
            self.cb_pos_motor["values"] = self.catalogs.get("posicion_motor", [])

        # Dependientes
        self._refresh_espesores()
        self._refresh_rodamientos()

    # ---- callbacks / refresh ----
    def _on_eje_od_changed(self):
        self._refresh_espesores()
        self._refresh_rodamientos()

    def _on_eje_thk_changed(self):
        self._refresh_rodamientos()

    def _refresh_espesores(self):
        """Carga espesores según Ø exterior seleccionado."""
        if not self.cb_thk:
            return

        od = (self.v_eje_od.get() or "").strip()
        espesores_by_od = self.catalogs.get("espesores_by_od", {}) or {}
        espes = espesores_by_od.get(od, [])

        self.cb_thk["values"] = espes

        cur = (self.v_eje_thk.get() or "").strip()
        if cur and cur in espes:
            return

        # si el actual no vale, dejamos el primero si existe
        if espes:
            self.v_eje_thk.set(espes[0])
        else:
            self.v_eje_thk.set("")

    def _refresh_rodamientos(self):
        """Rellena rodamientos filtrados por el eje (aprox)."""
        if not self.cb_rod:
            return

        rodamientos = self.catalogs.get("rodamientos", []) or []

        od = _to_float(self.v_eje_od.get())
        thk = _to_float(self.v_eje_thk.get())

        limit = None
        if od is not None and thk is not None:
            eje_id = od - 2.0 * thk
            if eje_id and eje_id > 0:
                limit = eje_id
            else:
                limit = od
        elif od is not None:
            limit = od

        filtered = []
        for r in rodamientos:
            d = r.get("d")
            if limit is None:
                filtered.append(r)
            else:
                try:
                    if float(d) <= float(limit) + 1e-6:
                        filtered.append(r)
                except Exception:
                    filtered.append(r)

        names = [str(r.get("name", "")).strip() for r in filtered if str(r.get("name", "")).strip()]
        # quitar duplicados manteniendo orden
        seen = set()
        out = []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)

        self.cb_rod["values"] = out

        # Si lo seleccionado ya no está, lo borramos
        cur = (self.v_rodamiento_ref.get() or "").strip()
        if cur and cur not in out:
            self.v_rodamiento_ref.set("")
            self.v_rodamiento_dim.set("")
        else:
            # refresca dims
            self._on_rodamiento_selected()

    def _on_rodamiento_selected(self):
        item = _find_rodamiento_by_name(self.catalogs.get("rodamientos", []), self.v_rodamiento_ref.get())
        if not item:
            self.v_rodamiento_dim.set("")
            return
        d = _fmt_mm(item.get("d"))
        D = _fmt_mm(item.get("D"))
        B = _fmt_mm(item.get("B"))
        parts = []
        if d:
            parts.append(f"d={d}")
        if D:
            parts.append(f"D={D}")
        if B:
            parts.append(f"B={B}")
        self.v_rodamiento_dim.set("  ".join(parts))

    # ---------------- PROGRESO ----------------
    def _build_progress_tab(self):
        top = tk.Frame(self.tab_prog, bg="#1e1e1e")
        top.pack(fill="x", padx=16, pady=12)

        tk.Label(
            top, text="Progreso sinfín:",
            fg="white", bg="#1e1e1e",
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        self.lbl_pct = tk.Label(
            top, text="",
            fg="#00bcd4", bg="#1e1e1e",
            font=("Segoe UI", 12, "bold")
        )
        self.lbl_pct.pack(side="left", padx=10)

        ttk.Button(top, text="💾 Guardar", command=self.save_progress).pack(
            side="right", padx=6)
        ttk.Button(top, text="🔄 Recargar", command=self.load_progress).pack(
            side="right", padx=6)

        container = tk.Frame(self.tab_prog, bg="#1e1e1e")
        container.pack(fill="both", expand=True, padx=16, pady=10)

        self.canvas = tk.Canvas(container, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg="#1e1e1e")

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ---------------- LOAD/SAVE ----------------
    def load_all(self):
        self.load_definition()
        self.load_progress()

    # ===== Definición =====
    def load_definition(self):
        con = connect()
        d = get_sinfin_definicion(con, self.sinfin_id)
        con.close()

        # GENERAL
        self.v_material.set(d.get("material", self.v_material.get()))
        self.v_camisa_tipo.set(d.get("camisa_tipo", self.v_camisa_tipo.get()))
        self.v_sentido.set(d.get("sentido_giro", self.v_sentido.get()))
        self.v_long_test.set(d.get("long_entre_testeros", self.v_long_test.get()))

        # TORNILLO
        self.v_eje_od.set(d.get("eje_od", self.v_eje_od.get()))
        self.v_eje_thk.set(d.get("eje_thk", self.v_eje_thk.get()))
        self.v_diam_espira.set(d.get("diam_espira", self.v_diam_espira.get()))
        self.v_paso_1.set(d.get("paso_1", self.v_paso_1.get()))
        self.v_paso_2.set(d.get("paso_2", self.v_paso_2.get()))
        self.v_tornilleria.set(d.get("tornilleria_n", self.v_tornilleria.get()))

        # CONDUCCIÓN
        self.v_rodamiento_ref.set(d.get("rodamiento_ref", self.v_rodamiento_ref.get()))
        self.v_pos_motor.set(d.get("pos_motor", self.v_pos_motor.get()))

        # refrescos dependientes
        self._refresh_espesores()
        self._refresh_rodamientos()
        self._on_rodamiento_selected()

    def save_definition(self):
        defin = {
            # GENERAL
            "material": self.v_material.get().strip(),
            "camisa_tipo": self.v_camisa_tipo.get().strip(),
            "sentido_giro": self.v_sentido.get().strip(),
            "long_entre_testeros": self.v_long_test.get().strip(),

            # TORNILLO
            "eje_od": self.v_eje_od.get().strip(),
            "eje_thk": self.v_eje_thk.get().strip(),
            "diam_espira": self.v_diam_espira.get().strip(),
            "paso_1": self.v_paso_1.get().strip(),
            "paso_2": self.v_paso_2.get().strip(),
            "tornilleria_n": self.v_tornilleria.get().strip(),

            # CONDUCCIÓN
            "rodamiento_ref": self.v_rodamiento_ref.get().strip(),
            "pos_motor": self.v_pos_motor.get().strip(),

            # útiles para cálculos
            "_num": {
                "long_entre_testeros": _to_float(self.v_long_test.get()),
                "eje_od": _to_float(self.v_eje_od.get()),
                "eje_thk": _to_float(self.v_eje_thk.get()),
                "diam_espira": _to_float(self.v_diam_espira.get()),
                "paso_1": _to_float(self.v_paso_1.get()),
                "paso_2": _to_float(self.v_paso_2.get()),
                "tornilleria_n": _to_float(self.v_tornilleria.get()),
            }
        }

        # añadir dims de rodamiento si existe
        item = _find_rodamiento_by_name(self.catalogs.get("rodamientos", []), defin["rodamiento_ref"])
        if item:
            defin["_num"]["rodamiento_d"] = item.get("d")
            defin["_num"]["rodamiento_D"] = item.get("D")
            defin["_num"]["rodamiento_B"] = item.get("B")
            defin["rodamiento_serie"] = item.get("serie")

        con = connect()
        set_sinfin_definicion(con, self.sinfin_id, defin)
        con.close()

        if self.on_updated_callback:
            self.on_updated_callback()

        messagebox.showinfo("Definición", "Definición guardada.")

    # ===== Progreso =====
    def load_progress(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.vars_checks.clear()

        con = connect()
        procs = list_tareas_por_proceso(con)

        row = 0
        for p in procs:
            title = tk.Label(
                self.inner,
                text=p["nombre"].upper(),
                fg="white", bg="#1e1e1e",
                font=("Segoe UI", 11, "bold")
            )
            title.grid(row=row, column=0, sticky="w", pady=(10, 2))
            row += 1

            for t in p["tareas"]:
                v = tk.IntVar(value=get_estado_tarea(con, self.sinfin_id, t["id"]))
                self.vars_checks[t["id"]] = v

                cb = tk.Checkbutton(
                    self.inner,
                    text=t["nombre"],
                    variable=v,
                    command=self.save_progress,
                    bg="#1e1e1e",
                    fg="#cccccc",
                    activebackground="#1e1e1e",
                    activeforeground="#ffffff",
                    selectcolor="#1e1e1e",
                    anchor="w"
                )
                cb.grid(row=row, column=0, sticky="w", pady=1)
                row += 1

        pct = sinfin_progress(con, self.sinfin_id)
        self.lbl_pct.config(text=f"{pct:.1f}%  ({estado_from_pct(pct)})")
        con.close()

    def save_progress(self):
        con = connect()
        for tarea_id, v in self.vars_checks.items():
            set_estado_tarea(con, self.sinfin_id, tarea_id, v.get())

        pct = sinfin_progress(con, self.sinfin_id)
        self.lbl_pct.config(text=f"{pct:.1f}%  ({estado_from_pct(pct)})")
        con.close()

        if self.on_updated_callback:
            self.on_updated_callback()
