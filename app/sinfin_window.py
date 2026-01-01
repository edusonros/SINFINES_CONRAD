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
from utils.catalogs import (
    load_catalogs,
    espesores_for_od,
    filter_rodamientos_por_eje,
    rodamientos_refs,
    get_rodamiento_by_ref,
)


def _to_number(s: str):
    """Acepta '60,3' o '60.3'. Devuelve float o None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_mm(x) -> str:
    """Formatea mm a string estilo ES: '60,3' y sin ',0'."""
    if x is None:
        return ""
    try:
        f = float(x)
    except Exception:
        return str(x).strip()

    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    s = f"{f:.1f}".replace(".", ",")
    return s


class SinfinWindow(tk.Toplevel):
    def __init__(self, parent, sinfin_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.sinfin_id = sinfin_id
        self.on_updated_callback = on_updated_callback

        self.title("Sinfín – Definición / Progreso")
        self.geometry("1100x720")
        self.configure(bg="#1e1e1e")

        # Cargar catálogos (JSON)
        self.catalogs = load_catalogs()

        # ===== Vars - GENERAL =====
        self.v_material = tk.StringVar()
        self.v_camisa_tipo = tk.StringVar(value="ARTESA")  # ARTESA | CIRCULAR
        self.v_sentido = tk.StringVar(
            value="DERECHAS")  # DERECHAS | IZQUIERDAS
        self.v_long_test = tk.StringVar()
        self.v_tipo_disposicion = tk.StringVar()
        self.v_observaciones = tk.StringVar()

        # ===== Vars - PARTE 001 (TORNILLO) =====
        self.v_eje_od = tk.StringVar()
        self.v_eje_thk = tk.StringVar()
        self.v_diam_ext_espira = tk.StringVar()
        self.v_espesor_espira = tk.StringVar()
        self.v_paso_1 = tk.StringVar()
        self.v_paso_2 = tk.StringVar()
        self.v_paso_3 = tk.StringVar()
        self.v_tornillos_metrica = tk.StringVar()
        self.v_tornillos_num = tk.StringVar()
        self.v_mangon_conduccion_d = tk.StringVar()
        self.v_mangon_conducido_d = tk.StringVar()

        # Tornillo en tramos
        self.v_num_tramos = tk.StringVar(value="1")
        self.v_num_mangones_intermedios = tk.StringVar(value="0")
        self.v_sujecion_mangon_intermedio = tk.StringVar(value="NINGUNA")

        # ===== Vars - PARTE 002 (CAMISA) =====
        # Circular
        self.v_camisa_tubo_od = tk.StringVar()
        self.v_camisa_tubo_id = tk.StringVar()
        self.v_camisa_testeros_thk = tk.StringVar()
        self.v_camisa_ventana = tk.StringVar()
        self.v_camisa_boca_entrada = tk.StringVar()
        self.v_camisa_boca_salida = tk.StringVar()
        self.v_camisa_suj_mangon = tk.StringVar()

        # Artesa
        self.v_artesa_chapa = tk.StringVar()
        self.v_artesa_testeros_thk = tk.StringVar()
        self.v_artesa_ventana = tk.StringVar()
        self.v_artesa_suj_mangon = tk.StringVar()
        self.v_artesa_boca_entrada = tk.StringVar()
        self.v_artesa_boca_salida = tk.StringVar()

        # ===== Vars - PARTE 003 (CONDUCCIÓN) =====
        self.v_rodamiento_ref = tk.StringVar()
        self.v_pos_motor = tk.StringVar()

        # ===== Vars - PARTE 004 (CONDUCIDO) =====
        self.v_conducido_brida = tk.StringVar()
        self.v_conducido_prensaestopas = tk.StringVar()
        self.v_conducido_bancada = tk.StringVar()
        self.v_conducido_cjto_rodamiento = tk.StringVar()
        self.v_conducido_sellado = tk.StringVar()

        # ===== Vars progreso =====
        self.vars_checks = {}  # tarea_id -> IntVar

        self._build_ui()
        self.load_all()

    # ---------------- UI ----------------
    def _build_ui(self):
        # Notebook (pestañas más visibles)
        style = ttk.Style()
        style.configure("Conrad.TNotebook",
                        background="#1e1e1e", borderwidth=0)
        style.configure(
            "Conrad.TNotebook.Tab",
            font=("Segoe UI", 11, "bold"),
            padding=(20, 12),
            background="#2b2b2b",
            foreground="white",
        )
        style.map(
            "Conrad.TNotebook.Tab",
            background=[("selected", "#00bcd4"), ("active", "#3a3a3a")],
            foreground=[("selected", "#000000"), ("active", "white")],
        )

        self.nb = ttk.Notebook(self, style="Conrad.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=14, pady=12)

        self.tab_def = tk.Frame(self.nb, bg="#1e1e1e")
        self.tab_prog = tk.Frame(self.nb, bg="#1e1e1e")

        self.nb.add(self.tab_def, text="Definición")
        self.nb.add(self.tab_prog, text="Progreso")

        self._build_def_tab()
        self._build_progress_tab()

    def _build_def_tab(self):
        top = tk.Frame(self.tab_def, bg="#1e1e1e")
        top.pack(fill="x", padx=10, pady=(10, 8))

        tk.Label(
            top,
            text="DEFINICIÓN DEL SINFÍN",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        ttk.Button(top, text="💾 Guardar definición", command=self.save_definition).pack(
            side="right", padx=6
        )
        ttk.Button(top, text="🔄 Recargar", command=self.load_definition).pack(
            side="right", padx=6
        )

        body = tk.Frame(self.tab_def, bg="#1e1e1e")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        # Lateral: secciones
        left = tk.Frame(body, bg="#1e1e1e")
        left.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(
            left, text="Secciones", fg="white", bg="#1e1e1e", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 6))

        self.section = tk.StringVar(value="GENERAL")

        def add_section(text, key):
            rb = tk.Radiobutton(
                left,
                text=text,
                value=key,
                variable=self.section,
                command=self._show_section,
                bg="#1e1e1e",
                fg="#cccccc",
                selectcolor="#1e1e1e",
                activebackground="#1e1e1e",
                activeforeground="#ffffff",
                anchor="w",
            )
            rb.pack(fill="x", anchor="w", pady=2)

        add_section("General", "GENERAL")
        add_section("Parte 001 – Tornillo", "T001")
        add_section("Parte 002 – Camisa", "T002")
        add_section("Parte 003 – Conducción", "T003")
        add_section("Parte 004 – Conducido", "T004")

        # Panel derecho: contenido variable
        self.right = tk.Frame(body, bg="#1e1e1e")
        self.right.pack(side="left", fill="both", expand=True)

        self.frames = {}

        self.frames["GENERAL"] = tk.Frame(self.right, bg="#1e1e1e")
        self.frames["T001"] = tk.Frame(self.right, bg="#1e1e1e")
        self.frames["T002"] = tk.Frame(self.right, bg="#1e1e1e")
        self.frames["T003"] = tk.Frame(self.right, bg="#1e1e1e")
        self.frames["T004"] = tk.Frame(self.right, bg="#1e1e1e")

        for f in self.frames.values():
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_def_general(self.frames["GENERAL"])
        self._build_def_tornillo(self.frames["T001"])
        self._build_def_camisa(self.frames["T002"])
        self._build_def_conduccion(self.frames["T003"])
        self._build_def_conducido(self.frames["T004"])

        self._show_section()

    def _section_title(self, parent, title: str):
        tk.Label(
            parent, text=title, fg="white", bg="#1e1e1e", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))

    def _row(self, parent, label: str, widget):
        row = tk.Frame(parent, bg="#1e1e1e")
        row.pack(fill="x", pady=6)
        tk.Label(
            row, text=label, fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 10), width=30, anchor="w"
        ).pack(side="left")
        widget.pack(side="left", fill="x", expand=True)
        return row

    def _build_def_general(self, parent):
        self._section_title(parent, "GENERAL")

        mats = self.catalogs.get("materials", [])
        cb_mat = ttk.Combobox(
            parent, textvariable=self.v_material, values=mats, state="readonly")
        self._row(parent, "Material", cb_mat)

        # Camisa tipo (excluyente)
        box_cam = tk.Frame(parent, bg="#1e1e1e")
        rb1 = ttk.Radiobutton(
            box_cam, text="Artesa", value="ARTESA", variable=self.v_camisa_tipo, command=self._on_camisa_changed
        )
        rb2 = ttk.Radiobutton(
            box_cam, text="Tubo circular", value="CIRCULAR", variable=self.v_camisa_tipo, command=self._on_camisa_changed
        )
        rb1.pack(side="left", padx=(0, 12))
        rb2.pack(side="left")
        self._row(parent, "Forma de la camisa", box_cam)

        # Sentido giro (excluyente)
        box_giro = tk.Frame(parent, bg="#1e1e1e")
        rg1 = ttk.Radiobutton(box_giro, text="A derechas",
                              value="DERECHAS", variable=self.v_sentido)
        rg2 = ttk.Radiobutton(box_giro, text="A izquierdas",
                              value="IZQUIERDAS", variable=self.v_sentido)
        rg1.pack(side="left", padx=(0, 12))
        rg2.pack(side="left")
        self._row(parent, "Sentido de giro", box_giro)

        ent_L = ttk.Entry(parent, textvariable=self.v_long_test)
        self._row(parent, "Longitud entre testeros (mm) [libre]", ent_L)

        # Tipo disposición motorreductor-eje
        tipos = self.catalogs.get("tipo_disposicion", [])
        cb_tipo = ttk.Combobox(
            parent, textvariable=self.v_tipo_disposicion, values=tipos, state="readonly")
        self._row(parent, "Tipo disposición motorreductor-eje", cb_tipo)

        # Observaciones
        ent_obs = ttk.Entry(parent, textvariable=self.v_observaciones)
        self._row(parent, "Observaciones", ent_obs)

        tk.Label(
            parent,
            text="(Posición motorreductor se define en Conducción.)",
            fg="#777777",
            bg="#1e1e1e",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(10, 0))

    def _build_def_tornillo(self, parent):
        self._section_title(parent, "PARTE 001 – TORNILLO")

        ods = self.catalogs.get("eje_od", [])
        self.cb_od = ttk.Combobox(
            parent, textvariable=self.v_eje_od, values=ods, state="readonly")
        self._row(parent, "Ø exterior tubo eje (mm)", self.cb_od)
        self.cb_od.bind("<<ComboboxSelected>>",
                        lambda e: self._refresh_espesores())

        # Espesor tubo (filtrado por OD)
        self.cb_thk = ttk.Combobox(
            parent, textvariable=self.v_eje_thk, values=[], state="readonly")
        self._row(parent, "Espesor tubo eje (mm)", self.cb_thk)

        diam = self.catalogs.get("diam_espira", [])
        cb_de = ttk.Combobox(
            parent, textvariable=self.v_diam_ext_espira, values=diam, state="readonly")
        self._row(parent, "Ø exterior espira (mm)", cb_de)

        espes_chapa = self.catalogs.get("espesores_chapa", [])
        cb_esp = ttk.Combobox(
            parent, textvariable=self.v_espesor_espira, values=espes_chapa, state="readonly")
        self._row(parent, "Espesor espira (mm)", cb_esp)

        pasos = self.catalogs.get("pasos", [])
        cb_p1 = ttk.Combobox(parent, textvariable=self.v_paso_1,
                             values=pasos, state="readonly")
        cb_p2 = ttk.Combobox(parent, textvariable=self.v_paso_2,
                             values=pasos, state="readonly")
        cb_p3 = ttk.Combobox(parent, textvariable=self.v_paso_3,
                             values=pasos, state="readonly")
        self._row(parent, "Paso 1 (mm)", cb_p1)
        self._row(parent, "Paso 2 (mm) [opcional]", cb_p2)
        self._row(parent, "Paso 3 (mm) [opcional]", cb_p3)

        # Tornillería (métrica)
        metricas = [f"M{x}" for x in (
            8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30)]
        cb_met = ttk.Combobox(
            parent, textvariable=self.v_tornillos_metrica, values=metricas, state="readonly")
        self._row(parent, "Tornillería (métrica)", cb_met)

        ent_num = ttk.Entry(parent, textvariable=self.v_tornillos_num)
        self._row(parent, "Tornillería (nº tornillos)", ent_num)

        # Mangones conducción / conducido (macizos)
        dims = self.catalogs.get("eje_dim", [])
        cb_m1 = ttk.Combobox(
            parent, textvariable=self.v_mangon_conduccion_d, values=dims, state="readonly")
        cb_m2 = ttk.Combobox(
            parent, textvariable=self.v_mangon_conducido_d, values=dims, state="readonly")
        self._row(parent, "Mangón conducción Ø (mm)", cb_m1)
        self._row(parent, "Mangón conducido Ø (mm)", cb_m2)

        # Tornillo en tramos
        ent_tr = ttk.Entry(parent, textvariable=self.v_num_tramos)
        ent_mi = ttk.Entry(
            parent, textvariable=self.v_num_mangones_intermedios)
        self._row(parent, "Nº tramos tornillo", ent_tr)
        self._row(parent, "Nº mangones intermedios", ent_mi)

        suj = ["NINGUNA", "SOPORTE CAMISA", "ABRAZADERA", "CARTELA/CHAPA"]
        cb_suj = ttk.Combobox(
            parent, textvariable=self.v_sujecion_mangon_intermedio, values=suj, state="readonly")
        self._row(parent, "Sujeción mangón intermedio", cb_suj)

        self._refresh_espesores()

    def _build_def_camisa(self, parent):
        self._section_title(parent, "PARTE 002 – CAMISA")

        self.camisa_container = tk.Frame(parent, bg="#1e1e1e")
        self.camisa_container.pack(fill="both", expand=True)

        self._render_camisa_panel()

    def _render_camisa_panel(self):
        for w in self.camisa_container.winfo_children():
            w.destroy()

        if self.v_camisa_tipo.get().strip().upper() == "CIRCULAR":
            tk.Label(
                self.camisa_container,
                text="PARTE 002A: CAMISA TUBO Ø",
                fg="white",
                bg="#1e1e1e",
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w", pady=(0, 10))

            self._row(self.camisa_container, "Distancia entre testeros", ttk.Entry(
                self.camisa_container, textvariable=self.v_long_test))
            self._row(self.camisa_container, "Tubo Ø exterior", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_tubo_od))
            self._row(self.camisa_container, "Tubo Ø interior", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_tubo_id))
            self._row(self.camisa_container, "Testeros (espesor)", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_testeros_thk))
            self._row(self.camisa_container, "Ventana inspección", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_ventana))
            self._row(self.camisa_container, "Cjto. sujeción mangón intermedio", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_suj_mangon))
            self._row(self.camisa_container, "Boca entrada", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_boca_entrada))
            self._row(self.camisa_container, "Boca salida", ttk.Entry(
                self.camisa_container, textvariable=self.v_camisa_boca_salida))

        else:
            tk.Label(
                self.camisa_container,
                text="PARTE 002B: CAMISA ARTESA",
                fg="white",
                bg="#1e1e1e",
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w", pady=(0, 10))

            self._row(self.camisa_container, "Distancia entre testeros", ttk.Entry(
                self.camisa_container, textvariable=self.v_long_test))
            self._row(self.camisa_container, "Chapa artesa", ttk.Entry(
                self.camisa_container, textvariable=self.v_artesa_chapa))
            self._row(self.camisa_container, "Testeros (espesor)", ttk.Entry(
                self.camisa_container, textvariable=self.v_artesa_testeros_thk))
            self._row(self.camisa_container, "Ventana inspección", ttk.Entry(
                self.camisa_container, textvariable=self.v_artesa_ventana))
            self._row(self.camisa_container, "Chapa sujeción mangón intermedio", ttk.Entry(
                self.camisa_container, textvariable=self.v_artesa_suj_mangon))
            self._row(self.camisa_container, "Boca entrada", ttk.Entry(
                self.camisa_container, textvariable=self.v_artesa_boca_entrada))
            self._row(self.camisa_container, "Boca salida", ttk.Entry(
                self.camisa_container, textvariable=self.v_artesa_boca_salida))

    def _build_def_conduccion(self, parent):
        self._section_title(parent, "PARTE 003 – CONDUCCIÓN")

        refs = rodamientos_refs(self.catalogs)
        self.cb_rod = ttk.Combobox(
            parent, textvariable=self.v_rodamiento_ref, values=refs, state="readonly")
        self._row(parent, "Rodamiento (referencia)", self.cb_rod)

        pos = self.catalogs.get("posicion_motor", [])
        self.cb_pos = ttk.Combobox(
            parent, textvariable=self.v_pos_motor, values=pos, state="readonly")
        self._row(parent, "Posición motorreductor-eje", self.cb_pos)

    def _build_def_conducido(self, parent):
        self._section_title(parent, "PARTE 004 – CONDUCIDO")

        self._row(parent, "004.001 Brida", ttk.Entry(
            parent, textvariable=self.v_conducido_brida))
        self._row(parent, "004.002 Prensaestopas", ttk.Entry(
            parent, textvariable=self.v_conducido_prensaestopas))
        self._row(parent, "004.003 Bancada soporte", ttk.Entry(
            parent, textvariable=self.v_conducido_bancada))
        self._row(parent, "004.004 Cjto Rodamiento", ttk.Entry(
            parent, textvariable=self.v_conducido_cjto_rodamiento))
        self._row(parent, "004.005 Sellado", ttk.Entry(
            parent, textvariable=self.v_conducido_sellado))

    def _show_section(self):
        key = self.section.get()
        for k, f in self.frames.items():
            f.lift() if k == key else None
        self.frames[key].lift()

    def _on_camisa_changed(self):
        self._render_camisa_panel()

    def _refresh_espesores(self):
        od = self.v_eje_od.get().strip()
        espes = espesores_for_od(self.catalogs, od)
        self.cb_thk["values"] = espes
        if espes:
            if self.v_eje_thk.get().strip() not in espes:
                self.v_eje_thk.set(espes[0])
        else:
            self.v_eje_thk.set("")

        # Refresca rodamientos filtrados por eje
        refs = filter_rodamientos_por_eje(
            self.catalogs.get("rodamientos", []), od)
        self.cb_rod["values"] = refs

    # ---------------- LOAD/SAVE ----------------
    def load_all(self):
        self.load_definition()
        self.load_progress()

    def load_definition(self):
        con = connect()
        d = get_sinfin_definicion(con, self.sinfin_id)
        con.close()

        self.v_material.set(d.get("material", self.v_material.get()))
        self.v_camisa_tipo.set(d.get("camisa_tipo", self.v_camisa_tipo.get()))
        self.v_sentido.set(d.get("sentido_giro", self.v_sentido.get()))
        self.v_long_test.set(
            d.get("long_entre_testeros", self.v_long_test.get()))
        self.v_tipo_disposicion.set(
            d.get("tipo_disposicion", self.v_tipo_disposicion.get()))
        self.v_observaciones.set(
            d.get("observaciones", self.v_observaciones.get()))

        self.v_eje_od.set(d.get("eje_od", self.v_eje_od.get()))
        self.v_eje_thk.set(d.get("eje_thk", self.v_eje_thk.get()))
        self.v_diam_ext_espira.set(
            d.get("diam_ext_espira", self.v_diam_ext_espira.get()))
        self.v_espesor_espira.set(
            d.get("espesor_espira", self.v_espesor_espira.get()))
        self.v_paso_1.set(d.get("paso_1", self.v_paso_1.get()))
        self.v_paso_2.set(d.get("paso_2", self.v_paso_2.get()))
        self.v_paso_3.set(d.get("paso_3", self.v_paso_3.get()))
        self.v_tornillos_metrica.set(
            d.get("tornillos_metrica", self.v_tornillos_metrica.get()))
        self.v_tornillos_num.set(
            d.get("tornillos_num", self.v_tornillos_num.get()))
        self.v_mangon_conduccion_d.set(
            d.get("mangon_conduccion_d", self.v_mangon_conduccion_d.get()))
        self.v_mangon_conducido_d.set(
            d.get("mangon_conducido_d", self.v_mangon_conducido_d.get()))
        self.v_num_tramos.set(d.get("num_tramos", self.v_num_tramos.get()))
        self.v_num_mangones_intermedios.set(
            d.get("num_mangones_intermedios", self.v_num_mangones_intermedios.get()))
        self.v_sujecion_mangon_intermedio.set(
            d.get("sujecion_mangon_intermedio", self.v_sujecion_mangon_intermedio.get()))

        self.v_camisa_tubo_od.set(
            d.get("camisa_tubo_od", self.v_camisa_tubo_od.get()))
        self.v_camisa_tubo_id.set(
            d.get("camisa_tubo_id", self.v_camisa_tubo_id.get()))
        self.v_camisa_testeros_thk.set(
            d.get("camisa_testeros_thk", self.v_camisa_testeros_thk.get()))
        self.v_camisa_ventana.set(
            d.get("camisa_ventana", self.v_camisa_ventana.get()))
        self.v_camisa_suj_mangon.set(
            d.get("camisa_suj_mangon", self.v_camisa_suj_mangon.get()))
        self.v_camisa_boca_entrada.set(
            d.get("camisa_boca_entrada", self.v_camisa_boca_entrada.get()))
        self.v_camisa_boca_salida.set(
            d.get("camisa_boca_salida", self.v_camisa_boca_salida.get()))

        self.v_artesa_chapa.set(
            d.get("artesa_chapa", self.v_artesa_chapa.get()))
        self.v_artesa_testeros_thk.set(
            d.get("artesa_testeros_thk", self.v_artesa_testeros_thk.get()))
        self.v_artesa_ventana.set(
            d.get("artesa_ventana", self.v_artesa_ventana.get()))
        self.v_artesa_suj_mangon.set(
            d.get("artesa_suj_mangon", self.v_artesa_suj_mangon.get()))
        self.v_artesa_boca_entrada.set(
            d.get("artesa_boca_entrada", self.v_artesa_boca_entrada.get()))
        self.v_artesa_boca_salida.set(
            d.get("artesa_boca_salida", self.v_artesa_boca_salida.get()))

        self.v_rodamiento_ref.set(
            d.get("rodamiento_ref", self.v_rodamiento_ref.get()))
        self.v_pos_motor.set(d.get("pos_motor", self.v_pos_motor.get()))

        # refrescos dependientes
        self._render_camisa_panel()
        self._refresh_espesores()

    def save_definition(self):
        defin = {
            "material": self.v_material.get().strip(),
            "camisa_tipo": self.v_camisa_tipo.get().strip(),
            "sentido_giro": self.v_sentido.get().strip(),
            "long_entre_testeros": self.v_long_test.get().strip(),
            "tipo_disposicion": self.v_tipo_disposicion.get().strip(),
            "observaciones": self.v_observaciones.get().strip(),

            "eje_od": self.v_eje_od.get().strip(),
            "eje_thk": self.v_eje_thk.get().strip(),
            "diam_ext_espira": self.v_diam_ext_espira.get().strip(),
            "espesor_espira": self.v_espesor_espira.get().strip(),
            "paso_1": self.v_paso_1.get().strip(),
            "paso_2": self.v_paso_2.get().strip(),
            "paso_3": self.v_paso_3.get().strip(),
            "tornillos_metrica": self.v_tornillos_metrica.get().strip(),
            "tornillos_num": self.v_tornillos_num.get().strip(),
            "mangon_conduccion_d": self.v_mangon_conduccion_d.get().strip(),
            "mangon_conducido_d": self.v_mangon_conducido_d.get().strip(),
            "num_tramos": self.v_num_tramos.get().strip(),
            "num_mangones_intermedios": self.v_num_mangones_intermedios.get().strip(),
            "sujecion_mangon_intermedio": self.v_sujecion_mangon_intermedio.get().strip(),

            "camisa_tubo_od": self.v_camisa_tubo_od.get().strip(),
            "camisa_tubo_id": self.v_camisa_tubo_id.get().strip(),
            "camisa_testeros_thk": self.v_camisa_testeros_thk.get().strip(),
            "camisa_ventana": self.v_camisa_ventana.get().strip(),
            "camisa_suj_mangon": self.v_camisa_suj_mangon.get().strip(),
            "camisa_boca_entrada": self.v_camisa_boca_entrada.get().strip(),
            "camisa_boca_salida": self.v_camisa_boca_salida.get().strip(),

            "artesa_chapa": self.v_artesa_chapa.get().strip(),
            "artesa_testeros_thk": self.v_artesa_testeros_thk.get().strip(),
            "artesa_ventana": self.v_artesa_ventana.get().strip(),
            "artesa_suj_mangon": self.v_artesa_suj_mangon.get().strip(),
            "artesa_boca_entrada": self.v_artesa_boca_entrada.get().strip(),
            "artesa_boca_salida": self.v_artesa_boca_salida.get().strip(),

            "rodamiento_ref": self.v_rodamiento_ref.get().strip(),
            "pos_motor": self.v_pos_motor.get().strip(),

            "_num": {
                "eje_od": _to_number(self.v_eje_od.get()),
                "eje_thk": _to_number(self.v_eje_thk.get()),
                "diam_ext_espira": _to_number(self.v_diam_ext_espira.get()),
                "espesor_espira": _to_number(self.v_espesor_espira.get()),
                "paso_1": _to_number(self.v_paso_1.get()),
                "paso_2": _to_number(self.v_paso_2.get()),
                "paso_3": _to_number(self.v_paso_3.get()),
                "long_entre_testeros": _to_number(self.v_long_test.get()),
            },
        }

        con = connect()
        set_sinfin_definicion(con, self.sinfin_id, defin)
        con.close()

        if self.on_updated_callback:
            self.on_updated_callback()

        messagebox.showinfo("Definición", "Definición guardada.")

    # ===== Progreso =====
    def _build_progress_tab(self):
        top = tk.Frame(self.tab_prog, bg="#1e1e1e")
        top.pack(fill="x", padx=16, pady=12)

        tk.Label(
            top,
            text="Progreso sinfín:",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        self.lbl_pct = tk.Label(
            top,
            text="",
            fg="#00bcd4",
            bg="#1e1e1e",
            font=("Segoe UI", 12, "bold"),
        )
        self.lbl_pct.pack(side="left", padx=10)

        ttk.Button(top, text="💾 Guardar", command=self.save_progress).pack(
            side="right", padx=6)
        ttk.Button(top, text="🔄 Recargar", command=self.load_progress).pack(
            side="right", padx=6)

        # Scrollable checklist
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
                fg="white",
                bg="#1e1e1e",
                font=("Segoe UI", 11, "bold"),
            )
            title.grid(row=row, column=0, sticky="w", pady=(10, 2))
            row += 1

            for t in p["tareas"]:
                v = tk.IntVar(value=get_estado_tarea(
                    con, self.sinfin_id, t["id"]))
                self.vars_checks[t["id"]] = v

                cb = tk.Checkbutton(
                    self.inner,
                    text=t["nombre"],
                    variable=v,
                    command=self.save_progress,  # guarda al marcar
                    bg="#1e1e1e",
                    fg="#cccccc",
                    activebackground="#1e1e1e",
                    activeforeground="#ffffff",
                    selectcolor="#1e1e1e",
                    anchor="w",
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
