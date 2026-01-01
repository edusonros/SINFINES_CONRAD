import tkinter as tk
from tkinter import ttk, messagebox

from utils.db import connect, list_sinfines_por_pedido, add_sinfin, rename_sinfin


class PedidoWindow(tk.Toplevel):
    def __init__(self, parent, pedido_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.pedido_id = pedido_id
        self.on_updated_callback = on_updated_callback

        self.title("Pedido — SINFINES CONRAD")
        self.geometry("900x600")
        self.configure(bg="#1e1e1e")

        # --- Tabla (Treeview) en gris claro ---
        style = ttk.Style()
        style.configure(
            "Conrad.Treeview",
            background="#d6d6d6",
            fieldbackground="#d6d6d6",
            foreground="#111111",
            rowheight=24,
            borderwidth=0,
        )
        style.map(
            "Conrad.Treeview",
            background=[("selected", "#9ecae1")],
            foreground=[("selected", "#000000")],
        )
        style.configure(
            "Conrad.Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#c2c2c2",
            foreground="#111111",
        )

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        header = tk.Frame(self, bg="#1e1e1e")
        header.pack(fill="x", padx=16, pady=(12, 8))

        self.lbl_title = tk.Label(
            header,
            text="SINFINES DEL PEDIDO",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 14, "bold"),
        )
        self.lbl_title.pack(side="left")

        # Tabla sinfines
        table = tk.Frame(self, bg="#1e1e1e")
        table.pack(fill="both", expand=True, padx=16, pady=12)

        self.tree = ttk.Treeview(
            table,
            style="Conrad.Treeview",
            columns=("nombre",),
            show="headings",
            height=18,
        )
        self.tree.heading("nombre", text="Sinfines")
        self.tree.column("nombre", width=600, anchor="w")

        yscroll = ttk.Scrollbar(table, orient="vertical",
                                command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.on_open_sinfin())

        # Botonera
        footer = tk.Frame(self, bg="#1e1e1e")
        footer.pack(fill="x", padx=16, pady=(0, 14))

        ttk.Button(footer, text="➕ Añadir Sinfín", command=self.on_add_sinfin).pack(
            side="left", padx=6
        )
        ttk.Button(footer, text="✏️ Renombrar", command=self.on_rename_sinfin).pack(
            side="left", padx=6
        )
        ttk.Button(footer, text="🔄 Recargar", command=self.refresh).pack(
            side="right", padx=6)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        con = connect()
        sinfines = list_sinfines_por_pedido(con, self.pedido_id)
        con.close()

        for s in sinfines:
            self.tree.insert("", "end", iid=str(
                s["id"]), values=(s["nombre"],))

    def on_add_sinfin(self):
        con = connect()
        add_sinfin(con, self.pedido_id)
        con.close()
        self.refresh()
        if self.on_updated_callback:
            self.on_updated_callback()

    def on_rename_sinfin(self):
        sel = self.tree.selection()
        if not sel:
            return
        sinfin_id = int(sel[0])
        old = self.tree.item(sel[0], "values")[0]

        win = tk.Toplevel(self)
        win.title("Renombrar sinfín")
        win.configure(bg="#1e1e1e")
        win.geometry("420x140")

        tk.Label(win, text="Nuevo nombre:", bg="#1e1e1e", fg="white").pack(
            anchor="w", padx=12, pady=(12, 6)
        )
        v = tk.StringVar(value=old)
        ent = ttk.Entry(win, textvariable=v)
        ent.pack(fill="x", padx=12)

        def do():
            new = v.get().strip()
            if not new:
                return
            con = connect()
            rename_sinfin(con, sinfin_id, new)
            con.close()
            win.destroy()
            self.refresh()
            if self.on_updated_callback:
                self.on_updated_callback()

        ttk.Button(win, text="Guardar", command=do).pack(pady=12)

    def on_open_sinfin(self):
        sel = self.tree.selection()
        if not sel:
            return
        sinfin_id = int(sel[0])

        # import aquí para evitar ciclos
        from app.sinfin_window import SinfinWindow

        SinfinWindow(self, sinfin_id, on_updated_callback=self.refresh)
