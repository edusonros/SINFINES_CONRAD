import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "pedidos.db")

PROCESOS = [
    (1, "Material"),
    (2, "Mecanización"),
    (3, "Calderería"),
    (4, "Soldadura"),
    (5, "Pintura"),
    (6, "Pruebas"),
    (7, "Mediciones"),
    (8, "Manual CE"),
]

# Tareas FIJAS por proceso (ajústalas cuando quieras; el sistema ya queda montado)
TAREAS = [
    # Material
    ("Material", "Tubo eje comprado/recibido"),
    ("Material", "Camisa/tubo o chapa artesa comprada/recibida"),
    ("Material", "Chapa testeros comprada/recibida"),
    ("Material", "Tornillería/elementos auxiliares recibidos"),

    # Mecanizacion
    ("Mecanización", "Eje mecanizado"),
    ("Mecanización", "Mangones mecanizados"),
    ("Mecanización", "Alojamiento rodamientos verificado"),

    # Caldereria
    ("Calderería", "Espiras cortadas"),
    ("Calderería", "Camisa preparada (tubo/artesa)"),
    ("Calderería", "Testeros y bridas cortados/taladrados"),

    # Soldadura
    ("Soldadura", "Soldadura espiras-eje"),
    ("Soldadura", "Soldadura testeros/camisa"),
    ("Soldadura", "Repaso y limpieza cordones"),

    # Pintura
    ("Pintura", "Preparación superficie"),
    ("Pintura", "Imprimación"),
    ("Pintura", "Acabado"),

    # Pruebas
    ("Pruebas", "Montaje provisional y giro"),
    ("Pruebas", "Prueba sin rozamientos/anomalías"),

    # Mediciones
    ("Mediciones", "Verificación cotas principales"),
    ("Mediciones", "Registro mediciones"),

    # Manual CE
    ("Manual CE", "Listado materiales (BOM)"),
    ("Manual CE", "Planos PDF emitidos"),
    ("Manual CE", "Declaración conformidad"),
    ("Manual CE", "Manual usuario/instalación"),
]


def connect():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def init_schema(con: sqlite3.Connection):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_pedido TEXT UNIQUE NOT NULL,
            cliente TEXT,
            fecha_pedido TEXT,
            fecha_entrega TEXT,
            observaciones TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sinfines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,                 -- ej: "Sinfín 1", "Sinfín A", "Tolva", etc.
            definicion_json TEXT,                 -- guardaremos aquí parámetros (material, diametros...) en JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS procesos (
            id INTEGER PRIMARY KEY,
            orden INTEGER NOT NULL,
            nombre TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            UNIQUE(proceso_id, descripcion),
            FOREIGN KEY (proceso_id) REFERENCES procesos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS estado_tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sinfin_id INTEGER NOT NULL,
            tarea_id INTEGER NOT NULL,
            completado INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(sinfin_id, tarea_id),
            FOREIGN KEY (sinfin_id) REFERENCES sinfines(id) ON DELETE CASCADE,
            FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE
        );

        -- Proveedores (para pedir precios)
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            activo INTEGER NOT NULL DEFAULT 1
        );

        -- Solicitudes de cotización (por pedido/sinfín)
        CREATE TABLE IF NOT EXISTS solicitudes_cotizacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            sinfin_id INTEGER,
            proveedor_id INTEGER NOT NULL,
            asunto TEXT NOT NULL,
            cuerpo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'BORRADOR',  -- BORRADOR / ENVIADO / RESPONDIDO
            created_at TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
            FOREIGN KEY (sinfin_id) REFERENCES sinfines(id) ON DELETE SET NULL,
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE CASCADE
        );

        -- Items solicitados (líneas de material)
        CREATE TABLE IF NOT EXISTS solicitud_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitud_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            cantidad REAL,
            unidad TEXT,
            referencia TEXT,
            FOREIGN KEY (solicitud_id) REFERENCES solicitudes_cotizacion(id) ON DELETE CASCADE
        );
        """
    )
    con.commit()


def normalize_texts(con: sqlite3.Connection):
    proceso_updates = {
        "Mecanizacion": "Mecanización",
        "Caldereria": "Calderería",
    }

    tarea_updates = {
        "Tornilleria/elementos auxiliares recibidos": "Tornillería/elementos auxiliares recibidos",
        "Preparacion superficie": "Preparación superficie",
        "Imprimacion": "Imprimación",
        "Prueba sin rozamientos/anomalias": "Prueba sin rozamientos/anomalías",
        "Verificacion cotas principales": "Verificación cotas principales",
        "Declaracion conformidad": "Declaración conformidad",
        "Manual usuario/instalacion": "Manual usuario/instalación",
    }

    for old_name, new_name in proceso_updates.items():
        con.execute(
            "UPDATE procesos SET nombre = ? WHERE nombre = ?",
            (new_name, old_name),
        )

    for old_desc, new_desc in tarea_updates.items():
        con.execute(
            "UPDATE tareas SET descripcion = ? WHERE descripcion = ?",
            (new_desc, old_desc),
        )

    con.commit()


def seed_procesos_y_tareas(con: sqlite3.Connection):
    now = datetime.now().isoformat(timespec="seconds")

    # Procesos
    for orden, nombre in PROCESOS:
        con.execute(
            "INSERT OR IGNORE INTO procesos(id, orden, nombre) VALUES(?, ?, ?)",
            (orden, orden, nombre),
        )

    # Mapa nombre->id
    proc_map = {r["nombre"]: r["id"]
                for r in con.execute("SELECT id, nombre FROM procesos")}

    # Tareas
    for proc_name, desc in TAREAS:
        pid = proc_map[proc_name]
        con.execute(
            "INSERT OR IGNORE INTO tareas(proceso_id, descripcion, activo) VALUES(?, ?, 1)",
            (pid, desc),
        )

    con.commit()
    print(f"[OK] Procesos y tareas sembrados. ({now})")


def main():
    con = connect()
    init_schema(con)
    normalize_texts(con)
    seed_procesos_y_tareas(con)
    con.close()
    print(f"[OK] DB lista en: {DB_PATH}")


if __name__ == "__main__":
    main()
