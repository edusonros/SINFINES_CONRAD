import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

from utils.db import connect
from app.pedido_window import PedidoWindow


class MainTkinterApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("SINFINES_CONRAD")
        self.geometry("1050x720")
        self.configure(bg="#1e1e1e")

        ttk.Style().configure("Conrad.TButton", font=("Segoe UI", 10, "bold"))

        # --- Tabla (Treeview) en gris claro ---
        style = ttk.Style()
        style.configure(
            "Conrad.Treeview",
            background="#d6d6d6",
            fieldbackground="#d6d6d6",
            foreground="#111111",
            rowheight=26,
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
        # Encabezado
        header = tk.Frame(self, bg="#1e1e1e")
        header.pack(fill="x", padx=16, pady=(12, 8))

        tk.Label(
            header,
            text="OFICINA TÉCNICA",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text="PEDIDOS",
            fg="#00bcd4",
            bg="#1e1e1e",
            font=("Segoe UI", 20, "bold"),
        ).pack(side="right")

        # Tabla
        table_frame = tk.Frame(self, bg="#1e1e1e")
        table_frame.pack(fill="both", expand=True, padx=16, pady=12)

        cols = ("codigo", "cliente", "entrega", "estado", "progreso")
        self.tree = ttk.Treeview(
            table_frame,
            style="Conrad.Treeview",
            columns=cols,
            show="headings",
            height=16,
        )

        self.tree.heading("codigo", text="Código")
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("entrega", text="Entrega")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("progreso", text="Progreso")

        self.tree.column("codigo", width=140, anchor="w")
        self.tree.column("cliente", width=260, anchor="w")
        self.tree.column("entrega", width=120, anchor="center")
        self.tree.column("estado", width=140, anchor="center")
        self.tree.column("progreso", width=120, anchor="center")

        yscroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        # Tags (mantenemos el color por estado, pero con fondo gris claro)
        self.tree.tag_configure(
            "NO_INICIADO", foreground="#a0a0a0", background="#d6d6d6")
        self.tree.tag_configure(
            "EN_CURSO", foreground="#ffcc00", background="#d6d6d6")
        self.tree.tag_configure(
            "FINALIZADO", foreground="#00c853", background="#d6d6d6")

        self.tree.bind("<Double-1>", lambda e: self.on_open_pedido())

        # Botonera
        footer = tk.Frame(self, bg="#1e1e1e")
        footer.pack(fill="x", padx=16, pady=(0, 14))

        ttk.Button(footer, text="🔄 Recargar", style="Conrad.TButton", command=self.refresh).pack(
            side="right", padx=6
        )

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        con = connect()
        try:
            rows = con.execute(
                """
                SELECT id, codigo, cliente, entrega, estado, progreso
                FROM pedidos
                ORDER BY id DESC
                """
            ).fetchall()
        except sqlite3.OperationalError:
            # Si la tabla no existe aún
            rows = []
        finally:
            con.close()

        for r in rows:
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(r["codigo"], r["cliente"], r["entrega"],
                        r["estado"], r["progreso"]),
                tags=(str(r["estado"]).upper(),),
            )

    def on_open_pedido(self):
        sel = self.tree.selection()
        if not sel:
            return
        pedido_id = int(sel[0])
        PedidoWindow(self, pedido_id, on_updated_callback=self.refresh)


if __name__ == "__main__":
    app = MainTkinterApp()
    app.mainloop()
