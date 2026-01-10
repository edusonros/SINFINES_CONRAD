# app/sinfin_window.py
from __future__ import annotations

import json
import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, List, Optional

from utils.db import (
    connect,
    get_sinfin_definicion,
    set_sinfin_definicion,
    list_tareas_por_proceso,
    get_estado_tarea,
    set_estado_tarea,
)
from utils.catalogs import (
    load_catalogs,
    filter_espesores_por_od,
    filter_rodamientos_por_tubo,
    tubo_id_mm,
)
from exporter.inventor_export import export_params_to_csv


# ------------------ UI Helpers ------------------

def to_float_required(x) -> float:
    s = str(x).strip().replace(",", ".")
    return float(s)


def to_float_optional(x) -> Optional[float]:
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _norm_num_text(s: str) -> str:
    return str(s).strip().replace(",", ".")


def _set_dark_style(root: tk.Misc) -> None:
    """
    Ajustes de estilo ttk (dark) sin depender de temas externos.
    """
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg = "#1e1e1e"
    fg = "#ffffff"
    accent = "#00bcd4"
    panel = "#252526"
    entry_bg = "#ffffff"

    # Base
    style.configure(".", background=bg, foreground=fg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure(
        "TLabelframe.Label",
        background=bg,
        foreground=fg,
        font=("Segoe UI", 10, "bold"),
    )

    # Buttons
    style.configure("TButton", font=("Segoe UI", 10))
    style.map("TButton", background=[("active", "#f0f0f0")])

    # Entries / Combos
    style.configure("TEntry", fieldbackground=entry_bg, foreground="#000000")
    style.configure("TCombobox", fieldbackground=entry_bg,
                    foreground="#000000")

    # Combobox estilos específicos (para "pendiente medir")
    style.configure("Normal.TCombobox",
                    fieldbackground=entry_bg, foreground="#000000")
    style.configure("Pending.TCombobox",
                    fieldbackground=entry_bg, foreground="#ff3b30")
    style.map(
        "Pending.TCombobox",
        foreground=[("readonly", "#ff3b30"), ("!disabled", "#ff3b30")],
    )
    style.map(
        "Normal.TCombobox",
        foreground=[("readonly", "#000000"), ("!disabled", "#000000")],
    )

    # Notebook
    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        padding=(18, 10),
        font=("Segoe UI", 11, "bold"),
        background=panel,
        foreground=fg,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", accent), ("active", "#3a3a3a")],
        foreground=[("selected", "#000000"), ("active", fg)],
    )

    # Treeview (gris claro)
    tv_bg = "#d9d9d9"
    tv_head = "#cfcfcf"
    style.configure(
        "Treeview",
        background=tv_bg,
        fieldbackground=tv_bg,
        foreground="#000000",
        rowheight=26,
    )
    style.configure(
        "Treeview.Heading",
        background=tv_head,
        foreground="#000000",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", "#4a90e2")],
        foreground=[("selected", "#ffffff")],
    )


