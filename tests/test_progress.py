import sqlite3

from utils.progress import pedido_progress, proceso_progress, sinfin_progress


def _connect():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE procesos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            orden INTEGER NOT NULL
        );
        CREATE TABLE tareas (
            id INTEGER PRIMARY KEY,
            proceso_id INTEGER NOT NULL,
            activo INTEGER NOT NULL
        );
        CREATE TABLE estado_tareas (
            tarea_id INTEGER NOT NULL,
            sinfin_id INTEGER NOT NULL,
            completado INTEGER NOT NULL
        );
        CREATE TABLE sinfines (
            id INTEGER PRIMARY KEY,
            pedido_id INTEGER NOT NULL
        );
        """
    )
    return con


def test_progress_sin_tareas_activas():
    con = _connect()
    con.execute(
        "INSERT INTO procesos (id, nombre, orden) VALUES (1, 'Corte', 1)"
    )
    con.execute("INSERT INTO tareas (id, proceso_id, activo) VALUES (1, 1, 0)")
    con.execute("INSERT INTO sinfines (id, pedido_id) VALUES (1, 10)")
    con.commit()

    assert proceso_progress(con, 1) == []
    assert sinfin_progress(con, 1) == 0.0
    assert pedido_progress(con, 10) == 0.0


def test_progress_todas_completadas():
    con = _connect()
    con.executemany(
        "INSERT INTO procesos (id, nombre, orden) VALUES (?, ?, ?)",
        [(1, "Corte", 1), (2, "Soldadura", 2)],
    )
    con.executemany(
        "INSERT INTO tareas (id, proceso_id, activo) VALUES (?, ?, 1)",
        [(1, 1), (2, 1), (3, 2)],
    )
    con.executemany(
        "INSERT INTO sinfines (id, pedido_id) VALUES (?, 10)",
        [(1,), (2,)],
    )
    con.executemany(
        "INSERT INTO estado_tareas (tarea_id, sinfin_id, completado) VALUES (?, ?, 1)",
        [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)],
    )
    con.commit()

    procesos = proceso_progress(con, 1)
    assert [p["pct"] for p in procesos] == [100.0, 100.0]
    assert sinfin_progress(con, 1) == 100.0
    assert pedido_progress(con, 10) == 100.0


def test_progress_mezcla_completadas_e_incompletas():
    con = _connect()
    con.executemany(
        "INSERT INTO procesos (id, nombre, orden) VALUES (?, ?, ?)",
        [(1, "Corte", 1), (2, "Soldadura", 2)],
    )
    con.executemany(
        "INSERT INTO tareas (id, proceso_id, activo) VALUES (?, ?, 1)",
        [(1, 1), (2, 1), (3, 2)],
    )
    con.execute("INSERT INTO sinfines (id, pedido_id) VALUES (1, 10)")
    con.execute(
        "INSERT INTO estado_tareas (tarea_id, sinfin_id, completado) VALUES (1, 1, 1)"
    )
    con.commit()

    procesos = proceso_progress(con, 1)
    assert [p["pct"] for p in procesos] == [50.0, 0.0]
    assert sinfin_progress(con, 1) == 25.0
    assert pedido_progress(con, 10) == 25.0


def test_progress_redondeo_a_una_decimal():
    con = _connect()
    con.execute(
        "INSERT INTO procesos (id, nombre, orden) VALUES (1, 'Corte', 1)"
    )
    con.executemany(
        "INSERT INTO tareas (id, proceso_id, activo) VALUES (?, 1, 1)",
        [(1,), (2,), (3,)],
    )
    con.execute("INSERT INTO sinfines (id, pedido_id) VALUES (1, 10)")
    con.executemany(
        "INSERT INTO estado_tareas (tarea_id, sinfin_id, completado) VALUES (?, 1, 1)",
        [(1,), (2,)],
    )
    con.commit()

    procesos = proceso_progress(con, 1)
    assert procesos[0]["pct"] == 66.7
    assert sinfin_progress(con, 1) == 66.7
    assert pedido_progress(con, 10) == 66.7
