# app/main_tkinter.py
import os
import tkinter as tk
from tkinter import ttk, messagebox

from utils.db import connect, list_pedidos, create_pedido
from utils.progress import sinfin_progress, estado_from_pct

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


def _setup_tree_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # tabla gris claro (principal)
    style.configure(
        "Conrad.Treeview",
        background="#dedede",
        fieldbackground="#dedede",
        foreground="#000000",
        rowheight=28,
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


class SinfinesConradApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SINFINES_CONRAD")
        self.geometry("1100x720")
        self.configure(bg="#1e1e1e")

        _setup_tree_style()

        self._logo_img = None
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        # --- cabecera con logo ---
        header = tk.Frame(self, bg="#1e1e1e")
        header.pack(fill="x", padx=18, pady=(16, 10))

        # izquierda: título
        tk.Label(
            header,
            text="OFICINA TÉCNICA",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 26, "bold"),
        ).pack(side="left", anchor="w")

        # derecha: “PEDIDOS”
        tk.Label(
            header,
            text="PEDIDOS",
            fg="#00bcd4",
            bg="#1e1e1e",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="right", anchor="e")

        # logo centrado (debajo)
        logo_row = tk.Frame(self, bg="#1e1e1e")
        logo_row.pack(fill="x", padx=18, pady=(0, 10))

        self.logo_label = tk.Label(logo_row, bg="#1e1e1e")
        self.logo_label.pack()

        self._load_logo()

        # --- botones ---
        bar = tk.Frame(self, bg="#1e1e1e")
        bar.pack(fill="x", padx=18, pady=(0, 10))

        ttk.Button(bar, text="➕ Nuevo Pedido",
                   command=self.on_new).pack(side="left", padx=6)
        ttk.Button(bar, text="✏️ Editar Pedido",
                   command=self.on_edit).pack(side="left", padx=6)
        ttk.Button(bar, text="📂 Abrir Pedido",
                   command=self.on_open).pack(side="left", padx=6)
        ttk.Button(bar, text="✅ Cerrar Pedido",
                   command=self.on_close).pack(side="left", padx=6)

        ttk.Button(bar, text="🔄 Refrescar", command=self.refresh_table).pack(
            side="right", padx=6)

        # --- tabla ---
        table_frame = tk.Frame(self, bg="#1e1e1e")
        table_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        cols = ("codigo", "cliente", "entrega",
                "estado", "progreso", "sinfines")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            style="Conrad.Treeview",
        )

        self.tree.heading("codigo", text="Código")
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("entrega", text="Entrega")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("progreso", text="Progreso")
        self.tree.heading("sinfines", text="Sinfines")

        self.tree.column("codigo", width=130, anchor="w")
        self.tree.column("cliente", width=320, anchor="w")
        self.tree.column("entrega", width=130, anchor="center")
        self.tree.column("estado", width=150, anchor="center")
        self.tree.column("progreso", width=120, anchor="e")
        self.tree.column("sinfines", width=90, anchor="e")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.on_open())

    def _load_logo(self):
        if Image is None:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "assets", "Logo_conrad.PNG")
        if not os.path.exists(path):
            return
        try:
            img = Image.open(path)
            img = img.resize((420, 150))
            self._logo_img = ImageTk.PhotoImage(img)
            self.logo_label.config(image=self._logo_img)
        except Exception:
            pass

    def _selected_pedido_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def refresh_table(self):
        con = connect()
        pedidos = list_pedidos(con)

        # Si no hay nada: crear pedido ejemplo (solo si DB vacía)
        if not pedidos:
            pid = create_pedido(
                con,
                numero_pedido="P-009250",
                cliente="Ejemplo",
                fecha_pedido=None,
                fecha_entrega=(__import__("datetime").date.today(
                ) + __import__("datetime").timedelta(days=25)).isoformat(),
                observaciones="Pedido de ejemplo creado automáticamente para pruebas."
            )
            # 2 sinfines de ejemplo
            from utils.db import create_sinfin
            create_sinfin(con, pid, "Sinfín 1")
            create_sinfin(con, pid, "Sinfín 2")
            pedidos = list_pedidos(con)
            messagebox.showinfo(
                "Demo", "Base vacía: se ha creado un pedido de ejemplo con 2 sinfines para pruebas.")

        # limpiar tabla
        for i in self.tree.get_children():
            self.tree.delete(i)

        # rellenar (progreso pedido = media de sinfines)
        from utils.db import list_sinfines

        for p in pedidos:
            sinf = list_sinfines(con, p["id"])
            n = len(sinf)
            if n:
                total = 0.0
                for s in sinf:
                    total += sinfin_progress(con, s["id"])
                pct = total / n
            else:
                pct = 0.0

            estado = estado_from_pct(pct)
            entrega = p["fecha_entrega"] or "—"

            self.tree.insert(
                "",
                "end",
                iid=str(p["id"]),
                values=(
                    p["numero_pedido"],
                    p["cliente"] or "",
                    entrega,
                    estado,
                    f"{pct:.1f}%",
                    str(n),
                ),
            )

        con.close()

    # ===== Acciones =====
    def on_new(self):
        from app.main_tkinter import PedidoDialog  # definido abajo
        dlg = PedidoDialog(self, title="Nuevo pedido")
        self.wait_window(dlg)
        if dlg.result:
            con = connect()
            create_pedido(con, **dlg.result)
            con.close()
            self.refresh_table()

    def on_edit(self):
        pid = self._selected_pedido_id()
        if not pid:
            messagebox.showinfo("Editar", "Selecciona un pedido.")
            return

        from utils.db import get_pedido, update_pedido
        con = connect()
        ped = get_pedido(con, pid)
        con.close()
        if not ped:
            return

        from app.main_tkinter import PedidoDialog
        dlg = PedidoDialog(
            self,
            title="Editar pedido",
            initial={
                "numero_pedido": ped["numero_pedido"],
                "cliente": ped["cliente"] or "",
                "fecha_pedido": ped["fecha_pedido"] or "",
                "fecha_entrega": ped["fecha_entrega"] or "",
                "observaciones": ped["observaciones"] or "",
            },
            lock_numero=True,
        )
        self.wait_window(dlg)
        if dlg.result:
            con = connect()
            update_pedido(
                con,
                pid,
                cliente=dlg.result["cliente"],
                fecha_pedido=dlg.result["fecha_pedido"],
                fecha_entrega=dlg.result["fecha_entrega"],
                observaciones=dlg.result["observaciones"],
            )
            con.close()
            self.refresh_table()

    def on_open(self):
        pid = self._selected_pedido_id()
        if not pid:
            messagebox.showinfo("Abrir", "Selecciona un pedido.")
            return
        from app.pedido_window import PedidoWindow
        PedidoWindow(self, pid, on_updated_callback=self.refresh_table)

    def on_close(self):
        pid = self._selected_pedido_id()
        if not pid:
            messagebox.showinfo("Cerrar", "Selecciona un pedido.")
            return
        messagebox.showinfo(
            "Cerrar pedido",
            "Por ahora un pedido se considera 'cerrado' cuando su progreso llega al 100%.\n"
            "Más adelante añadimos campo CERRADO en la base de datos si quieres.",
        )