def _safe_float_text(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if not s:
        return ""
    return s


# ------------------ Main Window ------------------


class SinfinWindow(tk.Toplevel):
    def __init__(self, parent, sinfin_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.title("Sinfín – Definición / Progreso")
        self.geometry("1100x720")
        self.configure(bg="#1e1e1e")
        self.minsize(980, 620)

        self.sinfin_id = sinfin_id
        self.on_updated_callback = on_updated_callback

        _set_dark_style(self)

        # Cargar catálogos desde JSON
        self.catalogs = load_catalogs()

        # ---------------- Vars (Definición) ----------------
        self.v_section = tk.StringVar(value="General")

        # GENERAL
        self.v_material = tk.StringVar()
        self.v_camisa_tipo = tk.StringVar(
            value="CIRCULAR")  # CIRCULAR / ARTESA
        self.v_sentido = tk.StringVar(
            value="DERECHAS")  # DERECHAS / IZQUIERDAS

        # Longitud entre testeros ahora es LISTA (Combobox)
        self.v_long_test = tk.StringVar()

        self.v_pendiente_medir = tk.BooleanVar(value=False)

        # Longitud total exterior calculada
        self.v_long_total_ext = tk.StringVar(value="")
        self.v_long_total_hint = tk.StringVar(value="")

        self._obs_text: Optional[tk.Text] = None

        # (Disposición motor) -> se muestra en Conducción (Parte 003)
        self.v_tipo_dispos = tk.StringVar()

        # PARTE 001 – TORNILLO
        self.v_eje_od = tk.StringVar()
        self.v_eje_thk = tk.StringVar()

        # Automático: mangón Ø (macizo) (lo rellena _auto_from_tubo si está vacío)
        self.v_mangon_conduccion = tk.StringVar()
        self.v_mangon_conducido = tk.StringVar()

        # Longitudes exteriores mangones (para L total exterior)
        self.v_mangon_ext_conduccion = tk.StringVar()
        self.v_mangon_ext_conducido = tk.StringVar()

        self.v_mangones_intermedios = tk.BooleanVar(value=False)
        self.v_num_mangones_intermedios = tk.StringVar()
        self.v_diam_mangon_intermedio = tk.StringVar()

        # Tornillería automática (texto)
        self.v_metrica_tornillos = tk.StringVar()

        # Espiras/pasos
        self.v_diam_espira = tk.StringVar()
        self.v_espesor_espira = tk.StringVar()
        self.v_paso1 = tk.StringVar()
        self.v_paso2 = tk.StringVar()
        self.v_paso3 = tk.StringVar()

        # PARTE 002 – CAMISA (ahora con filas de “subconjuntos”)
        self.v_dist_testeros = tk.StringVar()

        # 002A
        self.v_002A_tubo = tk.StringVar()
        self.v_002A_testeros = tk.StringVar()
        self.v_002A_ventana_inspeccion = tk.StringVar()
        self.v_002A_suj_mangon_intermedio = tk.StringVar()
        self.v_002A_boca_entrada = tk.StringVar()
        self.v_002A_boca_salida = tk.StringVar()

        # 002B
        self.v_002B_chapa_artesa = tk.StringVar()
        self.v_002B_testeros = tk.StringVar()
        self.v_002B_ventana_inspeccion = tk.StringVar()
        self.v_002B_suj_mangon_intermedio = tk.StringVar()
        self.v_002B_boca_entrada = tk.StringVar()
        self.v_002B_boca_salida = tk.StringVar()

        # PARTE 003 – CONDUCCIÓN
        self.v_rod_conduccion = tk.StringVar()
        self.v_pos_motor = tk.StringVar()

        # PARTE 004 – CONDUCIDO
        self.v_rod_conducido = tk.StringVar()

        # refs widgets
        self.cb_long_test: Optional[ttk.Combobox] = None
        self.ent_long_total_ext: Optional[tk.Entry] = None

        # progreso: mapping iid->tarea_id
        self._tree_item_to_tarea_id: dict[str, int] = {}

        # traces
        self.v_long_test.trace_add(
            "write", lambda *_: self._recalc_longitudes())
        self.v_mangon_ext_conduccion.trace_add(
            "write", lambda *_: self._recalc_longitudes())
        self.v_mangon_ext_conducido.trace_add(
            "write", lambda *_: self._recalc_longitudes())
        self.v_pendiente_medir.trace_add(
            "write", lambda *_: self._apply_pending_style())

        # ---------------- Build UI ----------------
        self._build_ui()
        self._load_all()

    def _get_definicion_completa(self) -> dict:
        """
        Devuelve un dict con todos los parámetros necesarios para exportar a Inventor.
        (Si falta alguno, lanzamos error con messagebox)
        """
        # Ejemplo mínimo para que export_params_to_csv no reviente:
        # Ajusta los nombres para que coincidan con inventor_export.py
        d = {
            "longitud_entre_testeros": self.v_long_test.get().strip(),
            "paso_espira": self.v_paso1.get().strip(),
            "diametro_tubo": self.v_eje_od.get().strip(),
            "espesor_tubo": self.v_eje_thk.get().strip(),
            "diametro_espira": self.v_diam_espira.get().strip(),
            "espesor_chapa": self.v_espesor_espira.get().strip(),
            # opcional
            "espesor_testero": self.v_002A_testeros.get().strip() or self.v_002B_testeros.get().strip() or "10",
        }

        # Validación rápida
        faltan = [k for k, v in d.items() if not str(v).strip()]
        if faltan:
            raise ValueError(
                "Faltan datos para generar planos: " + ", ".join(faltan))

        return d

    def _on_generar_planos(self):
        """
        Exporta params.csv y ejecuta Inventor+iLogic.
        """
        try:
            definicion = self._get_definicion_completa()
            export_params_to_csv(definicion)

            # IMPORT DIFERIDO (solo si pulsas el botón)
            from exporter.run_inventor import run_inventor
            run_inventor()

            messagebox.showinfo(
                "OK", "Planos generados / modelo actualizado en Inventor.")
        except Exception as e:
            messagebox.showerror("Error al generar planos", str(e))

    # ------------------ UI Layout ------------------

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_def = ttk.Frame(nb)
        self.tab_prog = ttk.Frame(nb)

        nb.add(self.tab_def, text="Definición")
        nb.add(self.tab_prog, text="Progreso")

        self._build_def_tab()
        self._build_progress_tab()

    def _build_def_tab(self):
        # Header
        header = ttk.Frame(self.tab_def)
        header.pack(fill="x", padx=16, pady=(14, 10))

        ttk.Label(header, text="DEFINICIÓN DEL SINFÍN", font=("Segoe UI", 14, "bold")).pack(
            side="left"
        )

        btns = ttk.Frame(header)
        btns.pack(side="right")

        ttk.Button(btns, text="Recargar", command=self._load_definition).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(btns, text="Guardar definición", command=self._save_definition).pack(
            side="left"
        )
        ttk.Button(btns, text="Generar Planos", command=self._on_generar_planos).pack(
            side="left", padx=(0, 10)
        )

        # Body
        body = ttk.Frame(self.tab_def)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        left = ttk.Frame(body, width=220)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ttk.Label(left, text="Secciones", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        def add_section(name: str):
            rb = ttk.Radiobutton(
                left,
                text=name,
                value=name,
                variable=self.v_section,
                command=self._render_section,
            )
            rb.pack(anchor="w", pady=4)

        add_section("General")
        add_section("Parte 001 – Tornillo")
        add_section("Parte 002 – Camisa")
        add_section("Parte 003 – Conducción")
        add_section("Parte 004 – Conducido")

        ttk.Separator(body, orient="vertical").pack(
            side="left", fill="y", padx=14)

        # Right content (scrollable)
        self.right_container = ttk.Frame(body)
        self.right_container.pack(side="left", fill="both", expand=True)

        self._canvas = tk.Canvas(self.right_container,
                                 bg="#1e1e1e", highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(self.right_container,
                            orient="vertical", command=self._canvas.yview)
        vsb.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=vsb.set)

        self.right = ttk.Frame(self._canvas)
        self._canvas.create_window((0, 0), window=self.right, anchor="nw")

        self.right.bind(
            "<Configure>",
            lambda _e=None: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")),
        )

        self._render_section()

    def _clear_right(self):
        for w in self.right.winfo_children():
            w.destroy()

    def _make_form(self, title: str, cols: int = 2) -> ttk.Frame:
        """
        Crea un bloque con título y devuelve el frame 'form' para añadir filas.
        cols=2: [label][widget]
        cols=3: [label][widget][acción]
        """
        title_lbl = ttk.Label(self.right, text=title,
                              font=("Segoe UI", 12, "bold"))
        title_lbl.pack(anchor="w", pady=(0, 10))

        outer = ttk.Frame(self.right)
        outer.pack(fill="x", padx=6)

        form = ttk.Frame(outer)
        form.pack(fill="x")

        form.grid_columnconfigure(0, weight=0, minsize=260)  # labels
        form.grid_columnconfigure(1, weight=1)  # inputs
        if cols >= 3:
            form.grid_columnconfigure(2, weight=0, minsize=200)  # actions

        return form

    def _add_row(
        self,
        form: ttk.Frame,
        row: int,
        label: str,
        widget: tk.Widget,
        *,
        action_widget: Optional[tk.Widget] = None,
        hint: Optional[str] = None,
        height: Optional[int] = None,
        expand: bool = True,
    ) -> int:
        ttk.Label(form, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 14), pady=6)

        if isinstance(widget, tk.Text):
            wrap = ttk.Frame(form)
            wrap.grid(row=row, column=1, sticky="we", pady=6)
            wrap.grid_columnconfigure(0, weight=1)
            widget.configure(
                height=height or 4,
                wrap="word",
                bg="#ffffff",
                fg="#000000",
                insertbackground="#000000",
            )
            widget.grid(in_=wrap, row=0, column=0, sticky="we")
        else:
            sticky = "we" if expand else "w"
            widget.grid(row=row, column=1, sticky=sticky, pady=6)

        if action_widget is not None:
            action_widget.grid(row=row, column=2, sticky="e",
                               padx=(10, 0), pady=6)

        if hint:
            row += 1
            ttk.Label(form, text=hint, foreground="#b0b0b0").grid(
                row=row, column=1, sticky="w", pady=(0, 8)
            )
        return row + 1

    def _render_section(self):
        self._clear_right()
        sec = self.v_section.get()

        if sec == "General":
            self._build_general()
        elif sec == "Parte 001 – Tornillo":
            self._build_tornillo()
        elif sec == "Parte 002 – Camisa":
            self._build_camisa()
        elif sec == "Parte 003 – Conducción":
            self._build_conduccion()
        elif sec == "Parte 004 – Conducido":
            self._build_conducido()
        else:
            ttk.Label(self.right, text=sec).pack(anchor="w")

        self.right.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # ------------------ Stub Actions ------------------

    def _stub_offer(self, what: str):
        messagebox.showinfo(
            "Oferta (pendiente)",
            f"Botón preparado para futuro:\n\n{what}\n\n(En el futuro: preparar borrador Outlook.)",
        )

    # ------------------ Helpers automáticos ------------------

    def _ceil_to_5(self, x: float) -> int:
        return int(math.ceil(x / 5.0) * 5)

    def _auto_from_tubo(self):
        """
        - Calcula ID del tubo y propone mangones = (ID + 10) redondeado a 5 por arriba.
        - Tornillería automática: M12 x (ID + 25) redondeada a 5 por arriba.
        """
        try:
            id_calc = tubo_id_mm(self.v_eje_od.get(), self.v_eje_thk.get())
            id_mm = float(id_calc) if id_calc is not None and str(
                id_calc).strip() else None
        except Exception:
            id_mm = None

        if id_mm is None:
            return

        mangon = self._ceil_to_5(id_mm + 10.0)

        # Solo autocompleta si vacío (no pisa lo que escriba el usuario)
        if not self.v_mangon_conduccion.get().strip():
            self.v_mangon_conduccion.set(str(mangon))
        if not self.v_mangon_conducido.get().strip():
            self.v_mangon_conducido.set(str(mangon))

        bolt_len = self._ceil_to_5(id_mm + 25.0)
        self.v_metrica_tornillos.set(f"M12x{bolt_len}")

    # ------------------ Section Builders ------------------

    def _build_general(self):
        form = self._make_form("GENERAL")

        # Material (estrecho)
        cb_mat = ttk.Combobox(
            form,
            textvariable=self.v_material,
            values=self.catalogs.get("materials", []),
            state="readonly",
            width=18,
            style="Normal.TCombobox",
        )
        row = 0
        row = self._add_row(form, row, "Material", cb_mat, expand=False)

        # Forma camisa
        row = self._add_row(form, row, "Forma de la camisa", ttk.Frame(form))
        for w in form.grid_slaves(row=row - 1, column=1):
            w.destroy()
        f_cam = ttk.Frame(form)
        f_cam.grid(row=row - 1, column=1, sticky="w", pady=6)

        ttk.Radiobutton(
            f_cam,
            text="Artesa",
            value="ARTESA",
            variable=self.v_camisa_tipo,
            command=self._on_camisa_changed,
        ).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(
            f_cam,
            text="Tubo circular",
            value="CIRCULAR",
            variable=self.v_camisa_tipo,
            command=self._on_camisa_changed,
        ).pack(side="left")

        # Sentido de giro
        row = self._add_row(form, row, "Sentido de giro", ttk.Frame(form))
        for w in form.grid_slaves(row=row - 1, column=1):
            w.destroy()
        f_giro = ttk.Frame(form)
        f_giro.grid(row=row - 1, column=1, sticky="w", pady=6)
        ttk.Radiobutton(f_giro, text="A derechas", value="DERECHAS", variable=self.v_sentido).pack(
            side="left", padx=(0, 14)
        )
        ttk.Radiobutton(
            f_giro, text="A izquierdas", value="IZQUIERDAS", variable=self.v_sentido
        ).pack(side="left")

        # Longitud entre testeros (LISTA de Distancio_Testeros.csv -> catalogs["distancia_testeros"])
        cb_len = ttk.Combobox(
            form,
            textvariable=self.v_long_test,
            values=self.catalogs.get("distancia_testeros", []),
            state="readonly",
            width=18,
            style="Normal.TCombobox",
        )
        self.cb_long_test = cb_len
        row = self._add_row(
            form, row, "Longitud entre testeros (mm)", cb_len, expand=False)

        # Pendiente medir en cliente (checkbox)
        chk = ttk.Checkbutton(
            form,
            text="Pendiente de medir en el Cliente",
            variable=self.v_pendiente_medir,
            command=self._apply_pending_style,
        )
        ttk.Label(form, text="").grid(row=row, column=0,
                                      sticky="w", padx=(0, 14), pady=6)
        chk.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # Longitud total exterior (calculada) - estrecha + rojo si faltan datos
        ent_total = tk.Entry(
            form,
            textvariable=self.v_long_total_ext,
            bg="#ffffff",
            fg="#000000",
            insertbackground="#000000",
            relief="flat",
            width=18,
        )
        ent_total.config(state="readonly")
        self.ent_long_total_ext = ent_total
        row = self._add_row(
            form,
            row,
            "Longitud total exterior del sinfín (mm) [calc]",
            ent_total,
            expand=False,
        )

        # Hint dinámico (si falta algo para calcular)
        lbl_hint = ttk.Label(
            form, textvariable=self.v_long_total_hint, foreground="#ff3b30")
        lbl_hint.grid(row=row, column=1, sticky="w", pady=(0, 8))
        row += 1

        # Observaciones (Text) - cuadro editable
        txt = tk.Text(form, height=4)
        self._obs_text = txt
        pending = getattr(self, "_pending_obs", "")
        if pending:
            self._set_observaciones(pending)
        row = self._add_row(form, row, "Observaciones", txt, height=6)

        # aplicar estilos iniciales
        self._recalc_longitudes()
        self._apply_pending_style()

    def _build_tornillo(self):
        form = self._make_form("PARTE 001 – TORNILLO", cols=3)
        row = 0

        def offer_btn(text: str):
            return ttk.Button(
                form,
                text="Pedir Ofertas Material",
                command=lambda: self._stub_offer(text),
            )

        # 1) Eje OD (con botón oferta)
        cb_od = ttk.Combobox(
            form,
            textvariable=self.v_eje_od,
            values=self.catalogs.get("eje_od", []),
            state="readonly",
        )
        cb_od.bind("<<ComboboxSelected>>",
                   lambda _e: self._on_eje_od_changed())
        row = self._add_row(
            form,
            row,
            "Eje: ø exterior tubo:",
            cb_od,
            action_widget=offer_btn("Eje: Ø exterior tubo"),
        )

        # 2) Espesor eje (filtrado por OD) (SIN botón oferta)
        cb_thk = ttk.Combobox(
            form, textvariable=self.v_eje_thk, values=[], state="readonly")
        cb_thk.bind("<<ComboboxSelected>>",
                    lambda _e: self._on_eje_thk_changed())
        row = self._add_row(form, row, "Espesor tubo eje (mm)", cb_thk)
        self.cb_eje_thk = cb_thk

        # Mangones extremos Ø (automático si vacío)
        ent_mc = ttk.Entry(
            form, textvariable=self.v_mangon_conduccion, width=18)
        row = self._add_row(
            form,
            row,
            "Mangón conducción Ø macizo (mm) [auto]",
            ent_mc,
            expand=False,
        )

        ent_md = ttk.Entry(
            form, textvariable=self.v_mangon_conducido, width=18)
        row = self._add_row(
            form,
            row,
            "Mangón conducido Ø macizo (mm) [auto]",
            ent_md,
            expand=False,
        )

        # Longitudes exteriores mangones (para longitud total exterior)
        ent_lc = ttk.Entry(
            form, textvariable=self.v_mangon_ext_conduccion, width=18)
        row = self._add_row(
            form,
            row,
            "Longitud exterior mangón conducción (mm)",
            ent_lc,
            expand=False,
        )

        ent_ld = ttk.Entry(
            form, textvariable=self.v_mangon_ext_conducido, width=18)
        row = self._add_row(
            form,
            row,
            "Longitud exterior mangón conducido (mm)",
            ent_ld,
            expand=False,
        )

        # ¿Mangones intermedios?
        chk = ttk.Checkbutton(
            form,
            text="¿Mangón/es Intermedio/s?",
            variable=self.v_mangones_intermedios,
            command=self._render_section,  # re-render para mostrar/ocultar campos
        )
        ttk.Label(form, text="").grid(row=row, column=0,
                                      sticky="w", padx=(0, 14), pady=6)
        chk.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        if self.v_mangones_intermedios.get():
            ent_n = ttk.Entry(
                form, textvariable=self.v_num_mangones_intermedios, width=18)
            row = self._add_row(
                form,
                row,
                "Número de Mangones Intermedios",
                ent_n,
                expand=False,
            )

            ent_d = ttk.Entry(
                form, textvariable=self.v_diam_mangon_intermedio, width=18)
            row = self._add_row(
                form,
                row,
                "Diámetro del mismo (mm) [libre]",
                ent_d,
                action_widget=offer_btn("Mangones intermedios (material)"),
                expand=False,
            )

        # Separador antes de tornillería (para diferenciar)
        sep = ttk.Separator(form, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="we", pady=(10, 10))
        row += 1

        # Tornillería automática (readonly entry) (sin botón)
        ent_torn = tk.Entry(
            form,
            textvariable=self.v_metrica_tornillos,
            bg="#ffffff",
            fg="#000000",
            insertbackground="#000000",
            relief="flat",
            width=18,
        )
        ent_torn.config(state="readonly")
        row = self._add_row(
            form, row, "Tornillería (automática)", ent_torn, expand=False)

        # Ø exterior espira (sin botón)
        cb_de = ttk.Combobox(
            form,
            textvariable=self.v_diam_espira,
            values=self.catalogs.get("diam_espira", []),
            state="readonly",
        )
        row = self._add_row(form, row, "DIAMETRO EXTERIOR ESPIRA (mm)", cb_de)

        # Espesor espira (CON botón único central)
        cb_es = ttk.Combobox(
            form,
            textvariable=self.v_espesor_espira,
            values=self.catalogs.get("espesores_chapa", []),
            state="readonly",
        )
        row = self._add_row(
            form,
            row,
            "ESPESOR ESPIRAS (mm)",
            cb_es,
            action_widget=offer_btn("Espiras: espesor"),
        )

        # Pasos (sin botones)
        cb_p1 = ttk.Combobox(form, textvariable=self.v_paso1, values=self.catalogs.get(
            "pasos", []), state="readonly")
        row = self._add_row(form, row, "PASO ESPIRAS – Paso 1 (mm)", cb_p1)

        cb_p2 = ttk.Combobox(form, textvariable=self.v_paso2, values=self.catalogs.get(
            "pasos", []), state="readonly")
        row = self._add_row(
            form, row, "PASO ESPIRAS – Paso 2 (mm) [opcional]", cb_p2)

        cb_p3 = ttk.Combobox(form, textvariable=self.v_paso3, values=self.catalogs.get(
            "pasos", []), state="readonly")
        row = self._add_row(
            form, row, "PASO ESPIRAS – Paso 3 (mm) [opcional]", cb_p3)

        self._on_eje_od_changed()
        self._recalc_longitudes()

    def _build_camisa(self):
        tipo = self.v_camisa_tipo.get()  # CIRCULAR / ARTESA
        yesno = ["", "Sí", "No"]

        def offer_btn(text: str):
            return ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(text))

        if tipo == "CIRCULAR":
            form = self._make_form("PARTE 002A – CAMISA TUBO Ø", cols=3)
            row = 0

            cb_dist = ttk.Combobox(
                form,
                textvariable=self.v_dist_testeros,
                values=self.catalogs.get("distancia_testeros", []),
                state="readonly",
            )
            row = self._add_row(
                form,
                row,
                "Distancia entre testeros (mm)",
                cb_dist,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002A: Distancia entre testeros")),
            )

            ent_tubo = ttk.Entry(form, textvariable=self.v_002A_tubo)
            row = self._add_row(
                form,
                row,
                "002A.001  Tubo ø exterior / ø interior",
                ent_tubo,
                action_widget=ttk.Button(
                    form, text="Pedir oferta", command=lambda: self._stub_offer("Camisa 002A: Tubo")),
            )

            cb_testeros = ttk.Combobox(
                form,
                textvariable=self.v_002A_testeros,
                values=self.catalogs.get("espesores_chapa", []),
                state="readonly",
            )
            row = self._add_row(
                form,
                row,
                "002A.002  Testeros (espesor)",
                cb_testeros,
                action_widget=ttk.Button(
                    form, text="Pedir oferta", command=lambda: self._stub_offer("Camisa 002A: Testeros")),
            )

            cb_win = ttk.Combobox(
                form, textvariable=self.v_002A_ventana_inspeccion, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002A.003  Ventana inspección",
                cb_win,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002A: Ventana inspección")),
            )

            cb_suj = ttk.Combobox(
                form, textvariable=self.v_002A_suj_mangon_intermedio, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002A.004  Cjto. sujeción mangón intermedio",
                cb_suj,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002A: Sujeción mangón intermedio")),
            )

            cb_in = ttk.Combobox(
                form, textvariable=self.v_002A_boca_entrada, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002A.005  Boca entrada",
                cb_in,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002A: Boca entrada")),
            )

            cb_out = ttk.Combobox(
                form, textvariable=self.v_002A_boca_salida, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002A.006  Boca salida",
                cb_out,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002A: Boca salida")),
            )

        else:
            form = self._make_form("PARTE 002B – CAMISA ARTESA", cols=3)
            row = 0

            cb_dist = ttk.Combobox(
                form,
                textvariable=self.v_dist_testeros,
                values=self.catalogs.get("distancia_testeros", []),
                state="readonly",
            )
            row = self._add_row(
                form,
                row,
                "Distancia entre testeros (mm)",
                cb_dist,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002B: Distancia entre testeros")),
            )

            cb_chapa = ttk.Combobox(
                form,
                textvariable=self.v_002B_chapa_artesa,
                values=self.catalogs.get("espesores_chapa", []),
                state="readonly",
            )
            row = self._add_row(
                form,
                row,
                "002B.001  Chapa artesa (espesor)",
                cb_chapa,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002B: Chapa artesa")),
            )

            cb_testeros = ttk.Combobox(
                form,
                textvariable=self.v_002B_testeros,
                values=self.catalogs.get("espesores_chapa", []),
                state="readonly",
            )
            row = self._add_row(
                form,
                row,
                "002B.002  Testeros (espesor)",
                cb_testeros,
                action_widget=ttk.Button(
                    form, text="Pedir oferta", command=lambda: self._stub_offer("Camisa 002B: Testeros")),
            )

            cb_win = ttk.Combobox(
                form, textvariable=self.v_002B_ventana_inspeccion, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002B.003  Ventana inspección",
                cb_win,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002B: Ventana inspección")),
            )

            cb_suj = ttk.Combobox(
                form, textvariable=self.v_002B_suj_mangon_intermedio, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002B.004  Chapa sujeción mangón intermedio",
                cb_suj,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002B: Sujeción mangón intermedio")),
            )

            cb_in = ttk.Combobox(
                form, textvariable=self.v_002B_boca_entrada, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002B.005  Boca entrada",
                cb_in,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002B: Boca entrada")),
            )

            cb_out = ttk.Combobox(
                form, textvariable=self.v_002B_boca_salida, values=yesno, state="readonly")
            row = self._add_row(
                form,
                row,
                "002B.006  Boca salida",
                cb_out,
                action_widget=ttk.Button(form, text="Pedir oferta", command=lambda: self._stub_offer(
                    "Camisa 002B: Boca salida")),
            )

    def _build_conduccion(self):
        form = self._make_form("PARTE 003 – CONDUCCIÓN")
        row = 0

        # Disposición del motor (movida desde GENERAL)
        cb_tipo = ttk.Combobox(
            form,
            textvariable=self.v_tipo_dispos,
            values=self.catalogs.get("tipo_disposicion", []),
            state="readonly",
        )
        row = self._add_row(form, row, "Disposición del motor (tipo)", cb_tipo)

        self.cb_rod_conduccion = ttk.Combobox(
            form, textvariable=self.v_rod_conduccion, values=[], state="readonly"
        )
        row = self._add_row(
            form, row, "Rodamiento (referencia)", self.cb_rod_conduccion)

        cb_pos = ttk.Combobox(
            form,
            textvariable=self.v_pos_motor,
            values=self.catalogs.get("posicion_motor", []),
            state="readonly",
        )
        row = self._add_row(form, row, "Posición motorreductor-eje", cb_pos)

        self._refresh_rodamientos()

    def _build_conducido(self):
        form = self._make_form("PARTE 004 – CONDUCIDO")
        row = 0

        self.cb_rod_conducido = ttk.Combobox(
            form, textvariable=self.v_rod_conducido, values=[], state="readonly"
        )
        row = self._add_row(
            form, row, "Rodamiento (referencia)", self.cb_rod_conducido)

        self._refresh_rodamientos()

    # ------------------ Events / Refresh ------------------

    def _on_camisa_changed(self):
        if self.v_section.get() == "Parte 002 – Camisa":
            self._render_section()

    def _on_eje_od_changed(self):
        od_raw = self.v_eje_od.get().strip()
        od = _norm_num_text(od_raw)

        # si quieres, normaliza también el propio StringVar:
        if od_raw != od:
            self.v_eje_od.set(od)

        espes = filter_espesores_por_od(self.catalogs, od)
        self.cb_eje_thk.configure(values=espes)

        if self.v_eje_thk.get().strip() not in espes:
            self.v_eje_thk.set(espes[0] if espes else "")

        self._refresh_rodamientos()
        self._auto_from_tubo()

    def _on_eje_thk_changed(self):
        thk_raw = self.v_eje_thk.get().strip()
        thk = _norm_num_text(thk_raw)
        if thk_raw != thk:
            self.v_eje_thk.set(thk)

        self._refresh_rodamientos()
        self._auto_from_tubo()

    def _refresh_rodamientos(self):
        od = _norm_num_text(self.v_eje_od.get())
        thk = _norm_num_text(self.v_eje_thk.get())

        vals: List[str] = filter_rodamientos_por_tubo(self.catalogs, od, thk)

        if hasattr(self, "cb_rod_conduccion"):
            self.cb_rod_conduccion.configure(values=vals)
            if self.v_rod_conduccion.get() and self.v_rod_conduccion.get() not in vals:
                self.v_rod_conduccion.set("")
        if hasattr(self, "cb_rod_conducido"):
            self.cb_rod_conducido.configure(values=vals)
            if self.v_rod_conducido.get() and self.v_rod_conducido.get() not in vals:
                self.v_rod_conducido.set("")

    def _apply_pending_style(self):
        """
        Si está pendiente de medir, intentamos marcar la Longitud entre testeros en rojo.
        (En algunos temas de Windows el foreground del Combobox no cambia; en ese caso al menos
        queda indicado por la casilla y por el hint/calculo.)
        """
        if self.cb_long_test:
            self.cb_long_test.configure(
                style="Pending.TCombobox" if self.v_pendiente_medir.get() else "Normal.TCombobox")

    def _recalc_longitudes(self):
        """
        Longitud total exterior = longitud entre testeros + longitudes exteriores de mangón (conducción + conducido).
        Si falta algún valor -> el total queda en rojo y mostramos texto indicando qué falta.
        """
        lt = _to_float(self.v_long_test.get())
        lc = _to_float(self.v_mangon_ext_conduccion.get())
        ld = _to_float(self.v_mangon_ext_conducido.get())

        missing = []
        if lt is None:
            missing.append("Longitud entre testeros")
        if lc is None:
            missing.append("Longitud exterior mangón conducción")
        if ld is None:
            missing.append("Longitud exterior mangón conducido")

        if missing:
            self.v_long_total_ext.set("")
            self.v_long_total_hint.set(
                "Falta para calcular: " + " · ".join(missing))
            if self.ent_long_total_ext:
                self.ent_long_total_ext.config(state="normal")
                self.ent_long_total_ext.config(fg="#ff3b30")  # rojo
                self.ent_long_total_ext.config(state="readonly")
        else:
            total = float(lt) + float(lc) + float(ld)
            self.v_long_total_ext.set(f"{total:.0f}")
            self.v_long_total_hint.set("")
            if self.ent_long_total_ext:
                self.ent_long_total_ext.config(state="normal")
                self.ent_long_total_ext.config(fg="#000000")
                self.ent_long_total_ext.config(state="readonly")

    # ------------------ Progress Tab (Treeview con Estado) ------------------

    def _build_progress_tab(self):
        top = ttk.Frame(self.tab_prog)
        top.pack(fill="x", padx=16, pady=12)

        ttk.Label(top, text="Progreso sinfín:", font=(
            "Segoe UI", 12, "bold")).pack(side="left")
        self.lbl_pct = ttk.Label(top, text="", font=(
            "Segoe UI", 12, "bold"), foreground="#00bcd4")
        self.lbl_pct.pack(side="left", padx=10)

        btns = ttk.Frame(top)
        btns.pack(side="right")
        ttk.Button(btns, text="Recargar", command=self._load_progress).pack(
            side="left", padx=(0, 8))
        ttk.Button(btns, text="Marcar HECHO", command=lambda: self._set_selected_task_state(
            1)).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Marcar PENDIENTE",
                   command=lambda: self._set_selected_task_state(0)).pack(side="left")

        cols = ("Proceso", "Tarea", "Estado")
        self.tree_prog = ttk.Treeview(
            self.tab_prog, columns=cols, show="headings", height=22)
        for c in cols:
            self.tree_prog.heading(c, text=c)
            self.tree_prog.column(c, width=220 if c !=
                                  "Tarea" else 600, anchor="w")

        self.tree_prog.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.tree_prog.bind(
            "<Double-1>", lambda _e: self._toggle_selected_task())

        ttk.Label(
            self.tab_prog,
            text="Doble click para alternar HECHO/PENDIENTE. Se guarda en la base de datos.",
            foreground="#b0b0b0",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        self._tree_item_to_tarea_id = {}

    def _toggle_selected_task(self):
        sel = self.tree_prog.selection()
        if not sel:
            return
        item = sel[0]
        tarea_id = self._tree_item_to_tarea_id.get(item)
        if not tarea_id:
            return

        con = connect()
        try:
            cur = get_estado_tarea(con, self.sinfin_id, int(tarea_id))
            newv = 0 if int(cur) == 1 else 1
            set_estado_tarea(con, self.sinfin_id, int(tarea_id), newv)
        finally:
            con.close()

        self._load_progress()

    def _set_selected_task_state(self, completado: int):
        sel = self.tree_prog.selection()
        if not sel:
            return
        item = sel[0]
        tarea_id = self._tree_item_to_tarea_id.get(item)
        if not tarea_id:
            return

        con = connect()
        try:
            set_estado_tarea(con, self.sinfin_id,
                             int(tarea_id), int(completado))
        finally:
            con.close()

        self._load_progress()

    # ------------------ Load / Save ------------------

    def _load_all(self):
        self._load_definition()
        self._load_progress()

    def _get_observaciones(self) -> str:
        if not self._obs_text:
            return ""
        try:
            return self._obs_text.get("1.0", "end").strip()
        except tk.TclError:
            return ""

    def _set_observaciones(self, text: str):
        if not self._obs_text:
            return
        self._obs_text.delete("1.0", "end")
        if text:
            self._obs_text.insert("1.0", text)

    def _load_definition(self):
        con = connect()
        try:
            d = get_sinfin_definicion(con, self.sinfin_id) or {}
        finally:
            con.close()

        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception:
                d = {}

        # GENERAL
        self.v_material.set(d.get("material", self.v_material.get()))
        self.v_camisa_tipo.set(d.get("camisa_tipo", self.v_camisa_tipo.get()))
        self.v_sentido.set(d.get("sentido_giro", self.v_sentido.get()))
        self.v_long_test.set(_safe_float_text(
            d.get("longitud_entre_testeros", d.get("long_test", ""))))
        self.v_pendiente_medir.set(
            bool(d.get("pendiente_medir_cliente", False)))
        self._pending_obs = d.get("observaciones", "")

        # Disposición motor (Parte 003)
        self.v_tipo_dispos.set(
            d.get("tipo_disposicion", self.v_tipo_dispos.get()))

        # TORNILLO
        self.v_eje_od.set(d.get("eje_od", self.v_eje_od.get()))
        self.v_eje_thk.set(d.get("eje_thk", self.v_eje_thk.get()))

        self.v_mangon_conduccion.set(
            d.get("mangon_conduccion", self.v_mangon_conduccion.get()))
        self.v_mangon_conducido.set(
            d.get("mangon_conducido", self.v_mangon_conducido.get()))

        self.v_mangon_ext_conduccion.set(
            d.get("mangon_ext_conduccion", self.v_mangon_ext_conduccion.get()))
        self.v_mangon_ext_conducido.set(
            d.get("mangon_ext_conducido", self.v_mangon_ext_conducido.get()))

        self.v_mangones_intermedios.set(
            bool(d.get("mangones_intermedios", False)))
        self.v_num_mangones_intermedios.set(
            d.get("num_mangones_intermedios", ""))
        self.v_diam_mangon_intermedio.set(d.get("diam_mangon_intermedio", ""))

        self.v_metrica_tornillos.set(
            d.get("metrica_tornillos", self.v_metrica_tornillos.get()))

        self.v_diam_espira.set(d.get("diam_espira", self.v_diam_espira.get()))
        self.v_espesor_espira.set(
            d.get("espesor_espira", self.v_espesor_espira.get()))
        self.v_paso1.set(d.get("paso1", self.v_paso1.get()))
        self.v_paso2.set(d.get("paso2", self.v_paso2.get()))
        self.v_paso3.set(d.get("paso3", self.v_paso3.get()))

        # CAMISA
        self.v_dist_testeros.set(
            d.get("distancia_testeros", self.v_dist_testeros.get()))

        self.v_002A_tubo.set(d.get("002A_tubo", ""))
        self.v_002A_testeros.set(d.get("002A_testeros", ""))
        self.v_002A_ventana_inspeccion.set(
            d.get("002A_ventana_inspeccion", ""))
        self.v_002A_suj_mangon_intermedio.set(
            d.get("002A_suj_mangon_intermedio", ""))
        self.v_002A_boca_entrada.set(d.get("002A_boca_entrada", ""))
        self.v_002A_boca_salida.set(d.get("002A_boca_salida", ""))

        self.v_002B_chapa_artesa.set(d.get("002B_chapa_artesa", ""))
        self.v_002B_testeros.set(d.get("002B_testeros", ""))
        self.v_002B_ventana_inspeccion.set(
            d.get("002B_ventana_inspeccion", ""))
        self.v_002B_suj_mangon_intermedio.set(
            d.get("002B_suj_mangon_intermedio", ""))
        self.v_002B_boca_entrada.set(d.get("002B_boca_entrada", ""))
        self.v_002B_boca_salida.set(d.get("002B_boca_salida", ""))

        # CONDUCCIÓN / CONDUCIDO
        self.v_rod_conduccion.set(d.get("rodamiento_conduccion", d.get(
            "rodamiento", self.v_rod_conduccion.get())))
        self.v_pos_motor.set(d.get("posicion_motor", self.v_pos_motor.get()))
        self.v_rod_conducido.set(
            d.get("rodamiento_conducido", self.v_rod_conducido.get()))

        self._on_eje_od_changed()
        self._auto_from_tubo()
        self._recalc_longitudes()
        self._apply_pending_style()
        self._render_section()

    def _save_definition(self):
        data = {
            # GENERAL
            "material": self.v_material.get().strip(),
            "camisa_tipo": self.v_camisa_tipo.get().strip(),
            "sentido_giro": self.v_sentido.get().strip(),
            "longitud_entre_testeros": self.v_long_test.get().strip(),
            "pendiente_medir_cliente": bool(self.v_pendiente_medir.get()),
            "observaciones": self._get_observaciones(),

            # Disposición motor (Parte 003)
            "tipo_disposicion": self.v_tipo_dispos.get().strip(),

            # TORNILLO
            "eje_od": self.v_eje_od.get().strip(),
            "eje_thk": self.v_eje_thk.get().strip(),
            "eje_id_calc": _safe_float_text(tubo_id_mm(self.v_eje_od.get(), self.v_eje_thk.get())),

            "mangon_conduccion": self.v_mangon_conduccion.get().strip(),
            "mangon_conducido": self.v_mangon_conducido.get().strip(),

            "mangon_ext_conduccion": self.v_mangon_ext_conduccion.get().strip(),
            "mangon_ext_conducido": self.v_mangon_ext_conducido.get().strip(),

            "mangones_intermedios": bool(self.v_mangones_intermedios.get()),
            "num_mangones_intermedios": self.v_num_mangones_intermedios.get().strip(),
            "diam_mangon_intermedio": self.v_diam_mangon_intermedio.get().strip(),

            "metrica_tornillos": self.v_metrica_tornillos.get().strip(),

            "diam_espira": self.v_diam_espira.get().strip(),
            "espesor_espira": self.v_espesor_espira.get().strip(),
            "paso1": self.v_paso1.get().strip(),
            "paso2": self.v_paso2.get().strip(),
            "paso3": self.v_paso3.get().strip(),

            # CAMISA
            "distancia_testeros": self.v_dist_testeros.get().strip(),

            "002A_tubo": self.v_002A_tubo.get().strip(),
            "002A_testeros": self.v_002A_testeros.get().strip(),
            "002A_ventana_inspeccion": self.v_002A_ventana_inspeccion.get().strip(),
            "002A_suj_mangon_intermedio": self.v_002A_suj_mangon_intermedio.get().strip(),
            "002A_boca_entrada": self.v_002A_boca_entrada.get().strip(),
            "002A_boca_salida": self.v_002A_boca_salida.get().strip(),

            "002B_chapa_artesa": self.v_002B_chapa_artesa.get().strip(),
            "002B_testeros": self.v_002B_testeros.get().strip(),
            "002B_ventana_inspeccion": self.v_002B_ventana_inspeccion.get().strip(),
            "002B_suj_mangon_intermedio": self.v_002B_suj_mangon_intermedio.get().strip(),
            "002B_boca_entrada": self.v_002B_boca_entrada.get().strip(),
            "002B_boca_salida": self.v_002B_boca_salida.get().strip(),

            # CONDUCCIÓN / CONDUCIDO
            "rodamiento_conduccion": self.v_rod_conduccion.get().strip(),
            "posicion_motor": self.v_pos_motor.get().strip(),
            "rodamiento_conducido": self.v_rod_conducido.get().strip(),
        }

        con = connect()
        try:
            set_sinfin_definicion(con, self.sinfin_id, data)
        finally:
            con.close()

        messagebox.showinfo("Guardado", "Definición guardada.")
        if self.on_updated_callback:
            try:
                self.on_updated_callback()
            except Exception:
                pass

    def _load_progress(self):
        con = connect()
        try:
            procs = list_tareas_por_proceso(con) or []

            self.tree_prog.delete(*self.tree_prog.get_children())
            self._tree_item_to_tarea_id = {}

            total = 0
            done = 0

            for p in procs:
                proc_name = p.get("nombre", "")
                for t in p.get("tareas", []):
                    tarea_id = int(t["id"])
                    tarea_name = str(t["nombre"])

                    est = get_estado_tarea(con, self.sinfin_id, tarea_id)
                    estado_txt = "HECHO" if int(est) == 1 else "PENDIENTE"

                    iid = self.tree_prog.insert("", "end", values=(
                        proc_name, tarea_name, estado_txt))
                    self._tree_item_to_tarea_id[iid] = tarea_id

                    total += 1
                    if int(est) == 1:
                        done += 1

            pct = (done / total * 100.0) if total else 0.0
            self.lbl_pct.configure(text=f"{pct:.1f}%")

        finally:
            con.close()

        if self.on_updated_callback:
            try:
                self.on_updated_callback()
            except Exception:
                pass
