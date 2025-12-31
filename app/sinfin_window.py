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


class SinfinWindow(tk.Toplevel):
    def __init__(self, parent, sinfin_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.sinfin_id = sinfin_id
        self.on_updated_callback = on_updated_callback

        self.title("Sinfín – Definición / Progreso")
        self.geometry("980x680")
        self.configure(bg="#1e1e1e")

        # ===== vars definición =====
        self.v_material = tk.StringVar()
        self.v_diam_eje_tubo = tk.StringVar()
        self.v_camisa_tipo = tk.StringVar(
            value="ARTESA")      # ARTESA | CIRCULAR
        self.v_diam_ext_espira = tk.StringVar()
        self.v_paso_1 = tk.StringVar()
        self.v_paso_2 = tk.StringVar()
        self.v_sentido = tk.StringVar(
            value="DERECHAS")        # DERECHAS | IZQUIERDAS
        self.v_long_test = tk.StringVar()
        self.v_esp_test = tk.StringVar()
        self.v_esp_bridas = tk.StringVar()
        self.v_pos_motor = tk.StringVar()

        # ===== vars progreso =====
        self.vars_checks = {}  # tarea_id -> IntVar

        self._build_ui()
        self.load_all()

    # ---------------- UI ----------------
    def _build_ui(self):
        # Notebook
        self.nb = ttk.Notebook(self)
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
            top, text="DEFINICIÓN DEL SINFÍN",
            fg="white", bg="#1e1e1e",
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        ttk.Button(top, text="💾 Guardar definición",
                   command=self.save_definition).pack(side="right", padx=6)
        ttk.Button(top, text="🔄 Recargar", command=self.load_definition).pack(
            side="right", padx=6)

        form = tk.Frame(self.tab_def, bg="#1e1e1e")
        form.pack(fill="both", expand=True, padx=10, pady=10)

        def add_row(r, label, widget):
            tk.Label(form, text=label, fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 10)).grid(
                row=r, column=0, sticky="w", pady=6
            )
            widget.grid(row=r, column=1, sticky="we", pady=6)
            return r + 1

        form.grid_columnconfigure(1, weight=1)

        # Listas (por ahora “fijas”; luego las leemos de CSV)
        MATERIALS = ["S275JR", "S355J2+N", "HARDOX 400",
                     "HARDOX 450", "HARDOX 500", "AISI 304", "AISI 316"]

        r = 0

        cb_mat = ttk.Combobox(form, textvariable=self.v_material,
                              values=MATERIALS, state="readonly")
        r = add_row(r, "Material", cb_mat)

        ent_eje = ttk.Entry(form, textvariable=self.v_diam_eje_tubo)
        r = add_row(r, "Diámetro tubo eje tornillo (Ø exterior, mm)", ent_eje)

        # Camisa tipo (excluyente)
        box_cam = tk.Frame(form, bg="#1e1e1e")
        rb1 = ttk.Radiobutton(box_cam, text="Artesa",
                              value="ARTESA", variable=self.v_camisa_tipo)
        rb2 = ttk.Radiobutton(box_cam, text="Tubo circular",
                              value="CIRCULAR", variable=self.v_camisa_tipo)
        rb1.pack(side="left", padx=(0, 12))
        rb2.pack(side="left")
        r = add_row(r, "Forma de la camisa", box_cam)

        ent_de = ttk.Entry(form, textvariable=self.v_diam_ext_espira)
        r = add_row(r, "Diámetro exterior espira (mm)", ent_de)

        ent_p1 = ttk.Entry(form, textvariable=self.v_paso_1)
        r = add_row(r, "Paso espiras – Paso 1 (mm)", ent_p1)

        ent_p2 = ttk.Entry(form, textvariable=self.v_paso_2)
        r = add_row(r, "Paso espiras – Paso 2 (mm) [opcional]", ent_p2)

        # Sentido giro (excluyente)
        box_giro = tk.Frame(form, bg="#1e1e1e")
        rg1 = ttk.Radiobutton(box_giro, text="A derechas",
                              value="DERECHAS", variable=self.v_sentido)
        rg2 = ttk.Radiobutton(box_giro, text="A izquierdas",
                              value="IZQUIERDAS", variable=self.v_sentido)
        rg1.pack(side="left", padx=(0, 12))
        rg2.pack(side="left")
        r = add_row(r, "Sentido de giro", box_giro)

        ent_L = ttk.Entry(form, textvariable=self.v_long_test)
        r = add_row(r, "Longitud entre testeros (mm)", ent_L)

        ent_et = ttk.Entry(form, textvariable=self.v_esp_test)
        r = add_row(r, "Espesor testeros (mm)", ent_et)

        ent_eb = ttk.Entry(form, textvariable=self.v_esp_bridas)
        r = add_row(r, "Espesor bridas (mm)", ent_eb)

        # Nota
        tk.Label(
            self.tab_def,
            text="(Luego conectamos esto con: numeración de planos, listas CSV, y generación de solicitudes a proveedores.)",
            fg="#777777", bg="#1e1e1e", font=("Segoe UI", 9)
        ).pack(anchor="w", padx=12, pady=(0, 8))

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

    # ---------------- LOAD/SAVE ----------------
    def load_all(self):
        self.load_definition()
        self.load_progress()

    # ===== Definición =====
    def load_definition(self):
        con = connect()
        d = get_sinfin_definicion(con, self.sinfin_id)
        con.close()

        # Cargar vars (si faltan, se quedan como estén)
        self.v_material.set(d.get("material", self.v_material.get()))
        self.v_diam_eje_tubo.set(
            d.get("diametro_eje_tubo", self.v_diam_eje_tubo.get()))
        self.v_camisa_tipo.set(d.get("camisa_tipo", self.v_camisa_tipo.get()))
        self.v_diam_ext_espira.set(
            d.get("diam_ext_espira", self.v_diam_ext_espira.get()))
        self.v_paso_1.set(d.get("paso_1", self.v_paso_1.get()))
        self.v_paso_2.set(d.get("paso_2", self.v_paso_2.get()))
        self.v_sentido.set(d.get("sentido_giro", self.v_sentido.get()))
        self.v_long_test.set(
            d.get("long_entre_testeros", self.v_long_test.get()))
        self.v_esp_test.set(d.get("espesor_testeros", self.v_esp_test.get()))
        self.v_esp_bridas.set(d.get("espesor_bridas", self.v_esp_bridas.get()))
        self.v_pos_motor.set(d.get("pos_motor", self.v_pos_motor.get()))

    def save_definition(self):
        # Guardamos tal cual (texto), y además guardamos versión numérica cuando se pueda
        defin = {
            "material": self.v_material.get().strip(),
            "diametro_eje_tubo": self.v_diam_eje_tubo.get().strip(),
            "camisa_tipo": self.v_camisa_tipo.get().strip(),
            "diam_ext_espira": self.v_diam_ext_espira.get().strip(),
            "paso_1": self.v_paso_1.get().strip(),
            "paso_2": self.v_paso_2.get().strip(),
            "sentido_giro": self.v_sentido.get().strip(),
            "long_entre_testeros": self.v_long_test.get().strip(),
            "espesor_testeros": self.v_esp_test.get().strip(),
            "espesor_bridas": self.v_esp_bridas.get().strip(),
            "pos_motor": self.v_pos_motor.get().strip(),

            # útiles para cálculos (floats)
            "_num": {
                "diametro_eje_tubo": _to_number(self.v_diam_eje_tubo.get()),
                "diam_ext_espira": _to_number(self.v_diam_ext_espira.get()),
                "paso_1": _to_number(self.v_paso_1.get()),
                "paso_2": _to_number(self.v_paso_2.get()),
                "long_entre_testeros": _to_number(self.v_long_test.get()),
                "espesor_testeros": _to_number(self.v_esp_test.get()),
                "espesor_bridas": _to_number(self.v_esp_bridas.get()),
            }
        }

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
                v = tk.IntVar(value=get_estado_tarea(
                    con, self.sinfin_id, t["id"]))
                self.vars_checks[t["id"]] = v

                cb = tk.Checkbutton(
                    self.inner,
                    text=t["nombre"],
                    variable=v,
                    command=self.save_progress,   # <- guarda al marcar
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
