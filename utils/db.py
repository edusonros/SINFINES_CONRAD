import os
import sqlite3
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "pedidos.db")


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


def list_pedidos(con: sqlite3.Connection):
    return con.execute(
        """
        SELECT id, numero_pedido, cliente, fecha_pedido, fecha_entrega, observaciones
        FROM pedidos
        ORDER BY fecha_entrega IS NULL, fecha_entrega ASC, id DESC
        """
    ).fetchall()


def create_pedido(con: sqlite3.Connection, numero_pedido: str, cliente: str, fecha_pedido: str, fecha_entrega: str, observaciones: str):
    ts = now_ts()
    con.execute(
        """
        INSERT INTO pedidos (numero_pedido, cliente, fecha_pedido, fecha_entrega, observaciones, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (numero_pedido.strip(), (cliente or "").strip(), fecha_pedido or None,
         fecha_entrega or None, (observaciones or "").strip(), ts, ts),
    )
    con.commit()


def update_pedido(con: sqlite3.Connection, pedido_id: int, cliente: str, fecha_pedido: str, fecha_entrega: str, observaciones: str):
    ts = now_ts()
    con.execute(
        """
        UPDATE pedidos
        SET cliente = ?, fecha_pedido = ?, fecha_entrega = ?, observaciones = ?, updated_at = ?
        WHERE id = ?
        """,
        ((cliente or "").strip(), fecha_pedido or None,
         fecha_entrega or None, (observaciones or "").strip(), ts, pedido_id),
    )
    con.commit()


def create_sinfin(con: sqlite3.Connection, pedido_id: int, nombre: str):
    ts = now_ts()
    con.execute(
        """
        INSERT INTO sinfines (pedido_id, nombre, definicion_json, created_at, updated_at)
        VALUES (?, ?, NULL, ?, ?)
        """,
        (pedido_id, nombre.strip(), ts, ts),
    )
    sinfin_id = con.execute(
        "SELECT last_insert_rowid() AS id").fetchone()["id"]

    # crear estado_tareas para TODAS las tareas activas (por defecto completado=0)
    tareas = con.execute("SELECT id FROM tareas WHERE activo = 1").fetchall()
    for t in tareas:
        con.execute(
            """
            INSERT OR IGNORE INTO estado_tareas (sinfin_id, tarea_id, completado, updated_at)
            VALUES (?, ?, 0, ?)
            """,
            (sinfin_id, t["id"], ts),
        )

    con.commit()
    return sinfin_id


def count_sinfines(con: sqlite3.Connection, pedido_id: int) -> int:
    r = con.execute(
        "SELECT COUNT(*) AS n FROM sinfines WHERE pedido_id = ?", (pedido_id,)).fetchone()
    return int(r["n"])


def pedido_is_closed(con: sqlite3.Connection, pedido_id: int) -> bool:
    # lo consideramos cerrado si progreso = 100% (se calcula fuera), pero dejamos función por si luego quieres
    return False


def get_pedido(con: sqlite3.Connection, pedido_id: int):
    return con.execute(
        """
        SELECT id, numero_pedido, cliente, fecha_pedido, fecha_entrega, observaciones
        FROM pedidos WHERE id = ?
        """,
        (pedido_id,),
    ).fetchone()


def list_sinfines(con: sqlite3.Connection, pedido_id: int):
    return con.execute(
        """
        SELECT id, pedido_id, nombre
        FROM sinfines
        WHERE pedido_id = ?
        ORDER BY id ASC
        """,
        (pedido_id,),
    ).fetchall()


def rename_sinfin(con: sqlite3.Connection, sinfin_id: int, new_name: str):
    ts = now_ts()
    con.execute(
        "UPDATE sinfines SET nombre = ?, updated_at = ? WHERE id = ?",
        (new_name.strip(), ts, sinfin_id),
    )
    con.commit()


def list_tareas_por_proceso(con):
    procs = con.execute(
        "SELECT id, nombre FROM procesos ORDER BY orden, id"
    ).fetchall()

    out = []
    for p in procs:
        tareas = con.execute(
            "SELECT id, descripcion AS nombre FROM tareas WHERE proceso_id=? AND activo=1 ORDER BY id",
            (p["id"],)
        ).fetchall()

        out.append({"id": p["id"], "nombre": p["nombre"], "tareas": tareas})
    return out


def get_estado_tarea(con: sqlite3.Connection, sinfin_id: int, tarea_id: int) -> int:
    r = con.execute(
        "SELECT completado FROM estado_tareas WHERE sinfin_id = ? AND tarea_id = ?",
        (sinfin_id, tarea_id),
    ).fetchone()
    return int(r["completado"]) if r else 0


def set_estado_tarea(con: sqlite3.Connection, sinfin_id: int, tarea_id: int, completado: int):
    ts = now_ts()
    con.execute(
        """
        INSERT INTO estado_tareas (sinfin_id, tarea_id, completado, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(sinfin_id, tarea_id) DO UPDATE SET completado=excluded.completado, updated_at=excluded.updated_at
        """,
        (sinfin_id, tarea_id, int(completado), ts),
    )
    con.commit()


def get_sinfin_definicion(con: sqlite3.Connection, sinfin_id: int) -> dict:
    r = con.execute(
        "SELECT definicion_json FROM sinfines WHERE id = ?",
        (sinfin_id,),
    ).fetchone()
    if not r or not r["definicion_json"]:
        return {}
    try:
        return json.loads(r["definicion_json"])
    except Exception:
        return {}


def set_sinfin_definicion(con: sqlite3.Connection, sinfin_id: int, definicion: dict):
    ts = now_ts()
    con.execute(
        """
        UPDATE sinfines
        SET definicion_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (json.dumps(definicion, ensure_ascii=False), ts, sinfin_id),
    )
    con.commit()
