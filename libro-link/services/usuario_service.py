from datetime import date

from models.usuario import crear_usuario
from services.errores import EntidadNoEncontradaError, ReglaNegocioError
from services.utilidades import formatear_pesos, generar_id, orden_natural
from validators.validaciones import (
    normalizar_texto,
    validar_email,
    validar_nombre,
    validar_rol,
    validar_termino_busqueda,
)


class UsuarioService:
    def __init__(self, usuarios, prestamos=None):
        self.usuarios = usuarios
        self.prestamos = prestamos if prestamos is not None else []

    def validar_email_disponible(self, valor, excluir_id=None):
        email = validar_email(valor)
        for usuario in self.usuarios:
            if usuario.id_usuario == excluir_id:
                continue
            if usuario.email.lower() == email:
                raise ReglaNegocioError(
                    f"El correo '{email}' ya está registrado para {usuario.nombre}."
                )
        return email

    def registrar(self, nombre, email, rol="regular"):
        nombre = validar_nombre(nombre)
        email = self.validar_email_disponible(email)
        rol = validar_rol(rol)
        identificadores = [u.id_usuario for u in self.usuarios]
        identificadores += [p.id_usuario for p in self.prestamos]
        usuario = crear_usuario(rol, generar_id("U", identificadores), nombre, email)
        self.usuarios.append(usuario)
        return usuario

    def obtener(self, id_usuario):
        clave = str(id_usuario).strip().upper()
        for usuario in self.usuarios:
            if str(usuario.id_usuario).upper() == clave:
                return usuario
        raise EntidadNoEncontradaError(f"No existe un usuario con ID '{id_usuario}'.")

    def listar(self):
        return sorted(self.usuarios, key=lambda u: orden_natural(u.id_usuario))

    def buscar(self, termino):
        termino = normalizar_texto(validar_termino_busqueda(termino))
        coincidencias = [
            usuario
            for usuario in self.usuarios
            if termino in normalizar_texto(usuario.nombre)
            or termino in usuario.email.lower()
        ]
        return sorted(coincidencias, key=lambda u: orden_natural(u.id_usuario))

    def actualizar(self, id_usuario, nombre=None, email=None, rol=None):
        usuario = self.obtener(id_usuario)
        nuevo_nombre = validar_nombre(nombre) if nombre is not None else usuario.nombre
        nuevo_email = (
            self.validar_email_disponible(email, excluir_id=usuario.id_usuario)
            if email is not None
            else usuario.email
        )
        nuevo_rol = validar_rol(rol) if rol is not None else usuario.rol
        reemplazo = crear_usuario(
            nuevo_rol,
            usuario.id_usuario,
            nuevo_nombre,
            nuevo_email,
            usuario.puntaje_confiabilidad,
        )
        posicion = self.usuarios.index(usuario)
        self.usuarios[posicion] = reemplazo
        return reemplazo

    def eliminar(self, id_usuario, hoy=None):
        usuario = self.obtener(id_usuario)
        hoy = hoy or date.today()
        for prestamo in self.prestamos:
            if prestamo.id_usuario != usuario.id_usuario:
                continue
            if prestamo.activo:
                raise ReglaNegocioError(
                    f"No se puede eliminar a {usuario.nombre}: tiene préstamos activos."
                )
            pendiente = prestamo.multa_pendiente(hoy)
            if pendiente > 0:
                raise ReglaNegocioError(
                    f"No se puede eliminar a {usuario.nombre}: debe una multa de "
                    f"{formatear_pesos(pendiente)} COP."
                )
        self.usuarios.remove(usuario)
        return usuario
