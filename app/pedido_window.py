import tkinter as tk
from tkinter import ttk, messagebox

from utils.db import connect, get_pedido, list_sinfines, create_sinfin, rename_sinfin
from utils.progress import sinfin_progress, pedido_progress, estado_from_pct


class PedidoWindow(tk.Toplevel):
    def __init__(self, parent, pedido_id: int, on_updated_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.pedido_id = pedido_id
        self.on_updated_callback = on_updated_callback

        self.title("Pedido – SINFINES CONRAD")
        self.geometry("900x520")
        self.configure(bg="#1e1e1e")

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        top = tk.Frame(self, bg="#1e1e1e")
        top.pack(fill="x", padx=16, pady=12)

        self.lbl_title = tk.Label(
            top, text="", fg="white", bg="#1e1e1e", font=("Segoe UI", 14, "bold"))
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = tk.Label(
            top, text="", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 10))
        self.lbl_sub.pack(anchor="w", pady=(2, 0))

        # Tabla sinfines
        mid = tk.Frame(self, bg="#1e1e1e")
        mid.pack(fill="both", expand=True, padx=16, pady=10)

        cols = ("nombre", "estado", "progreso")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=14)
        self.tree.heading("nombre", text="Sinfín")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("progreso", text="Progreso")

        self.tree.column("nombre", width=420, anchor="w")
        self.tree.column("estado", width=160, anchor="center")
        self.tree.column("progreso", width=120, anchor="center")

        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("NO_INICIADO", foreground="#ff6b6b")
        self.tree.tag_configure("EN_PROCESO", foreground="#ffd166")
        self.tree.tag_configure("FINALIZADO", foreground="#06d6a0")

        self.tree.bind("<Double-1>", lambda e: self.on_open_sinfin())

        # Botonera
        bot = tk.Frame(self, bg="#1e1e1e")
        bot.pack(fill="x", padx=16, pady=(0, 14))

        ttk.Button(bot, text="➕ Añadir Sinfín",
                   command=self.on_add_sinfin).pack(side="left", padx=6)
        ttk.Button(bot, text="✏ Renombrar", command=self.on_rename_sinfin).pack(
            side="left", padx=6)
        ttk.Button(bot, text="📂 Abrir Sinfín",
                   command=self.on_open_sinfin).pack(side="left", padx=6)

        self.lbl_pedido_pct = tk.Label(
            bot, text="", fg="white", bg="#1e1e1e", font=("Segoe UI", 11, "bold"))
        self.lbl_pedido_pct.pack(side="right", padx=6)

    def refresh(self):
        con = connect()
        p = get_pedido(con, self.pedido_id)
        if not p:
            con.close()
            messagebox.showerror("Error", "Pedido no encontrado.")
            self.destroy()
            return

        pct_pedido = pedido_progress(con, self.pedido_id)
        estado_pedido = estado_from_pct(pct_pedido)

        self.lbl_title.config(
            text=f"{p['numero_pedido']}  —  {p['cliente'] or ''}".strip())
        self.lbl_sub.config(
            text=f"Entrega: {p['fecha_entrega'] or '-'}   |   Estado: {estado_pedido}")
        self.lbl_pedido_pct.config(text=f"Progreso pedido: {pct_pedido:.1f}%")

        for i in self.tree.get_children():
            self.tree.delete(i)

        sinfines = list_sinfines(con, self.pedido_id)
        for s in sinfines:
            pct = sinfin_progress(con, s["id"])
            estado = estado_from_pct(pct)
            self.tree.insert("", "end", iid=str(s["id"]), values=(
                s["nombre"], estado, f"{pct:.1f}%"), tags=(estado,))

        con.close()

        if self.on_updated_callback:
            self.on_updated_callback()

    def on_add_sinfin(self):
        con = connect()
        sinfines = list_sinfines(con, self.pedido_id)
        n = len(sinfines) + 1
        new_id = create_sinfin(con, self.pedido_id, f"Sinfín {n}")
        con.close()
        self.refresh()
        self.tree.selection_set(str(new_id))

    def on_rename_sinfin(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Renombrar", "Selecciona un sinfín.")
            return
        sinfin_id = int(sel[0])

        old_name = self.tree.item(sel[0], "values")[0]
        new_name = tk.simpledialog.askstring(
            "Renombrar", "Nuevo nombre del sinfín:", initialvalue=old_name)
        if not new_name:
            return

        con = connect()
        rename_sinfin(con, sinfin_id, new_name)
        con.close()
        self.refresh()

    def on_open_sinfin(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Abrir sinfín", "Selecciona un sinfín.")
            return
        sinfin_id = int(sel[0])

        from app.sinfin_window import SinfinWindow  # import aquí para evitar ciclos
        SinfinWindow(self, sinfin_id, on_updated_callback=self.refresh)
