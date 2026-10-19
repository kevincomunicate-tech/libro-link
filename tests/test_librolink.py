import tempfile
import unittest
from datetime import date
from pathlib import Path
from models.usuario import UsuarioRegular, UsuarioPremium
from models.libro import Libro
from services.prestamo_service import PrestamoService
from services.errores import ReglaNegocioError, PersistenciaError
from persistence.json_repository import JsonRepository


class LibroLinkTests(unittest.TestCase):
    def setUp(self):
        self.u = UsuarioRegular("U1", "Ana")
        self.l = Libro("L1", "El libro", "Autor", "Novela")
        self.s = PrestamoService([self.u], [self.l])

    def test_prestamo_valido_y_estado_libro(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.assertEqual(p.fecha_vencimiento, date(2026, 1, 15))
        self.assertEqual(self.l.estado, "PRESTADO")

    def test_no_prestar_libro_ya_prestado(self):
        self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        with self.assertRaises(ReglaNegocioError): self.s.crear_prestamo("U1", "L1", date(2026, 1, 2))

    def test_usuario_inexistente(self):
        with self.assertRaises(ReglaNegocioError): self.s.crear_prestamo("X", "L1", date(2026, 1, 1))

    def test_devolucion_a_tiempo_puntaje(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.s.devolver(p.id, date(2026, 1, 10))
        self.assertEqual(str(p.multa), "0.00")
        self.assertEqual(self.u.puntaje_confiabilidad, 52)
        self.assertEqual(self.l.estado, "DISPONIBLE")

    def test_devolucion_tarde_multa_y_puntaje(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.s.devolver(p.id, date(2026, 1, 17))
        self.assertEqual(str(p.multa), "2.00")
        self.assertEqual(self.u.puntaje_confiabilidad, 45)

    def test_no_devolver_dos_veces(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.s.devolver(p.id, date(2026, 1, 2))
        with self.assertRaises(ReglaNegocioError): self.s.devolver(p.id, date(2026, 1, 3))

    def test_usuario_premium_tiene_reglas_distintas(self):
        u = UsuarioPremium("U2", "Beto")
        self.assertEqual(u.limite_prestamos(), 5)
        self.assertEqual(u.dias_prestamo(), 21)

    def test_json_guardar_y_cargar(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = JsonRepository(Path(temp) / "usuarios.json", UsuarioRegular.from_dict)
            repo.guardar([self.u])
            cargados = repo.cargar()
            self.assertEqual(cargados[0].nombre, "Ana")

    def test_json_danado_falla_sin_borrarse(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / "datos.json"
            ruta.write_text("{ roto", encoding="utf-8")
            with self.assertRaises(PersistenciaError): JsonRepository(ruta, dict).cargar()
            self.assertTrue(ruta.exists())

if __name__ == "__main__":
    unittest.main()
