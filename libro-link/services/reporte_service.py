from collections import Counter
from datetime import date

from services.utilidades import formatear_pesos, orden_natural, plural_dias
from validators.validaciones import normalizar_texto


class ReporteService:
    def __init__(self, usuarios, libros, prestamos):
        self.usuarios = usuarios
        self.libros = libros
        self.prestamos = prestamos

    def _usuario(self, id_usuario):
        for usuario in self.usuarios:
            if usuario.id_usuario == id_usuario:
                return usuario
        return None

    def _libro(self, id_libro):
        for libro in self.libros:
            if libro.id_libro == id_libro:
                return libro
        return None

    def _nombre_usuario(self, id_usuario):
        usuario = self._usuario(id_usuario)
        return usuario.nombre if usuario else f"{id_usuario} (eliminado)"

    def _correo_usuario(self, id_usuario):
        usuario = self._usuario(id_usuario)
        return usuario.email if usuario else ""

    def _titulo_libro(self, id_libro):
        libro = self._libro(id_libro)
        return libro.titulo if libro else f"{id_libro} (eliminado)"

    def _autor_libro(self, id_libro):
        libro = self._libro(id_libro)
        return libro.autor if libro else ""

    @staticmethod
    def _ordenados(prestamos):
        return sorted(prestamos, key=lambda p: orden_natural(p.id_prestamo))

    def usuarios_registrados(self, seleccion=None, hoy=None):
        hoy = hoy or date.today()
        lista = self.usuarios if seleccion is None else seleccion
        filas = []
        for usuario in sorted(lista, key=lambda u: orden_natural(u.id_usuario)):
            propios = [p for p in self.prestamos if p.id_usuario == usuario.id_usuario]
            activos = sum(1 for p in propios if p.activo)
            deuda = sum(p.multa_pendiente(hoy) for p in propios)
            filas.append(
                [
                    usuario.id_usuario,
                    usuario.nombre,
                    usuario.email,
                    usuario.rol.capitalize(),
                    usuario.puntaje_confiabilidad,
                    activos,
                    deuda,
                ]
            )
        encabezados = [
            "ID",
            "Nombre",
            "Correo",
            "Rol",
            "Puntaje",
            "Préstamos activos",
            "Deuda (COP)",
        ]
        return encabezados, filas

    def catalogo_libros(self, seleccion=None):
        lista = self.libros if seleccion is None else seleccion
        filas = [
            [
                libro.id_libro,
                libro.titulo,
                libro.autor,
                libro.isbn,
                libro.stock_total,
                libro.stock_disponible,
                libro.estado,
            ]
            for libro in sorted(lista, key=lambda l: orden_natural(l.id_libro))
        ]
        encabezados = [
            "ID",
            "Título",
            "Autor",
            "ISBN",
            "Ejemplares",
            "Disponibles",
            "Estado",
        ]
        return encabezados, filas

    def prestamos_activos(self, hoy=None):
        hoy = hoy or date.today()
        filas = []
        for prestamo in self._ordenados([p for p in self.prestamos if p.activo]):
            restantes = (prestamo.fecha_vencimiento - hoy).days
            if restantes < 0:
                estado = f"Atrasado ({plural_dias(-restantes)})"
            elif restantes == 0:
                estado = "Vence hoy"
            else:
                estado = f"Vigente (faltan {plural_dias(restantes)})"
            filas.append(
                [
                    prestamo.id_prestamo,
                    self._nombre_usuario(prestamo.id_usuario),
                    self._titulo_libro(prestamo.id_libro),
                    prestamo.fecha_prestamo,
                    prestamo.fecha_vencimiento,
                    estado,
                ]
            )
        encabezados = [
            "ID préstamo",
            "Usuario",
            "Libro",
            "Fecha préstamo",
            "Vence",
            "Estado",
        ]
        return encabezados, filas

    def prestamos_atrasados(self, hoy=None):
        hoy = hoy or date.today()
        atrasados = [p for p in self.prestamos if p.esta_atrasado(hoy)]
        atrasados.sort(
            key=lambda p: (-p.dias_retraso(hoy), orden_natural(p.id_prestamo))
        )
        filas = [
            [
                p.id_prestamo,
                self._nombre_usuario(p.id_usuario),
                self._correo_usuario(p.id_usuario),
                self._titulo_libro(p.id_libro),
                p.fecha_vencimiento,
                p.dias_retraso(hoy),
                p.multa_acumulada(hoy),
            ]
            for p in atrasados
        ]
        encabezados = [
            "ID préstamo",
            "Usuario",
            "Correo",
            "Libro",
            "Vencía",
            "Días de retraso",
            "Multa acumulada (COP)",
        ]
        return encabezados, filas

    def ranking_usuarios(self, limite=None):
        ordenados = sorted(
            self.usuarios,
            key=lambda u: (-u.puntaje_confiabilidad, normalizar_texto(u.nombre)),
        )
        if limite is not None:
            ordenados = ordenados[:limite]
        filas = [
            [
                posicion,
                usuario.id_usuario,
                usuario.nombre,
                usuario.rol.capitalize(),
                usuario.puntaje_confiabilidad,
                usuario.nivel_confiabilidad(),
            ]
            for posicion, usuario in enumerate(ordenados, start=1)
        ]
        encabezados = ["Posición", "ID", "Nombre", "Rol", "Puntaje", "Nivel"]
        return encabezados, filas

    def libros_mas_prestados(self, limite=10):
        conteo = Counter(p.id_libro for p in self.prestamos)
        ordenados = sorted(
            conteo.items(),
            key=lambda par: (-par[1], normalizar_texto(self._titulo_libro(par[0]))),
        )[:limite]
        filas = [
            [
                posicion,
                id_libro,
                self._titulo_libro(id_libro),
                self._autor_libro(id_libro),
                veces,
            ]
            for posicion, (id_libro, veces) in enumerate(ordenados, start=1)
        ]
        encabezados = ["Posición", "ID", "Título", "Autor", "Veces prestado"]
        return encabezados, filas

    def multas_pendientes(self, hoy=None):
        hoy = hoy or date.today()
        pendientes = self._ordenados(
            [p for p in self.prestamos if p.multa_pendiente(hoy) > 0]
        )
        filas = [
            [
                p.id_prestamo,
                self._nombre_usuario(p.id_usuario),
                self._titulo_libro(p.id_libro),
                p.dias_retraso(hoy),
                p.multa_pendiente(hoy),
                "En curso: libro sin devolver" if p.activo else "Pendiente de pago",
            ]
            for p in pendientes
        ]
        encabezados = [
            "ID préstamo",
            "Usuario",
            "Libro",
            "Días de retraso",
            "Multa (COP)",
            "Situación",
        ]
        return encabezados, filas

    def multas_por_cobrar(self, hoy=None):
        hoy = hoy or date.today()
        por_cobrar = self._ordenados(
            [p for p in self.prestamos if not p.activo and p.multa_pendiente(hoy) > 0]
        )
        filas = [
            [
                p.id_prestamo,
                self._nombre_usuario(p.id_usuario),
                self._titulo_libro(p.id_libro),
                p.fecha_devolucion,
                p.dias_retraso(hoy),
                p.multa,
            ]
            for p in por_cobrar
        ]
        encabezados = [
            "ID préstamo",
            "Usuario",
            "Libro",
            "Devuelto",
            "Días de retraso",
            "Multa (COP)",
        ]
        return encabezados, filas

    def historial_usuario(self, id_usuario, hoy=None):
        hoy = hoy or date.today()
        propios = self._ordenados(
            [p for p in self.prestamos if p.id_usuario == id_usuario]
        )
        filas = []
        for p in propios:
            if p.activo:
                estado = "Atrasado" if p.esta_atrasado(hoy) else "Activo"
            elif p.multa <= 0:
                estado = "Devuelto a tiempo"
            elif p.multa_pagada:
                estado = "Devuelto con multa pagada"
            else:
                estado = "Devuelto con multa pendiente"
            filas.append(
                [
                    p.id_prestamo,
                    self._titulo_libro(p.id_libro),
                    p.fecha_prestamo,
                    p.fecha_vencimiento,
                    p.fecha_devolucion,
                    p.multa_acumulada(hoy),
                    estado,
                ]
            )
        encabezados = [
            "ID préstamo",
            "Libro",
            "Prestado",
            "Vence",
            "Devuelto",
            "Multa (COP)",
            "Estado",
        ]
        return encabezados, filas

    def historial_prestamos(self, hoy=None):
        hoy = hoy or date.today()
        filas = []
        for p in self._ordenados(self.prestamos):
            if p.multa_acumulada(hoy) <= 0:
                pagada = ""
            else:
                pagada = "Sí" if p.multa_pagada else "No"
            filas.append(
                [
                    p.id_prestamo,
                    p.id_usuario,
                    self._nombre_usuario(p.id_usuario),
                    p.id_libro,
                    self._titulo_libro(p.id_libro),
                    p.fecha_prestamo,
                    p.fecha_vencimiento,
                    p.fecha_devolucion,
                    p.dias_retraso(hoy),
                    p.multa_acumulada(hoy),
                    pagada,
                    p.fecha_pago,
                ]
            )
        encabezados = [
            "ID préstamo",
            "ID usuario",
            "Usuario",
            "ID libro",
            "Libro",
            "Fecha préstamo",
            "Vence",
            "Fecha devolución",
            "Días de retraso",
            "Multa (COP)",
            "Multa pagada",
            "Fecha de pago",
        ]
        return encabezados, filas

    def resumen(self, hoy=None):
        hoy = hoy or date.today()
        pendientes = sum(p.multa_pendiente(hoy) for p in self.prestamos)
        cobradas = sum(p.multa for p in self.prestamos if p.multa_pagada)
        filas = [
            ["Usuarios registrados", len(self.usuarios)],
            ["Títulos en el catálogo", len(self.libros)],
            ["Ejemplares en total", sum(l.stock_total for l in self.libros)],
            ["Ejemplares disponibles", sum(l.stock_disponible for l in self.libros)],
            ["Préstamos activos", sum(1 for p in self.prestamos if p.activo)],
            [
                "Préstamos atrasados",
                sum(1 for p in self.prestamos if p.esta_atrasado(hoy)),
            ],
            ["Multas pendientes", f"{formatear_pesos(pendientes)} COP"],
            ["Multas cobradas", f"{formatear_pesos(cobradas)} COP"],
        ]
        return ["Indicador", "Valor"], filas
