import sqlite3


def proceso_progress(con: sqlite3.Connection, sinfin_id: int) -> list[dict]:
    """
    Devuelve lista por proceso:
    [{proceso: 'Material', total: 4, ok: 2, pct: 50.0}, ...]
    """
    rows = con.execute(
        """
        SELECT p.nombre AS proceso,
               COUNT(t.id) AS total,
               SUM(CASE WHEN et.completado = 1 THEN 1 ELSE 0 END) AS ok
        FROM procesos p
        JOIN tareas t ON t.proceso_id = p.id AND t.activo = 1
        LEFT JOIN estado_tareas et ON et.tarea_id = t.id AND et.sinfin_id = ?
        GROUP BY p.id
        ORDER BY p.orden
        """,
        (sinfin_id,),
    ).fetchall()

    out = []
    for r in rows:
        total = r["total"] or 0
        ok = r["ok"] or 0
        pct = (ok / total * 100.0) if total else 0.0
        out.append(
            {"proceso": r["proceso"], "total": total, "ok": ok, "pct": round(pct, 1)})
    return out


def sinfin_progress(con: sqlite3.Connection, sinfin_id: int) -> float:
    procs = proceso_progress(con, sinfin_id)
    if not procs:
        return 0.0
    return round(sum(p["pct"] for p in procs) / len(procs), 1)


def pedido_progress(con: sqlite3.Connection, pedido_id: int) -> float:
    sinfines = con.execute(
        "SELECT id FROM sinfines WHERE pedido_id = ?", (pedido_id,)).fetchall()
    if not sinfines:
        return 0.0
    vals = [sinfin_progress(con, s["id"]) for s in sinfines]
    return round(sum(vals) / len(vals), 1)


def estado_from_pct(pct: float) -> str:
    if pct <= 0.0:
        return "NO_INICIADO"
    if pct >= 100.0:
        return "FINALIZADO"
    return "EN_PROCESO"
