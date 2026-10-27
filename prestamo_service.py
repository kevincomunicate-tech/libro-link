from datetime import date, timedelta

from models.prestamo import Prestamo
from services.errores import EntidadNoEncontradaError, ReglaNegocioError
from services.utilidades import formatear_pesos, generar_id, orden_natural


class PrestamoService:
    def __init__(self, usuarios, libros, prestamos=None):
        self.usuarios = usuarios
        self.libros = libros
        self.prestamos = prestamos if prestamos is not None else []

    def _usuario(self, id_usuario):
        clave = str(id_usuario).strip().upper()
        for usuario in self.usuarios:
            if str(usuario.id_usuario).upper() == clave:
                return usuario
        raise EntidadNoEncontradaError(f"No existe un usuario con ID '{id_usuario}'.")

    def _libro(self, id_libro):
        clave = str(id_libro).strip().upper()
        for libro in self.libros:
            if str(libro.id_libro).upper() == clave:
                return libro
        raise EntidadNoEncontradaError(f"No existe un libro con ID '{id_libro}'.")

    def _libro_o_nada(self, id_libro):
        for libro in self.libros:
            if libro.id_libro == id_libro:
                return libro
        return None

    def _usuario_o_nada(self, id_usuario):
        for usuario in self.usuarios:
            if usuario.id_usuario == id_usuario:
                return usuario
        return None

    def obtener(self, id_prestamo):
        clave = str(id_prestamo).strip().upper()
        for prestamo in self.prestamos:
            if str(prestamo.id_prestamo).upper() == clave:
                return prestamo
        raise EntidadNoEncontradaError(f"No existe un préstamo con ID '{id_prestamo}'.")

    def crear_prestamo(self, id_usuario, id_libro, fecha=None):
        fecha = fecha or date.today()
        usuario = self._usuario(id_usuario)
        libro = self._libro(id_libro)

        deuda = self.deuda_usuario(usuario.id_usuario, fecha)
        if deuda > 0:
            raise ReglaNegocioError(
                f"{usuario.nombre} tiene una deuda pendiente de {formatear_pesos(deuda)} COP. "
                "Debe devolver los libros atrasados y pagar sus multas antes de un nuevo préstamo."
            )

        activos = self.activos_de(usuario.id_usuario)
        if len(activos) >= usuario.limite_prestamos():
            raise ReglaNegocioError(
                f"{usuario.nombre} alcanzó su límite de {usuario.limite_prestamos()} "
                f"préstamos simultáneos (rol {usuario.rol})."
            )
        if any(p.id_libro == libro.id_libro for p in activos):
            raise ReglaNegocioError(
                f"{usuario.nombre} ya tiene prestado '{libro.titulo}'."
            )
        if not libro.disponible:
            raise ReglaNegocioError(
                f"No hay ejemplares disponibles de '{libro.titulo}'."
            )

        prestamo = Prestamo(
            generar_id("P", [p.id_prestamo for p in self.prestamos]),
            usuario.id_usuario,
            libro.id_libro,
            fecha,
            fecha + timedelta(days=usuario.dias_prestamo()),
        )
        libro.prestar()
        self.prestamos.append(prestamo)
        return prestamo

    def devolver(self, id_prestamo, fecha=None):
        fecha = fecha or date.today()
        prestamo = self.obtener(id_prestamo)
        if not prestamo.activo:
            raise ReglaNegocioError(
                f"El préstamo {prestamo.id_prestamo} ya fue devuelto."
            )
        if fecha < prestamo.fecha_prestamo:
            raise ReglaNegocioError(
                "La fecha de devolución no puede ser anterior a la fecha del préstamo."
            )
        prestamo.cerrar(fecha)
        libro = self._libro_o_nada(prestamo.id_libro)
        if libro is not None:
            libro.devolver()
        usuario = self._usuario_o_nada(prestamo.id_usuario)
        if usuario is not None:
            if prestamo.multa > 0:
                usuario.registrar_devolucion_tardia()
            else:
                usuario.registrar_devolucion_a_tiempo()
        return prestamo

    def validar_multa_cobrable(self, id_prestamo):
        prestamo = self.obtener(id_prestamo)
        if prestamo.activo:
            raise ReglaNegocioError(
                "El libro aún no ha sido devuelto: registre la devolución antes de cobrar la multa."
            )
        if prestamo.multa <= 0:
            raise ReglaNegocioError(
                f"El préstamo {prestamo.id_prestamo} no tiene multa."
            )
        if prestamo.multa_pagada:
            raise ReglaNegocioError(
                f"La multa del préstamo {prestamo.id_prestamo} ya fue pagada."
            )
        return prestamo

    def pagar_multa(self, id_prestamo, fecha=None):
        fecha = fecha or date.today()
        prestamo = self.validar_multa_cobrable(id_prestamo)
        prestamo.pagar(fecha)
        return prestamo

    def activos(self):
        return self._ordenar([p for p in self.prestamos if p.activo])

    def activos_de(self, id_usuario):
        return [
            p for p in self.prestamos if p.activo and p.id_usuario == id_usuario
        ]

    def atrasados(self, hoy=None):
        hoy = hoy or date.today()
        return self._ordenar([p for p in self.prestamos if p.esta_atrasado(hoy)])

    def multas_pendientes(self, hoy=None):
        hoy = hoy or date.today()
        return self._ordenar([p for p in self.prestamos if p.multa_pendiente(hoy) > 0])

    def deuda_usuario(self, id_usuario, hoy=None):
        hoy = hoy or date.today()
        return sum(
            p.multa_pendiente(hoy) for p in self.prestamos if p.id_usuario == id_usuario
        )

    def historial_usuario(self, id_usuario):
        return self._ordenar([p for p in self.prestamos if p.id_usuario == id_usuario])

    @staticmethod
    def _ordenar(prestamos):
        return sorted(prestamos, key=lambda p: orden_natural(p.id_prestamo))
