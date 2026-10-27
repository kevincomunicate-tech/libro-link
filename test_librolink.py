import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from models.libro import Libro
from models.prestamo import MULTA_DIARIA, Prestamo
from models.usuario import Usuario, UsuarioPremium, UsuarioRegular
from persistence.csv_exporter import exportar_csv
from persistence.json_repository import JsonRepository
from services.auth_service import AuthService, registro_admin_desde_dict
from services.errores import (
    EntidadNoEncontradaError,
    PersistenciaError,
    ReglaNegocioError,
    ValidacionError,
)
from services.libro_service import LibroService
from services.prestamo_service import PrestamoService
from services.reporte_service import ReporteService
from services.usuario_service import UsuarioService
from validators.validaciones import (
    validar_email,
    validar_isbn,
    validar_nombre,
    validar_stock,
)


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
        with self.assertRaises(ReglaNegocioError):
            self.s.crear_prestamo("U1", "L1", date(2026, 1, 2))

    def test_usuario_inexistente(self):
        with self.assertRaises(ReglaNegocioError):
            self.s.crear_prestamo("X", "L1", date(2026, 1, 1))

    def test_devolucion_a_tiempo_puntaje(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.s.devolver(p.id, date(2026, 1, 10))
        self.assertEqual(p.multa, 0)
        self.assertEqual(self.u.puntaje_confiabilidad, 52)
        self.assertEqual(self.l.estado, "DISPONIBLE")

    def test_devolucion_tarde_multa_y_puntaje(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.s.devolver(p.id, date(2026, 1, 17))
        self.assertEqual(p.dias_retraso(), 2)
        self.assertEqual(p.multa, 4000)
        self.assertEqual(self.u.puntaje_confiabilidad, 45)

    def test_no_devolver_dos_veces(self):
        p = self.s.crear_prestamo("U1", "L1", date(2026, 1, 1))
        self.s.devolver(p.id, date(2026, 1, 2))
        with self.assertRaises(ReglaNegocioError):
            self.s.devolver(p.id, date(2026, 1, 3))

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
            with self.assertRaises(PersistenciaError):
                JsonRepository(ruta, dict).cargar()
            self.assertTrue(ruta.exists())


class MultasTests(unittest.TestCase):
    def setUp(self):
        self.usuarios = [UsuarioRegular("U001", "Ana", "ana@mail.com")]
        self.libros = [
            Libro("L001", "Uno", "Autor A", "9780306406157", 1),
            Libro("L002", "Dos", "Autor B", "9780306406164", 2),
        ]
        self.prestamos = []
        self.s = PrestamoService(self.usuarios, self.libros, self.prestamos)

    def test_multa_es_dos_mil_por_dia(self):
        self.assertEqual(MULTA_DIARIA, 2000)
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.s.devolver(p.id, date(2026, 3, 20))
        self.assertEqual(p.dias_retraso(), 5)
        self.assertEqual(p.multa, 10000)

    def test_devolver_el_dia_de_vencimiento_no_genera_multa(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.s.devolver(p.id, date(2026, 3, 15))
        self.assertEqual(p.multa, 0)

    def test_multa_crece_cada_dia_mientras_no_se_devuelve(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.assertEqual(p.multa_acumulada(date(2026, 3, 15)), 0)
        self.assertEqual(p.multa_acumulada(date(2026, 3, 16)), 2000)
        self.assertEqual(p.multa_acumulada(date(2026, 3, 26)), 22000)
        self.assertTrue(p.esta_atrasado(date(2026, 3, 16)))

    def test_multa_se_congela_al_devolver(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.s.devolver(p.id, date(2026, 3, 17))
        self.assertEqual(p.multa_acumulada(date(2026, 6, 1)), 4000)

    def test_usuario_con_multa_pendiente_no_puede_pedir_prestado(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.s.devolver(p.id, date(2026, 3, 17))
        with self.assertRaises(ReglaNegocioError):
            self.s.crear_prestamo("U001", "L002", date(2026, 3, 18))

    def test_pagar_multa_libera_al_usuario(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.s.devolver(p.id, date(2026, 3, 17))
        self.s.pagar_multa(p.id, date(2026, 3, 18))
        self.assertTrue(p.multa_pagada)
        self.assertEqual(self.s.deuda_usuario("U001", date(2026, 3, 19)), 0)
        nuevo = self.s.crear_prestamo("U001", "L002", date(2026, 3, 19))
        self.assertEqual(nuevo.id_prestamo, "P002")

    def test_no_se_paga_multa_de_libro_sin_devolver(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        with self.assertRaises(ReglaNegocioError):
            self.s.pagar_multa(p.id, date(2026, 3, 20))

    def test_no_se_paga_dos_veces_ni_sin_multa(self):
        a_tiempo = self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        self.s.devolver(a_tiempo.id, date(2026, 3, 2))
        with self.assertRaises(ReglaNegocioError):
            self.s.pagar_multa(a_tiempo.id)
        tarde = self.s.crear_prestamo("U001", "L002", date(2026, 3, 3))
        self.s.devolver(tarde.id, date(2026, 3, 30))
        self.s.pagar_multa(tarde.id, date(2026, 3, 30))
        with self.assertRaises(ReglaNegocioError):
            self.s.pagar_multa(tarde.id)

    def test_usuario_atrasado_no_puede_pedir_otro_libro(self):
        self.s.crear_prestamo("U001", "L001", date(2026, 3, 1))
        with self.assertRaises(ReglaNegocioError):
            self.s.crear_prestamo("U001", "L002", date(2026, 3, 20))

    def test_limite_de_prestamos_por_rol(self):
        libros = [Libro(f"L{n}", f"Libro {n}", "Autor", "", 1) for n in range(1, 8)]
        regular = UsuarioRegular("U1", "Ana")
        premium = UsuarioPremium("U2", "Beto")
        servicio = PrestamoService([regular, premium], libros)
        for n in range(1, 4):
            servicio.crear_prestamo("U1", f"L{n}", date(2026, 1, 1))
        with self.assertRaises(ReglaNegocioError):
            servicio.crear_prestamo("U1", "L4", date(2026, 1, 1))
        for n in range(4, 8):
            servicio.crear_prestamo("U2", f"L{n}", date(2026, 1, 1))
        libros_extra = [Libro(f"M{n}", f"Extra {n}", "Autor", "", 1) for n in range(1, 3)]
        libros.extend(libros_extra)
        servicio.crear_prestamo("U2", "M1", date(2026, 1, 1))
        with self.assertRaises(ReglaNegocioError):
            servicio.crear_prestamo("U2", "M2", date(2026, 1, 1))

    def test_no_se_presta_el_mismo_libro_dos_veces_al_mismo_usuario(self):
        self.s.crear_prestamo("U001", "L002", date(2026, 3, 1))
        with self.assertRaises(ReglaNegocioError):
            self.s.crear_prestamo("U001", "L002", date(2026, 3, 2))

    def test_libro_con_varios_ejemplares_se_presta_a_varios_usuarios(self):
        self.usuarios.append(UsuarioRegular("U002", "Beto", "beto@mail.com"))
        self.s.crear_prestamo("U001", "L002", date(2026, 3, 1))
        self.assertEqual(self.libros[1].estado, "DISPONIBLE")
        self.s.crear_prestamo("U002", "L002", date(2026, 3, 1))
        self.assertEqual(self.libros[1].estado, "PRESTADO")

    def test_puntaje_tiene_limites(self):
        usuario = UsuarioRegular("U9", "Zoe", puntaje_confiabilidad=99)
        usuario.registrar_devolucion_a_tiempo()
        self.assertEqual(usuario.puntaje_confiabilidad, 100)
        usuario.registrar_devolucion_a_tiempo()
        self.assertEqual(usuario.puntaje_confiabilidad, 100)
        otro = UsuarioRegular("U8", "Leo", puntaje_confiabilidad=3)
        otro.registrar_devolucion_tardia()
        self.assertEqual(otro.puntaje_confiabilidad, 0)

    def test_fecha_de_devolucion_anterior_al_prestamo_se_rechaza(self):
        p = self.s.crear_prestamo("U001", "L001", date(2026, 3, 10))
        with self.assertRaises(ReglaNegocioError):
            self.s.devolver(p.id, date(2026, 3, 1))


class UsuarioServiceTests(unittest.TestCase):
    def setUp(self):
        self.usuarios = []
        self.prestamos = []
        self.servicio = UsuarioService(self.usuarios, self.prestamos)

    def test_registrar_asigna_id_y_normaliza_correo(self):
        usuario = self.servicio.registrar("  Ana   Pérez ", "ANA@Mail.COM", "regular")
        self.assertEqual(usuario.id_usuario, "U001")
        self.assertEqual(usuario.nombre, "Ana Pérez")
        self.assertEqual(usuario.email, "ana@mail.com")
        self.assertIn(usuario, self.servicio.listar())

    def test_correo_duplicado_se_rechaza(self):
        self.servicio.registrar("Ana", "ana@mail.com", "regular")
        with self.assertRaises(ReglaNegocioError):
            self.servicio.registrar("Otra Ana", "ANA@mail.com", "premium")

    def test_campos_obligatorios_y_formatos(self):
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("", "a@b.com", "regular")
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("Ana", "sin-arroba", "regular")
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("Ana", "a@b.com", "administrador")
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("Ana123", "a@b.com", "regular")
        self.assertEqual(self.usuarios, [])

    def test_buscar_por_nombre_o_correo_sin_tildes_ni_mayusculas(self):
        self.servicio.registrar("María López", "maria@mail.com", "regular")
        self.servicio.registrar("Pedro Gómez", "pedro@correo.org", "premium")
        self.assertEqual(len(self.servicio.buscar("maria")), 1)
        self.assertEqual(len(self.servicio.buscar("GOMEZ")), 1)
        self.assertEqual(len(self.servicio.buscar("correo.org")), 1)
        self.assertEqual(self.servicio.buscar("zzz"), [])

    def test_actualizar_cambia_datos_y_rol(self):
        usuario = self.servicio.registrar("Ana", "ana@mail.com", "regular")
        usuario.puntaje_confiabilidad = 70
        actualizado = self.servicio.actualizar(
            "U001", nombre="Ana María", email="nueva@mail.com", rol="premium"
        )
        self.assertEqual(actualizado.rol, "premium")
        self.assertEqual(actualizado.limite_prestamos(), 5)
        self.assertEqual(actualizado.puntaje_confiabilidad, 70)
        self.assertEqual(self.servicio.obtener("u001").nombre, "Ana María")

    def test_actualizar_no_permite_correo_de_otro_usuario(self):
        self.servicio.registrar("Ana", "ana@mail.com", "regular")
        self.servicio.registrar("Beto", "beto@mail.com", "regular")
        with self.assertRaises(ReglaNegocioError):
            self.servicio.actualizar("U002", email="ana@mail.com")
        self.servicio.actualizar("U002", email="beto@mail.com")

    def test_obtener_inexistente(self):
        with self.assertRaises(EntidadNoEncontradaError):
            self.servicio.obtener("U999")

    def test_eliminar_y_no_reutilizar_ids(self):
        self.servicio.registrar("Ana", "ana@mail.com", "regular")
        self.servicio.registrar("Beto", "beto@mail.com", "regular")
        self.servicio.eliminar("U002")
        nuevo = self.servicio.registrar("Carla", "carla@mail.com", "regular")
        self.assertEqual(nuevo.id_usuario, "U002")
        libro = Libro("L001", "Uno", "A", "", 1)
        prestamos = PrestamoService(self.usuarios, [libro], self.prestamos)
        p = prestamos.crear_prestamo("U002", "L001", date(2026, 1, 1))
        prestamos.devolver(p.id, date(2026, 1, 2))
        self.servicio.eliminar("U002")
        otra = self.servicio.registrar("Diana", "diana@mail.com", "regular")
        self.assertEqual(otra.id_usuario, "U003")

    def test_no_eliminar_usuario_con_prestamo_activo_o_multa(self):
        self.servicio.registrar("Ana", "ana@mail.com", "regular")
        libro = Libro("L001", "Uno", "A", "", 1)
        prestamos = PrestamoService(self.usuarios, [libro], self.prestamos)
        p = prestamos.crear_prestamo("U001", "L001", date(2026, 1, 1))
        with self.assertRaises(ReglaNegocioError):
            self.servicio.eliminar("U001", hoy=date(2026, 1, 2))
        prestamos.devolver(p.id, date(2026, 1, 20))
        with self.assertRaises(ReglaNegocioError):
            self.servicio.eliminar("U001", hoy=date(2026, 1, 21))
        prestamos.pagar_multa(p.id, date(2026, 1, 21))
        self.servicio.eliminar("U001", hoy=date(2026, 1, 22))
        self.assertEqual(self.usuarios, [])


class LibroServiceTests(unittest.TestCase):
    def setUp(self):
        self.libros = []
        self.prestamos = []
        self.servicio = LibroService(self.libros, self.prestamos)

    def test_registrar_libro_completo(self):
        libro = self.servicio.registrar("Cien años de soledad", "Gabriel García Márquez", "978-0-06-088328-7", "3")
        self.assertEqual(libro.id_libro, "L001")
        self.assertEqual(libro.isbn, "9780060883287")
        self.assertEqual(libro.stock_total, 3)
        self.assertEqual(libro.stock_disponible, 3)

    def test_isbn_duplicado_y_formatos_invalidos(self):
        self.servicio.registrar("Uno", "Autor", "9780306406157", 1)
        with self.assertRaises(ReglaNegocioError):
            self.servicio.registrar("Otro", "Autor", "978-0-306-40615-7", 1)
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("Otro", "Autor", "12345", 1)
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("Otro", "Autor", "9780306406164", "cero")
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("Otro", "Autor", "9780306406164", 0)
        with self.assertRaises(ValidacionError):
            self.servicio.registrar("", "Autor", "9780306406164", 1)
        self.assertEqual(len(self.libros), 1)

    def test_buscar_por_titulo_autor_o_isbn(self):
        self.servicio.registrar("El Principito", "Antoine de Saint-Exupéry", "9780156012195", 2)
        self.servicio.registrar("Rayuela", "Julio Cortázar", "9788437604572", 1)
        self.assertEqual(len(self.servicio.buscar("principito")), 1)
        self.assertEqual(len(self.servicio.buscar("cortazar")), 1)
        self.assertEqual(len(self.servicio.buscar("978-84")), 1)
        self.assertEqual(self.servicio.buscar("inexistente"), [])

    def test_listar_solo_disponibles(self):
        self.servicio.registrar("Uno", "Autor", "9780306406157", 1)
        self.servicio.registrar("Dos", "Autor", "9780306406164", 1)
        self.libros[0].prestar()
        disponibles = self.servicio.listar(solo_disponibles=True)
        self.assertEqual([l.titulo for l in disponibles], ["Dos"])

    def test_actualizar_respeta_ejemplares_prestados(self):
        self.servicio.registrar("Uno", "Autor", "9780306406157", 3)
        self.libros[0].prestar()
        self.libros[0].prestar()
        with self.assertRaises(ReglaNegocioError):
            self.servicio.actualizar("L001", stock=1)
        libro = self.servicio.actualizar("L001", titulo="Uno revisado", stock=5)
        self.assertEqual(libro.stock_total, 5)
        self.assertEqual(libro.stock_disponible, 3)
        self.assertEqual(libro.titulo, "Uno revisado")

    def test_actualizar_isbn_no_choca_consigo_mismo_pero_si_con_otro(self):
        self.servicio.registrar("Uno", "Autor", "9780306406157", 1)
        self.servicio.registrar("Dos", "Autor", "9780306406164", 1)
        self.servicio.actualizar("L001", isbn="9780306406157")
        with self.assertRaises(ReglaNegocioError):
            self.servicio.actualizar("L001", isbn="9780306406164")

    def test_eliminar_libro_prestado_se_rechaza(self):
        self.servicio.registrar("Uno", "Autor", "9780306406157", 1)
        usuarios = [UsuarioRegular("U1", "Ana")]
        prestamos = PrestamoService(usuarios, self.libros, self.prestamos)
        p = prestamos.crear_prestamo("U1", "L001", date(2026, 1, 1))
        with self.assertRaises(ReglaNegocioError):
            self.servicio.eliminar("L001")
        prestamos.devolver(p.id, date(2026, 1, 2))
        self.servicio.eliminar("L001")
        self.assertEqual(self.libros, [])

    def test_libro_de_formato_antiguo_se_carga(self):
        libro = Libro.from_dict({"id_libro": "L1", "titulo": "T", "autor": "A", "disponible": False})
        self.assertEqual(libro.stock_total, 1)
        self.assertEqual(libro.stock_disponible, 0)


class ValidacionesTests(unittest.TestCase):
    def test_validar_email(self):
        self.assertEqual(validar_email(" Ana@Mail.com "), "ana@mail.com")
        for invalido in ("", "ana", "ana@", "@mail.com", "ana@mail", "a b@mail.com", "ana@mail..com"):
            with self.assertRaises(ValidacionError):
                validar_email(invalido)

    def test_validar_isbn(self):
        self.assertEqual(validar_isbn("0-306-40615-2"), "0306406152")
        self.assertEqual(validar_isbn("080442957x"), "080442957X")
        self.assertEqual(validar_isbn("978 0 306 40615 7"), "9780306406157")
        for invalido in ("", "123", "97803064061AB", "12345678901234"):
            with self.assertRaises(ValidacionError):
                validar_isbn(invalido)

    def test_validar_nombre_y_stock(self):
        self.assertEqual(validar_nombre("María-José O'Brien"), "María-José O'Brien")
        for invalido in ("", "A", "Ana 2", "!!!", "x" * 81):
            with self.assertRaises(ValidacionError):
                validar_nombre(invalido)
        self.assertEqual(validar_stock("4"), 4)
        for invalido in ("", "-1", "0", "2.5", "abc", "100000"):
            with self.assertRaises(ValidacionError):
                validar_stock(invalido)


class PersistenciaTests(unittest.TestCase):
    def test_archivo_inexistente_devuelve_lista_vacia(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = JsonRepository(Path(temp) / "no_existe.json", dict)
            self.assertEqual(repo.cargar(), [])

    def test_ciclo_completo_usuarios_libros_prestamos(self):
        with tempfile.TemporaryDirectory() as temp:
            carpeta = Path(temp)
            usuarios = [UsuarioPremium("U001", "Ana", "ana@mail.com", 64)]
            libros = [Libro("L001", "Uno", "Autor", "9780306406157", 2)]
            servicio = PrestamoService(usuarios, libros)
            p = servicio.crear_prestamo("U001", "L001", date(2026, 5, 1))
            servicio.devolver(p.id, date(2026, 5, 30))
            JsonRepository(carpeta / "u.json", Usuario.from_dict).guardar(usuarios)
            JsonRepository(carpeta / "l.json", Libro.from_dict).guardar(libros)
            JsonRepository(carpeta / "p.json", Prestamo.from_dict).guardar(servicio.prestamos)
            u2 = JsonRepository(carpeta / "u.json", Usuario.from_dict).cargar()[0]
            l2 = JsonRepository(carpeta / "l.json", Libro.from_dict).cargar()[0]
            p2 = JsonRepository(carpeta / "p.json", Prestamo.from_dict).cargar()[0]
            self.assertIsInstance(u2, UsuarioPremium)
            self.assertEqual(u2.puntaje_confiabilidad, usuarios[0].puntaje_confiabilidad)
            self.assertEqual(l2.stock_disponible, 2)
            self.assertEqual(p2.fecha_devolucion, date(2026, 5, 30))
            self.assertEqual(p2.dias_retraso(), 8)
            self.assertEqual(p2.multa, 16000)
            self.assertFalse(p2.multa_pagada)

    def test_registros_invalidos_se_reportan_sin_borrar(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / "libros.json"
            ruta.write_text('[{"titulo": "sin id"}]', encoding="utf-8")
            with self.assertRaises(PersistenciaError):
                JsonRepository(ruta, Libro.from_dict).cargar()
            self.assertTrue(ruta.exists())
            ruta.write_text('{"no": "es lista"}', encoding="utf-8")
            with self.assertRaises(PersistenciaError):
                JsonRepository(ruta, dict).cargar()

    def test_respaldar_conserva_el_archivo_danado(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / "datos.json"
            ruta.write_text("basura", encoding="utf-8")
            repo = JsonRepository(ruta, dict)
            destino = repo.respaldar()
            self.assertFalse(ruta.exists())
            self.assertEqual(destino.read_text(encoding="utf-8"), "basura")
            repo.guardar([{"ok": True}])
            self.assertEqual(repo.cargar(), [{"ok": True}])

    def test_guardado_no_deja_archivos_temporales(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = JsonRepository(Path(temp) / "datos.json", dict)
            repo.guardar([{"a": 1}])
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ["datos.json"])

    def test_exportar_csv_con_tildes_y_proteccion_de_formulas(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = exportar_csv(
                Path(temp) / "reporte.csv",
                ["Nombre", "Multa (COP)"],
                [["José Ñandú", 4000], ["=SUMA(A1)", 2000], ["Sin dato", None]],
            )
            with open(ruta, newline="", encoding="utf-8-sig") as archivo:
                filas = list(csv.reader(archivo))
            self.assertEqual(filas[0], ["Nombre", "Multa (COP)"])
            self.assertEqual(filas[1], ["José Ñandú", "4000"])
            self.assertEqual(filas[2][0], "'=SUMA(A1)")
            self.assertEqual(filas[3], ["Sin dato", ""])


class ReporteTests(unittest.TestCase):
    def setUp(self):
        self.usuarios = [
            UsuarioRegular("U001", "Ana", "ana@mail.com"),
            UsuarioPremium("U002", "Beto", "beto@mail.com"),
            UsuarioRegular("U003", "Carla", "carla@mail.com"),
        ]
        self.libros = [
            Libro("L001", "Uno", "Autor A", "9780306406157", 2),
            Libro("L002", "Dos", "Autor B", "9780306406164", 1),
            Libro("L003", "Tres", "Autor C", "9780306406171", 1),
        ]
        self.prestamos = []
        self.servicio = PrestamoService(self.usuarios, self.libros, self.prestamos)
        self.reportes = ReporteService(self.usuarios, self.libros, self.prestamos)

    def test_ranking_ordena_por_puntaje(self):
        p1 = self.servicio.crear_prestamo("U001", "L001", date(2026, 1, 1))
        self.servicio.devolver(p1.id, date(2026, 1, 5))
        p2 = self.servicio.crear_prestamo("U002", "L001", date(2026, 1, 1))
        self.servicio.devolver(p2.id, date(2026, 2, 1))
        _, filas = self.reportes.ranking_usuarios()
        self.assertEqual([f[2] for f in filas], ["Ana", "Carla", "Beto"])
        self.assertEqual([f[0] for f in filas], [1, 2, 3])
        _, top = self.reportes.ranking_usuarios(limite=1)
        self.assertEqual(len(top), 1)

    def test_libros_mas_prestados(self):
        for usuario, fecha in (("U001", 1), ("U002", 2), ("U003", 3)):
            p = self.servicio.crear_prestamo(usuario, "L001", date(2026, 1, fecha))
            self.servicio.devolver(p.id, date(2026, 1, fecha + 1))
        p = self.servicio.crear_prestamo("U001", "L002", date(2026, 1, 10))
        self.servicio.devolver(p.id, date(2026, 1, 11))
        _, filas = self.reportes.libros_mas_prestados()
        self.assertEqual(filas[0][2], "Uno")
        self.assertEqual(filas[0][4], 3)
        self.assertEqual(filas[1][2], "Dos")
        self.assertEqual(len(filas), 2)

    def test_activos_atrasados_y_multas(self):
        self.servicio.crear_prestamo("U001", "L001", date(2026, 1, 1))
        self.servicio.crear_prestamo("U002", "L002", date(2026, 1, 1))
        hoy = date(2026, 1, 20)
        _, activos = self.reportes.prestamos_activos(hoy)
        self.assertEqual(len(activos), 2)
        self.assertTrue(activos[0][5].startswith("Atrasado"))
        self.assertTrue(activos[1][5].startswith("Vigente"))
        _, atrasados = self.reportes.prestamos_atrasados(hoy)
        self.assertEqual(len(atrasados), 1)
        self.assertEqual(atrasados[0][5], 5)
        self.assertEqual(atrasados[0][6], 10000)
        _, multas = self.reportes.multas_pendientes(hoy)
        self.assertEqual(multas[0][4], 10000)
        self.assertEqual(multas[0][5], "En curso: libro sin devolver")
        _, por_cobrar = self.reportes.multas_por_cobrar(hoy)
        self.assertEqual(por_cobrar, [])

    def test_multas_por_cobrar_y_resumen(self):
        p = self.servicio.crear_prestamo("U001", "L001", date(2026, 1, 1))
        self.servicio.devolver(p.id, date(2026, 1, 18))
        hoy = date(2026, 1, 19)
        _, por_cobrar = self.reportes.multas_por_cobrar(hoy)
        self.assertEqual(len(por_cobrar), 1)
        self.assertEqual(por_cobrar[0][5], 6000)
        self.servicio.pagar_multa(p.id, hoy)
        _, por_cobrar = self.reportes.multas_por_cobrar(hoy)
        self.assertEqual(por_cobrar, [])
        _, resumen = self.reportes.resumen(hoy)
        valores = dict(resumen)
        self.assertEqual(valores["Usuarios registrados"], 3)
        self.assertEqual(valores["Multas cobradas"], "$6.000 COP")
        self.assertEqual(valores["Multas pendientes"], "$0 COP")

    def test_reportes_toleran_usuarios_o_libros_eliminados(self):
        p = self.servicio.crear_prestamo("U003", "L003", date(2026, 1, 1))
        self.servicio.devolver(p.id, date(2026, 1, 2))
        self.usuarios.pop()
        self.libros.pop()
        _, historial = self.reportes.historial_prestamos(date(2026, 2, 1))
        self.assertIn("eliminado", historial[0][2])
        self.assertIn("eliminado", historial[0][4])

    def test_usuarios_y_catalogo_incluyen_deuda_y_estado(self):
        self.servicio.crear_prestamo("U001", "L002", date(2026, 1, 1))
        hoy = date(2026, 1, 17)
        _, filas = self.reportes.usuarios_registrados(hoy=hoy)
        ana = next(f for f in filas if f[0] == "U001")
        self.assertEqual(ana[5], 1)
        self.assertEqual(ana[6], 4000)
        _, catalogo = self.reportes.catalogo_libros()
        dos = next(f for f in catalogo if f[0] == "L002")
        self.assertEqual(dos[6], "PRESTADO")

    def test_historial_de_usuario(self):
        p = self.servicio.crear_prestamo("U001", "L001", date(2026, 1, 1))
        self.servicio.devolver(p.id, date(2026, 1, 10))
        _, filas = self.reportes.historial_usuario("U001", date(2026, 1, 11))
        self.assertEqual(filas[0][6], "Devuelto a tiempo")


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.registros = []
        self.auth = AuthService(self.registros)

    def test_admin_inicial_se_crea_una_sola_vez(self):
        self.assertTrue(self.auth.asegurar_admin_inicial())
        self.assertFalse(self.auth.asegurar_admin_inicial())
        self.assertEqual(len(self.registros), 1)
        self.assertNotIn("admin123", str(self.registros))

    def test_autenticacion(self):
        self.auth.asegurar_admin_inicial()
        self.assertIsNotNone(self.auth.autenticar("admin", "admin123"))
        self.assertIsNotNone(self.auth.autenticar(" ADMIN ", "admin123"))
        self.assertIsNone(self.auth.autenticar("admin", "incorrecta"))
        self.assertIsNone(self.auth.autenticar("otro", "admin123"))
        self.assertTrue(self.auth.debe_cambiar_clave("admin"))

    def test_cambiar_clave(self):
        self.auth.asegurar_admin_inicial()
        with self.assertRaises(ReglaNegocioError):
            self.auth.cambiar_clave("admin", "mala", "nuevaclave1")
        with self.assertRaises(ValidacionError):
            self.auth.cambiar_clave("admin", "admin123", "123")
        with self.assertRaises(ReglaNegocioError):
            self.auth.cambiar_clave("admin", "admin123", "admin123")
        self.auth.cambiar_clave("admin", "admin123", "nuevaclave1")
        self.assertIsNone(self.auth.autenticar("admin", "admin123"))
        self.assertIsNotNone(self.auth.autenticar("admin", "nuevaclave1"))
        self.assertFalse(self.auth.debe_cambiar_clave("admin"))

    def test_credenciales_persisten_en_json(self):
        self.auth.asegurar_admin_inicial()
        with tempfile.TemporaryDirectory() as temp:
            repo = JsonRepository(Path(temp) / "admin.json", registro_admin_desde_dict)
            repo.guardar(self.registros)
            cargados = repo.cargar()
            self.assertIsNotNone(AuthService(cargados).autenticar("admin", "admin123"))

    def test_registro_admin_corrupto_se_rechaza(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / "admin.json"
            ruta.write_text('[{"usuario": "admin", "sal": "no-hex", "hash": "x"}]', encoding="utf-8")
            with self.assertRaises(PersistenciaError):
                JsonRepository(ruta, registro_admin_desde_dict).cargar()


if __name__ == "__main__":
    unittest.main()
