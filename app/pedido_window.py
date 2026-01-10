# app/pedido_window.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from utils.db import connect, get_pedido, list_sinfines, create_sinfin, rename_sinfin
from utils.progress import sinfin_progress, estado_from_pct


def _setup_tree_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # tabla gris claro
    style.configure(
        "Conrad.Treeview",
        background="#dedede",
        fieldbackground="#dedede",
        foreground="#000000",
        rowheight=26,
        borderwidth=0,
    )
    style.map(
        "Conrad.Treeview",
        background=[("selected", "#3a86ff")],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "Conrad.Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )


class PedidoWindow(tk.Toplevel):
    def __init__(self, parent, pedido_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.pedido_id = pedido_id
        self.on_updated_callback = on_updated_callback

        self.title("Pedido – SINFINES CONRAD")
        self.geometry("860x520")
        self.configure(bg="#1e1e1e")

        _setup_tree_style()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        head = tk.Frame(self, bg="#1e1e1e")
        head.pack(fill="x", padx=14, pady=(12, 8))

        self.lbl_title = tk.Label(
            head,
            text="",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 14, "bold"),
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = tk.Label(
            head,
            text="",
            fg="#bdbdbd",
            bg="#1e1e1e",
            font=("Segoe UI", 10),
        )
        self.lbl_sub.pack(anchor="w", pady=(2, 0))

        # botones
        bar = tk.Frame(self, bg="#1e1e1e")
        bar.pack(fill="x", padx=14, pady=(6, 8))

        ttk.Button(bar, text="➕ Añadir Sinfín",
                   command=self.on_add).pack(side="left", padx=6)
        ttk.Button(bar, text="✏️ Renombrar", command=self.on_rename).pack(
            side="left", padx=6)
        ttk.Button(bar, text="📂 Abrir Sinfín",
                   command=self.on_open).pack(side="left", padx=6)
        ttk.Button(bar, text="🔄 Refrescar", command=self.refresh).pack(
            side="right", padx=6)

        # tabla
        table_frame = tk.Frame(self, bg="#1e1e1e")
        table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        cols = ("nombre", "estado", "progreso")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            style="Conrad.Treeview",
        )

        self.tree.heading("nombre", text="Sinfín")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("progreso", text="Progreso")

        self.tree.column("nombre", width=420, anchor="w")
        self.tree.column("estado", width=160, anchor="center")
        self.tree.column("progreso", width=120, anchor="e")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.on_open())

        # footer
        foot = tk.Frame(self, bg="#1e1e1e")
        foot.pack(fill="x", padx=14, pady=(0, 10))

        self.lbl_pedido_pct = tk.Label(
            foot,
            text="",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_pedido_pct.pack(side="right")

    def refresh(self):
        con = connect()
        ped = get_pedido(con, self.pedido_id)

        if ped:
            self.lbl_title.config(
                text=f"{ped['numero_pedido']} — {ped['cliente'] or ''}".strip())
            entrega = ped["fecha_entrega"] or "—"
            self.lbl_sub.config(text=f"Entrega: {entrega}")

        for i in self.tree.get_children():
            self.tree.delete(i)

        sinfines = list_sinfines(con, self.pedido_id)

        # relleno
        total = 0.0
        n = 0
        for s in sinfines:
            pct = sinfin_progress(con, s["id"])
            estado = estado_from_pct(pct)
            self.tree.insert("", "end", iid=str(s["id"]), values=(
                s["nombre"], estado, f"{pct:.1f}%"))
            total += pct
            n += 1

        pedido_pct = (total / n) if n else 0.0
        self.lbl_pedido_pct.config(text=f"Progreso pedido: {pedido_pct:.1f}%")

        con.close()

        if self.on_updated_callback:
            self.on_updated_callback()

    def _selected_sinfin_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def on_add(self):
        name = simpledialog.askstring(
            "Añadir sinfín", "Nombre del sinfín:", parent=self)
        if not name:
            return
        con = connect()
        create_sinfin(con, self.pedido_id, name)
        con.close()
        self.refresh()

    def on_rename(self):
        sid = self._selected_sinfin_id()
        if not sid:
            messagebox.showinfo("Renombrar", "Selecciona un sinfín.")
            return
        new_name = simpledialog.askstring(
            "Renombrar", "Nuevo nombre:", parent=self)
        if not new_name:
            return
        con = connect()
        rename_sinfin(con, sid, new_name)
        con.close()
        self.refresh()

    def on_open(self):
        sid = self._selected_sinfin_id()
        if not sid:
            messagebox.showinfo("Abrir", "Selecciona un sinfín.")
            return

        from app.sinfin_window import SinfinWindow  # evitar ciclos
        SinfinWindow(self, sid, on_updated_callback=self.refresh)
