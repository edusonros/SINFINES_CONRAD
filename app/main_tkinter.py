import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os

from utils.db import connect, list_pedidos, create_pedido, update_pedido, create_sinfin, count_sinfines
from utils.progress import pedido_progress, estado_from_pct

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


class PedidoDialog(tk.Toplevel):
    def __init__(self, parent, title, initial=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None

        self.numero = tk.StringVar(
            value=(initial.get("numero_pedido") if initial else "P-"))
        self.cliente = tk.StringVar(
            value=(initial.get("cliente") if initial else ""))
        self.fecha_pedido = tk.StringVar(
            value=(initial.get("fecha_pedido") if initial else ""))
        self.fecha_entrega = tk.StringVar(
            value=(initial.get("fecha_entrega") if initial else ""))
        self.obs = tk.StringVar(
            value=(initial.get("observaciones") if initial else ""))

        frm = tk.Frame(self, padx=12, pady=12)
        frm.pack(fill="both", expand=True)

        # Numero pedido (solo editable en "Nuevo")
        tk.Label(frm, text="Número pedido (P-XXXXXX):").grid(row=0,
                                                             column=0, sticky="w")
        self.e_num = tk.Entry(frm, textvariable=self.numero, width=25)
        self.e_num.grid(row=0, column=1, pady=4)

        tk.Label(frm, text="Cliente:").grid(row=1, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.cliente,
                 width=45).grid(row=1, column=1, pady=4)

        tk.Label(frm, text="Fecha pedido (YYYY-MM-DD):").grid(row=2,
                                                              column=0, sticky="w")
        tk.Entry(frm, textvariable=self.fecha_pedido, width=25).grid(
            row=2, column=1, pady=4, sticky="w")

        tk.Label(frm, text="Fecha entrega (YYYY-MM-DD):").grid(row=3,
                                                               column=0, sticky="w")
        tk.Entry(frm, textvariable=self.fecha_entrega, width=25).grid(
            row=3, column=1, pady=4, sticky="w")

        tk.Label(frm, text="Observaciones:").grid(row=4, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.obs, width=45).grid(
            row=4, column=1, pady=4)

        btns = tk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, pady=(10, 0), sticky="e")
        tk.Button(btns, text="Cancelar", command=self.destroy).pack(
            side="right", padx=6)
        tk.Button(btns, text="Guardar", command=self._save).pack(side="right")

        self.grab_set()
        self.e_num.focus_set()

    def set_numero_readonly(self):
        self.e_num.configure(state="disabled")

    def _save(self):
        data = {
            "numero_pedido": self.numero.get().strip(),
            "cliente": self.cliente.get().strip(),
            "fecha_pedido": self.fecha_pedido.get().strip(),
            "fecha_entrega": self.fecha_entrega.get().strip(),
            "observaciones": self.obs.get().strip(),
        }
        if not data["numero_pedido"]:
            messagebox.showerror(
                "Error", "El número de pedido es obligatorio.")
            return
        self.result = data
        self.destroy()


class SinfinesConradApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("SINFINES CONRAD – Oficina Técnica")
        self.geometry("1000x650")
        self.configure(bg="#1e1e1e")

        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        # Logo
        logo_path = os.path.join(
            ASSETS_DIR, "Logo_conrad.PNG")  # tu nombre real
        img = Image.open(logo_path)
        img = img.resize((420, 120), Image.LANCZOS)
        self.logo = ImageTk.PhotoImage(img)

        tk.Label(self, image=self.logo, bg="#1e1e1e").pack(pady=18)

        tk.Label(
            self, text="OFICINA TÉCNICA",
            fg="white", bg="#1e1e1e",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=4)

        tk.Label(
            self, text="PEDIDOS",
            fg="#00bcd4", bg="#1e1e1e",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(22, 8))

        # Botones
        button_frame = tk.Frame(self, bg="#1e1e1e")
        button_frame.pack(pady=6)

        ttk.Style().configure("Conrad.TButton", font=("Segoe UI", 10, "bold"))

        ttk.Button(button_frame, text="➕ Nuevo Pedido", style="Conrad.TButton",
                   command=self.on_new).pack(side="left", padx=6)
        ttk.Button(button_frame, text="✏ Editar Pedido", style="Conrad.TButton",
                   command=self.on_edit).pack(side="left", padx=6)
        ttk.Button(button_frame, text="📂 Abrir Pedido", style="Conrad.TButton",
                   command=self.on_open).pack(side="left", padx=6)
        ttk.Button(button_frame, text="✅ Cerrar Pedido", style="Conrad.TButton",
                   command=self.on_close).pack(side="left", padx=6)
        ttk.Button(button_frame, text="🔄 Refrescar", style="Conrad.TButton",
                   command=self.refresh_table).pack(side="left", padx=6)

        # Tabla
        table_frame = tk.Frame(self, bg="#1e1e1e")
        table_frame.pack(fill="both", expand=True, padx=24, pady=18)

        columns = ("pedido", "cliente", "estado",
                   "progreso", "entrega", "sinfines")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=14)

        self.tree.heading("pedido", text="Pedido")
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("progreso", text="Progreso")
        self.tree.heading("entrega", text="Entrega")
        self.tree.heading("sinfines", text="Sinfines")

        self.tree.column("pedido", width=140, anchor="center")
        self.tree.column("cliente", width=260, anchor="w")
        self.tree.column("estado", width=140, anchor="center")
        self.tree.column("progreso", width=120, anchor="center")
        self.tree.column("entrega", width=120, anchor="center")
        self.tree.column("sinfines", width=80, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Tags (colores)
        self.tree.tag_configure(
            "NO_INICIADO", background="#2a2a2a", foreground="#ff6b6b")
        self.tree.tag_configure(
            "EN_PROCESO", background="#2a2a2a", foreground="#ffd166")
        self.tree.tag_configure(
            "FINALIZADO", background="#2a2a2a", foreground="#06d6a0")

        # Doble click = abrir
        self.tree.bind("<Double-1>", lambda e: self.on_open())

    def get_selected_pedido(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item = sel[0]
        return self.tree.item(item, "values"), self.tree.item(item, "tags")

    def refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        con = connect()
        pedidos = list_pedidos(con)

        for p in pedidos:
            pid = p["id"]
            pct = pedido_progress(con, pid)
            estado = estado_from_pct(pct)
            n_sinf = count_sinfines(con, pid)

            values = (
                p["numero_pedido"],
                p["cliente"] or "",
                estado,
                f"{pct:.1f}%",
                p["fecha_entrega"] or "",
                str(n_sinf),
            )
            # usamos el pedido id como iid para recuperar fácil
            self.tree.insert("", "end", iid=str(
                pid), values=values, tags=(estado,))

        con.close()

    def on_new(self):
        dlg = PedidoDialog(self, "Nuevo Pedido")
        self.wait_window(dlg)
        if not dlg.result:
            return

        con = connect()
        try:
            create_pedido(
                con,
                dlg.result["numero_pedido"],
                dlg.result["cliente"],
                dlg.result["fecha_pedido"],
                dlg.result["fecha_entrega"],
                dlg.result["observaciones"],
            )
        except Exception as e:
            con.close()
            messagebox.showerror("Error", f"No se pudo crear el pedido:\n{e}")
            return

        # por defecto creamos 1 sinfín dentro del pedido (luego podrás añadir más)
        pid = con.execute("SELECT id FROM pedidos WHERE numero_pedido = ?",
                          (dlg.result["numero_pedido"],)).fetchone()["id"]
        create_sinfin(con, pid, "Sinfín 1")
        con.close()

        self.refresh_table()

    def on_edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Editar", "Selecciona un pedido en la tabla.")
            return
        pedido_id = int(sel[0])

        con = connect()
        p = con.execute(
            "SELECT numero_pedido, cliente, fecha_pedido, fecha_entrega, observaciones FROM pedidos WHERE id = ?",
            (pedido_id,),
        ).fetchone()
        con.close()

        initial = dict(p)
        dlg = PedidoDialog(
            self, f"Editar Pedido {p['numero_pedido']}", initial=initial)
        dlg.set_numero_readonly()
        self.wait_window(dlg)
        if not dlg.result:
            return

        con = connect()
        update_pedido(
            con,
            pedido_id,
            dlg.result["cliente"],
            dlg.result["fecha_pedido"],
            dlg.result["fecha_entrega"],
            dlg.result["observaciones"],
        )
        con.close()
        self.refresh_table()

    def on_open(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Abrir", "Selecciona un pedido.")
            return
        pedido_id = int(sel[0])

        from app.pedido_window import PedidoWindow
        PedidoWindow(self, pedido_id, on_updated_callback=self.refresh_table)

    def on_close(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Cerrar", "Selecciona un pedido.")
            return
        pedido_id = int(sel[0])

        con = connect()
        pct = pedido_progress(con, pedido_id)
        con.close()

        if pct < 100.0:
            messagebox.showwarning(
                "Cerrar", f"No se puede cerrar: el pedido está al {pct:.1f}%.\nDebe estar al 100%.")
            return

        messagebox.showinfo(
            "Cerrar", "Pedido al 100%: lo consideramos cerrado automáticamente.\n(Después añadimos 'Archivar').")


if __name__ == "__main__":
    app = SinfinesConradApp()
    app.mainloop()
