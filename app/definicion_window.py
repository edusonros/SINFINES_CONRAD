# app/definicion_window.py
import tkinter as tk
from tkinter import ttk, messagebox

from utils.db import connect, get_sinfin_definicion, set_sinfin_definicion
from utils import catalogs


def _num_validate(P: str) -> bool:
    # permite vacío mientras escribes
    if P.strip() == "":
        return True
    # admite coma o punto
    s = P.replace(",", ".")
    try:
        float(s)
        return True
    except ValueError:
        return False


class DefinicionWindow(tk.Toplevel):
    def __init__(self, parent, sinfin_id: int, on_saved=None):
        super().__init__(parent)
        self.parent = parent
        self.sinfin_id = sinfin_id
        self.on_saved = on_saved

        self.title("Definición – Sinfín")
        self.geometry("1100x720")
        self.configure(bg="#1e1e1e")

        self._vnum = (self.register(_num_validate), "%P")

        # estado interno (vars)
        self.var_material = tk.StringVar()
        self.var_giro = tk.StringVar()

        self.var_eje_d = tk.StringVar()
        self.var_eje_L = tk.StringVar()

        self.var_camisa_tipo = tk.StringVar(value="TUBO")  # TUBO / ARTESA
        self.var_tubo_od = tk.StringVar()
        self.var_tubo_e = tk.StringVar()
        self.var_tubo_id = tk.StringVar()
        self.var_dist_test = tk.StringVar()

        self.var_rod_d = tk.StringVar()
        self.var_rod_ref = tk.StringVar()
        self.var_rod_d_dim = tk.StringVar()
        self.var_rod_D_dim = tk.StringVar()
        self.var_rod_B_dim = tk.StringVar()

        self.var_pos_mr = tk.StringVar()

        self._build_ui()
        self.load()

    def _build_ui(self):
        # --- Top bar
        top = tk.Frame(self, bg="#1e1e1e")
        top.pack(fill="x", padx=14, pady=10)

        tk.Label(top, text="Definición sinfín", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        ttk.Button(top, text="💾 Guardar", command=self.save).pack(
            side="right", padx=6)
        ttk.Button(top, text="🔄 Recargar", command=self.load).pack(
            side="right", padx=6)

        # --- Main split
        main = tk.Frame(self, bg="#1e1e1e")
        main.pack(fill="both", expand=True, padx=14, pady=10)

        left = tk.Frame(main, bg="#1e1e1e")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(main, bg="#141414", width=320)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Right panel (imagen/nota)
        tk.Label(right, text="Vista / Imagen", fg="white", bg="#141414",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        self.lbl_img = tk.Label(right, text="(Aquí pondremos imágenes por pestaña)",
                                fg="#bbbbbb", bg="#141414", justify="left", wraplength=290)
        self.lbl_img.pack(anchor="w", padx=10)

        ttk.Separator(right).pack(fill="x", pady=12)
        tk.Label(right, text="Notas rápidas", fg="white", bg="#141414",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(0, 6))
        self.txt_notes = tk.Text(right, height=10)
        self.txt_notes.pack(fill="x", padx=10, pady=(0, 10))

        # Notebook
        self.nb = ttk.Notebook(left)
        self.nb.pack(fill="both", expand=True)

        self.tab_general = tk.Frame(self.nb, bg="#1e1e1e")
        self.tab_001 = tk.Frame(self.nb, bg="#1e1e1e")
        self.tab_002 = tk.Frame(self.nb, bg="#1e1e1e")
        self.tab_003 = tk.Frame(self.nb, bg="#1e1e1e")
        self.tab_004 = tk.Frame(self.nb, bg="#1e1e1e")

        self.nb.add(self.tab_general, text="General")
        self.nb.add(self.tab_001, text="001 Tornillo")
        self.nb.add(self.tab_002, text="002 Camisa")
        self.nb.add(self.tab_003, text="003 Conducción")
        self.nb.add(self.tab_004, text="004 Conducido")

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab)

        self._build_general()
        self._build_001()
        self._build_002()
        self._build_003()
        self._build_004()

    def _on_tab(self, _evt=None):
        idx = self.nb.index(self.nb.select())
        hints = {
            0: "General: material, sentido giro, observaciones.",
            1: "Tornillo: Ø eje (lista), longitud (libre), espiras (catálogo en siguiente iteración).",
            2: "Camisa: TUBO/ARTESA. Para TUBO: OD/espesor/ID desde catálogo.",
            3: "Conducción: rodamientos filtrados por d, posición motorreductor aquí.",
            4: "Conducido: (igual que conducción, lo afinamos luego).",
        }
        self.lbl_img.config(text=hints.get(idx, ""))

    # -----------------------------
    # TAB GENERAL
    # -----------------------------
    def _build_general(self):
        f = self.tab_general
        row = 0

        tk.Label(f, text="MATERIAL", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(12, 4), padx=12)
        mats = catalogs.get_materiales()
        self.cb_material = ttk.Combobox(
            f, textvariable=self.var_material, values=mats, state="readonly", width=30)
        self.cb_material.grid(row=row, column=1, sticky="w", padx=12)
        row += 1

        tk.Label(f, text="SENTIDO DE GIRO", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(12, 4), padx=12)
        self.cb_giro = ttk.Combobox(f, textvariable=self.var_giro,
                                    values=["A DERECHAS", "A IZQUIERDAS"], state="readonly", width=30)
        self.cb_giro.grid(row=row, column=1, sticky="w", padx=12)
        row += 1

        tk.Label(f, text="OBSERVACIONES (del sinfín)", fg="white", bg="#1e1e1e").grid(
            row=row, column=0, sticky="nw", pady=(12, 4), padx=12
        )
        self.txt_obs = tk.Text(f, height=8, width=60)
        self.txt_obs.grid(row=row, column=1, sticky="w", padx=12)
        row += 1

    # -----------------------------
    # TAB 001 TORNILLO
    # -----------------------------
    def _build_001(self):
        f = self.tab_001

        tk.Label(f, text="001.001  EJE TUBO / LONGITUD", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(12, 6), padx=12)

        tk.Label(f, text="Ø eje (lista)", fg="white", bg="#1e1e1e").grid(
            row=1, column=0, sticky="w", padx=12)
        eje_vals = catalogs.get_eje_diametros()
        self.cb_eje = ttk.Combobox(
            f, textvariable=self.var_eje_d, values=eje_vals, state="readonly", width=18)
        self.cb_eje.grid(row=1, column=1, sticky="w", padx=12)

        tk.Label(f, text="Longitud (mm) (libre)", fg="white", bg="#1e1e1e").grid(
            row=2, column=0, sticky="w", padx=12, pady=(8, 0))
        self.en_L = ttk.Entry(f, textvariable=self.var_eje_L,
                              validate="key", validatecommand=self._vnum, width=18)
        self.en_L.grid(row=2, column=1, sticky="w", padx=12, pady=(8, 0))

        ttk.Separator(f).grid(row=3, column=0, columnspan=3,
                              sticky="ew", pady=14, padx=12)

        tk.Label(f, text="001.005  ESPIRAS (catálogo: siguiente iteración)", fg="#cccccc", bg="#1e1e1e").grid(
            row=4, column=0, sticky="w", padx=12
        )
        tk.Label(f, text="(De momento lo dejamos preparado; cuando metas catálogo de espiras lo conectamos)",
                 fg="#888888", bg="#1e1e1e").grid(row=5, column=0, sticky="w", padx=12)

    # -----------------------------
    # TAB 002 CAMISA
    # -----------------------------
    def _build_002(self):
        f = self.tab_002

        tk.Label(f, text="TIPO DE CAMISA", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(12, 6), padx=12)

        rb1 = ttk.Radiobutton(f, text="TUBO CIRCULAR", value="TUBO",
                              variable=self.var_camisa_tipo, command=self._toggle_camisa)
        rb2 = ttk.Radiobutton(f, text="ARTESA", value="ARTESA",
                              variable=self.var_camisa_tipo, command=self._toggle_camisa)
        rb1.grid(row=1, column=0, sticky="w", padx=12)
        rb2.grid(row=1, column=1, sticky="w", padx=12)

        ttk.Separator(f).grid(row=2, column=0, columnspan=3,
                              sticky="ew", pady=12, padx=12)

        # Frame TUBO
        self.fr_tubo = tk.Frame(f, bg="#1e1e1e")
        self.fr_tubo.grid(row=3, column=0, columnspan=3, sticky="nw", padx=12)

        tk.Label(self.fr_tubo, text="002A  CAMISA TUBO", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 8))

        tk.Label(self.fr_tubo, text="Distancia entre testeros (mm)",
                 fg="white", bg="#1e1e1e").grid(row=1, column=0, sticky="w")
        ttk.Entry(self.fr_tubo, textvariable=self.var_dist_test, validate="key",
                  validatecommand=self._vnum, width=20).grid(row=1, column=1, sticky="w", padx=10)

        tk.Label(self.fr_tubo, text="Ø exterior tubo (lista)", fg="white",
                 bg="#1e1e1e").grid(row=2, column=0, sticky="w", pady=(8, 0))
        od_vals = catalogs.get_tubo_exteriores()
        self.cb_tubo_od = ttk.Combobox(
            self.fr_tubo, textvariable=self.var_tubo_od, values=od_vals, state="readonly", width=18)
        self.cb_tubo_od.grid(row=2, column=1, sticky="w", padx=10, pady=(8, 0))
        self.cb_tubo_od.bind("<<ComboboxSelected>>",
                             lambda e: self._on_od_changed())

        tk.Label(self.fr_tubo, text="Espesor (lista por OD)", fg="white",
                 bg="#1e1e1e").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.cb_tubo_e = ttk.Combobox(
            self.fr_tubo, textvariable=self.var_tubo_e, values=[], state="readonly", width=18)
        self.cb_tubo_e.grid(row=3, column=1, sticky="w", padx=10, pady=(8, 0))
        self.cb_tubo_e.bind("<<ComboboxSelected>>",
                            lambda e: self._on_e_changed())

        tk.Label(self.fr_tubo, text="Ø interior (auto)", fg="white",
                 bg="#1e1e1e").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.en_tubo_id = ttk.Entry(
            self.fr_tubo, textvariable=self.var_tubo_id, state="readonly", width=18)
        self.en_tubo_id.grid(row=4, column=1, sticky="w", padx=10, pady=(8, 0))

        # Frame ARTESA (placeholder)
        self.fr_artesa = tk.Frame(f, bg="#1e1e1e")
        self.fr_artesa.grid(row=4, column=0, columnspan=3,
                            sticky="nw", padx=12)

        tk.Label(self.fr_artesa, text="002B  CAMISA ARTESA (lo conectamos al catálogo en la siguiente)",
                 fg="#cccccc", bg="#1e1e1e").grid(row=0, column=0, sticky="w", pady=(4, 8))

        self._toggle_camisa()

    def _toggle_camisa(self):
        tipo = self.var_camisa_tipo.get()
        if tipo == "TUBO":
            self.fr_tubo.grid()
            self.fr_artesa.grid_remove()
        else:
            self.fr_artesa.grid()
            self.fr_tubo.grid_remove()

    def _on_od_changed(self):
        od = self._safe_float(self.var_tubo_od.get())
        if od is None:
            self.cb_tubo_e["values"] = []
            self.var_tubo_e.set("")
            self.var_tubo_id.set("")
            return

        espesores = catalogs.get_tubo_espesores(od)
        self.cb_tubo_e["values"] = espesores
        self.var_tubo_e.set("")
        self.var_tubo_id.set("")

    def _on_e_changed(self):
        od = self._safe_float(self.var_tubo_od.get())
        e = self._safe_float(self.var_tubo_e.get())
        if od is None or e is None:
            self.var_tubo_id.set("")
            return
        di = catalogs.get_tubo_interior(od, e)
        self.var_tubo_id.set("" if di is None else f"{di:g}")

    # -----------------------------
    # TAB 003 CONDUCCIÓN
    # -----------------------------
    def _build_003(self):
        f = self.tab_003

        tk.Label(f, text="003.004  CONJUNTO RODAMIENTO", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(12, 6), padx=12)

        tk.Label(f, text="d (mm) (lista = Ø eje)", fg="white",
                 bg="#1e1e1e").grid(row=1, column=0, sticky="w", padx=12)
        self.cb_rod_d = ttk.Combobox(f, textvariable=self.var_rod_d, values=catalogs.get_eje_diametros(),
                                     state="readonly", width=18)
        self.cb_rod_d.grid(row=1, column=1, sticky="w", padx=12)
        self.cb_rod_d.bind("<<ComboboxSelected>>",
                           lambda e: self._on_rod_d_changed())

        tk.Label(f, text="Referencia (filtrada)", fg="white", bg="#1e1e1e").grid(
            row=2, column=0, sticky="w", padx=12, pady=(8, 0))
        self.cb_rod_ref = ttk.Combobox(
            f, textvariable=self.var_rod_ref, values=[], state="readonly", width=30)
        self.cb_rod_ref.grid(row=2, column=1, sticky="w", padx=12, pady=(8, 0))
        self.cb_rod_ref.bind("<<ComboboxSelected>>",
                             lambda e: self._on_rod_ref_changed())

        # dims
        tk.Label(f, text="d / D / B (auto)", fg="white",
                 bg="#1e1e1e").grid(row=3, column=0, sticky="w", padx=12, pady=(8, 0))
        dims = tk.Frame(f, bg="#1e1e1e")
        dims.grid(row=3, column=1, sticky="w", padx=12, pady=(8, 0))
        ttk.Entry(dims, textvariable=self.var_rod_d_dim, width=7,
                  state="readonly").pack(side="left", padx=(0, 6))
        ttk.Entry(dims, textvariable=self.var_rod_D_dim, width=7,
                  state="readonly").pack(side="left", padx=(0, 6))
        ttk.Entry(dims, textvariable=self.var_rod_B_dim, width=7,
                  state="readonly").pack(side="left", padx=(0, 6))

        ttk.Separator(f).grid(row=4, column=0, columnspan=3,
                              sticky="ew", pady=14, padx=12)

        tk.Label(f, text="003.005  MOTORREDUCTOR", fg="white", bg="#1e1e1e",
                 font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w", padx=12)

        tk.Label(f, text="Posición motorreductor", fg="white", bg="#1e1e1e").grid(
            row=6, column=0, sticky="w", padx=12, pady=(8, 0))
        self.cb_pos = ttk.Combobox(f, textvariable=self.var_pos_mr,
                                   values=["B3", "B5", "B6",
                                           "B7", "B8", "V5", "V6"],
                                   state="readonly", width=18)
        self.cb_pos.grid(row=6, column=1, sticky="w", padx=12, pady=(8, 0))

    def _on_rod_d_changed(self):
        d = self._safe_float(self.var_rod_d.get())
        refs = catalogs.get_rodamientos_for_d(d) if d is not None else []
        self.cb_rod_ref["values"] = refs
        self.var_rod_ref.set("")
        self.var_rod_d_dim.set("")
        self.var_rod_D_dim.set("")
        self.var_rod_B_dim.set("")

    def _on_rod_ref_changed(self):
        ref = self.var_rod_ref.get().strip()
        if not ref:
            return
        dims = catalogs.get_rodamiento_dims(ref)
        self.var_rod_d_dim.set("" if dims["d"] is None else f"{dims['d']:g}")
        self.var_rod_D_dim.set("" if dims["D"] is None else f"{dims['D']:g}")
        self.var_rod_B_dim.set("" if dims["B"] is None else f"{dims['B']:g}")

    # -----------------------------
    # TAB 004 CONDUCIDO (placeholder)
    # -----------------------------
    def _build_004(self):
        f = self.tab_004
        tk.Label(f, text="004 – Conducido (lo clonaremos de Conducción cuando lo afinemos)",
                 fg="#cccccc", bg="#1e1e1e").pack(anchor="w", padx=12, pady=12)

    # -----------------------------
    # LOAD / SAVE
    # -----------------------------
    def load(self):
        con = connect()
        data = get_sinfin_definicion(con, self.sinfin_id)
        con.close()

        # General
        self.var_material.set(data.get("material", "") or "S355J2+N")
        self.var_giro.set(data.get("giro", ""))
        self._set_text(self.txt_obs, data.get("observaciones", ""))

        # 001
        self.var_eje_d.set(str(data.get("eje_d", ""))
                           if data.get("eje_d") is not None else "")
        self.var_eje_L.set(str(data.get("eje_L", ""))
                           if data.get("eje_L") is not None else "")

        # 002
        self.var_camisa_tipo.set(data.get("camisa_tipo", "TUBO"))
        self.var_dist_test.set(str(data.get("dist_test", "")) if data.get(
            "dist_test") is not None else "")
        self.var_tubo_od.set(str(data.get("tubo_od", ""))
                             if data.get("tubo_od") is not None else "")
        self._on_od_changed()
        self.var_tubo_e.set(str(data.get("tubo_e", ""))
                            if data.get("tubo_e") is not None else "")
        self._on_e_changed()

        # 003
        self.var_rod_d.set(str(data.get("rod_d", ""))
                           if data.get("rod_d") is not None else "")
        self._on_rod_d_changed()
        self.var_rod_ref.set(data.get("rod_ref", ""))
        self._on_rod_ref_changed()
        self.var_pos_mr.set(data.get("pos_mr", ""))

        self._toggle_camisa()

        # Notas panel derecho
        self._set_text(self.txt_notes, data.get("notes", ""))

    def save(self):
        definicion = {
            "material": self.var_material.get().strip(),
            "giro": self.var_giro.get().strip(),
            "observaciones": self._get_text(self.txt_obs),
            "notes": self._get_text(self.txt_notes),

            "eje_d": self._safe_float(self.var_eje_d.get()),
            "eje_L": self._safe_float(self.var_eje_L.get()),

            "camisa_tipo": self.var_camisa_tipo.get(),
            "dist_test": self._safe_float(self.var_dist_test.get()),

            "tubo_od": self._safe_float(self.var_tubo_od.get()),
            "tubo_e": self._safe_float(self.var_tubo_e.get()),
            "tubo_id": self._safe_float(self.var_tubo_id.get()),

            "rod_d": self._safe_float(self.var_rod_d.get()),
            "rod_ref": self.var_rod_ref.get().strip(),

            "pos_mr": self.var_pos_mr.get().strip(),
        }

        con = connect()
        set_sinfin_definicion(con, self.sinfin_id, definicion)
        con.close()

        messagebox.showinfo("Guardar", "Definición guardada.")
        if self.on_saved:
            self.on_saved()

    # -----------------------------
    # helpers
    # -----------------------------
    def _safe_float(self, s: str):
        s = (s or "").strip()
        if not s:
            return None
        s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def _set_text(self, widget: tk.Text, value: str):
        widget.delete("1.0", "end")
        widget.insert("1.0", value or "")

    def _get_text(self, widget: tk.Text) -> str:
        return widget.get("1.0", "end").strip()
