import sqlite3
import unittest

from app.init_db import init_schema
from utils.db import (
    create_pedido,
    create_sinfin,
    get_sinfin_definicion,
    set_sinfin_definicion,
)


class SinfinDefinicionTest(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON;")
        init_schema(self.con)

    def tearDown(self):
        self.con.close()

    def test_set_and_get_sinfin_definicion(self):
        pedido_id = create_pedido(
            self.con,
            numero_pedido="PED-001",
            cliente="Cliente",
            fecha_pedido="2024-01-01",
            fecha_entrega=None,
            observaciones="",
        )
        sinfin_id = create_sinfin(self.con, pedido_id, "Sinfín 1")

        definicion = {
            "longitud_entre_testeros": 1200,
            "paso_espira": 150,
            "diametro_tubo": 50,
            "espesor_tubo": 3,
            "diametro_espira": 200,
            "espesor_chapa": 4,
        }

        set_sinfin_definicion(self.con, sinfin_id, definicion)

        self.assertEqual(get_sinfin_definicion(self.con, sinfin_id), definicion)


if __name__ == "__main__":
    unittest.main()