class PedidoDialog(tk.Toplevel):
    def __init__(self, parent, title="Pedido", initial=None, lock_numero=False):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)
        self.result = None

        initial = initial or {}

        self.v_num = tk.StringVar(value=initial.get("numero_pedido", ""))
        self.v_cli = tk.StringVar(value=initial.get("cliente", ""))
        self.v_fp = tk.StringVar(value=initial.get("fecha_pedido", ""))
        self.v_fe = tk.StringVar(value=initial.get("fecha_entrega", ""))
        self.v_obs = tk.StringVar(value=initial.get("observaciones", ""))

        frm = tk.Frame(self, bg="#1e1e1e")
        frm.pack(padx=14, pady=14)

        def row(r, txt, widget):
            tk.Label(frm, text=txt, fg="#cccccc", bg="#1e1e1e", font=(
                "Segoe UI", 10)).grid(row=r, column=0, sticky="w", pady=6)
            widget.grid(row=r, column=1, sticky="we", pady=6)

        frm.grid_columnconfigure(1, weight=1)

        e_num = ttk.Entry(frm, textvariable=self.v_num, width=35)
        if lock_numero:
            e_num.configure(state="readonly")
        row(0, "Código pedido", e_num)
        row(1, "Cliente", ttk.Entry(frm, textvariable=self.v_cli, width=35))
        row(2, "Fecha pedido (YYYY-MM-DD)",
            ttk.Entry(frm, textvariable=self.v_fp, width=35))
        row(3, "Fecha entrega (YYYY-MM-DD)",
            ttk.Entry(frm, textvariable=self.v_fe, width=35))
        row(4, "Observaciones", ttk.Entry(frm, textvariable=self.v_obs, width=35))

        btns = tk.Frame(self, bg="#1e1e1e")
        btns.pack(fill="x", padx=14, pady=(0, 14))

        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(
            side="right", padx=6)
        ttk.Button(btns, text="Guardar", command=self._ok).pack(
            side="right", padx=6)

        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        self.geometry(
            f"+{parent.winfo_rootx()+120}+{parent.winfo_rooty()+120}")

    def _ok(self):
        num = self.v_num.get().strip()
        if not num:
            messagebox.showerror(
                "Falta dato", "El código de pedido es obligatorio.")
            return
        self.result = {
            "numero_pedido": num,
            "cliente": self.v_cli.get().strip(),
            "fecha_pedido": self.v_fp.get().strip(),
            "fecha_entrega": self.v_fe.get().strip(),
            "observaciones": self.v_obs.get().strip(),
        }
        self.destroy()


if __name__ == "__main__":
    app = SinfinesConradApp()
    app.mainloop()
