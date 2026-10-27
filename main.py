import sys
from getpass import getpass
from pathlib import Path

from models.libro import Libro
from models.prestamo import MULTA_DIARIA, Prestamo
from models.usuario import Usuario, UsuarioPremium, UsuarioRegular
from persistence.csv_exporter import exportar_csv
from persistence.json_repository import JsonRepository
from services.auth_service import (
    CLAVE_INICIAL,
    USUARIO_INICIAL,
    AuthService,
    registro_admin_desde_dict,
)
from services.errores import (
    EntidadNoEncontradaError,
    PersistenciaError,
    ReglaNegocioError,
)
from services.libro_service import LibroService
from services.prestamo_service import PrestamoService
from services.reporte_service import ReporteService
from services.usuario_service import UsuarioService
from services.utilidades import formatear_pesos, plural_ejemplares
from ui.consola import (
    aviso_cancelar,
    confirmar,
    ejecutar_menu,
    encabezado,
    leer,
    mensaje_error,
    mensaje_info,
    mensaje_ok,
    pedir,
    tabla,
)
from validators.validaciones import (
    validar_autor,
    validar_nombre,
    validar_rol,
    validar_stock,
    validar_termino_busqueda,
    validar_titulo,
)

RUTA_DATOS = Path(__file__).resolve().parent / "data"
MAXIMO_INTENTOS_LOGIN = 3


class ArranqueCancelado(Exception):
    pass


class Aplicacion:
    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        self.usuarios = []
        self.libros = []
        self.prestamos = []
        self.administradores = []
        self.fuentes = [
            (
                "usuarios",
                JsonRepository(self.carpeta / "usuarios.json", Usuario.from_dict),
                self.usuarios,
            ),
            (
                "libros",
                JsonRepository(self.carpeta / "libros.json", Libro.from_dict),
                self.libros,
            ),
            (
                "préstamos",
                JsonRepository(self.carpeta / "prestamos.json", Prestamo.from_dict),
                self.prestamos,
            ),
            (
                "administrador",
                JsonRepository(self.carpeta / "admin.json", registro_admin_desde_dict),
                self.administradores,
            ),
        ]
        self.fuentes_datos = self.fuentes[:3]
        self.servicio_usuarios = UsuarioService(self.usuarios, self.prestamos)
        self.servicio_libros = LibroService(self.libros, self.prestamos)
        self.servicio_prestamos = PrestamoService(
            self.usuarios, self.libros, self.prestamos
        )
        self.reportes = ReporteService(self.usuarios, self.libros, self.prestamos)
        self.auth = AuthService(self.administradores)
        self.sesion = None

    def cargar_inicial(self):
        for etiqueta, repositorio, coleccion in self.fuentes:
            try:
                coleccion[:] = repositorio.cargar()
            except PersistenciaError as error:
                mensaje_error(str(error))
                if not confirmar(
                    f"¿Desea respaldar el archivo dañado de {etiqueta} y continuar "
                    "con esa información vacía?"
                ):
                    raise ArranqueCancelado()
                destino = repositorio.respaldar()
                mensaje_ok(f"El archivo dañado se conservó como '{destino.name}'.")
                coleccion[:] = []

    def recargar(self):
        nuevos = [repositorio.cargar() for _, repositorio, _ in self.fuentes_datos]
        for (_, _, coleccion), datos in zip(self.fuentes_datos, nuevos):
            coleccion[:] = datos

    def guardar_datos(self):
        for _, repositorio, coleccion in self.fuentes_datos:
            repositorio.guardar(coleccion)

    def guardar_administradores(self):
        _, repositorio, coleccion = self.fuentes[3]
        repositorio.guardar(coleccion)

    def persistir(self):
        try:
            self.guardar_datos()
            return True
        except PersistenciaError as error:
            mensaje_error(
                f"{error} Los cambios siguen en memoria; use la opción "
                "'Guardar datos' del menú principal para reintentar."
            )
            return False


def descripcion_rol(clase):
    return (
        f"{clase.ROL.capitalize()}: hasta {clase.LIMITE_PRESTAMOS} libros a la vez, "
        f"{clase.DIAS_PRESTAMO} días de préstamo"
    )


def mostrar_rol_opciones():
    print("\nRoles disponibles:")
    print(f"  1. {descripcion_rol(UsuarioRegular)}")
    print(f"  2. {descripcion_rol(UsuarioPremium)}")


def convertir_rol(valor):
    atajos = {"1": "regular", "2": "premium"}

    return validar_rol(atajos.get(str(valor).strip(), valor))


def mostrar_reporte(app, titulo, datos, archivo_csv=None):
    encabezados, filas = datos
    print(f"\n--- {titulo} ---")
    if not filas:
        mensaje_info("No hay información para mostrar.")
        return
    tabla(encabezados, filas)
    if archivo_csv and confirmar("\n¿Desea exportar este reporte a CSV?"):
        ruta = exportar_csv(app.carpeta / archivo_csv, encabezados, filas)
        mensaje_ok(f"Reporte exportado en: {ruta}")


def elegir_usuario(app):
    while True:
        entrada = leer("ID, nombre o correo del usuario: ").strip()
        if not entrada:
            mensaje_error("Debe ingresar un dato para identificar al usuario.")
            continue
        try:
            return app.servicio_usuarios.obtener(entrada)
        except EntidadNoEncontradaError:
            pass
        try:
            coincidencias = app.servicio_usuarios.buscar(entrada)
        except ReglaNegocioError as error:
            mensaje_error(str(error))
            continue
        if not coincidencias:
            mensaje_error(f"No se encontró ningún usuario con '{entrada}'.")
            continue
        if len(coincidencias) == 1:
            usuario = coincidencias[0]
            if confirmar(f"¿Es {usuario.nombre} ({usuario.id_usuario})?"):
                return usuario
            continue
        mensaje_info("Hay varias coincidencias. Ingrese el ID exacto del usuario.")
        tabla(*app.reportes.usuarios_registrados(coincidencias))


def elegir_libro(app):
    while True:
        entrada = leer("ID, título, autor o ISBN del libro: ").strip()
        if not entrada:
            mensaje_error("Debe ingresar un dato para identificar el libro.")
            continue
        try:
            return app.servicio_libros.obtener(entrada)
        except EntidadNoEncontradaError:
            pass
        try:
            coincidencias = app.servicio_libros.buscar(entrada)
        except ReglaNegocioError as error:
            mensaje_error(str(error))
            continue
        if not coincidencias:
            mensaje_error(f"No se encontró ningún libro con '{entrada}'.")
            continue
        if len(coincidencias) == 1:
            libro = coincidencias[0]
            if confirmar(f"¿Es '{libro.titulo}' de {libro.autor} ({libro.id_libro})?"):
                return libro
            continue
        mensaje_info("Hay varias coincidencias. Ingrese el ID exacto del libro.")
        tabla(*app.reportes.catalogo_libros(coincidencias))


def registrar_usuario(app):
    aviso_cancelar()
    nombre = pedir("Nombre completo", validar_nombre)
    email = pedir("Correo electrónico", app.servicio_usuarios.validar_email_disponible)
    mostrar_rol_opciones()
    rol = pedir("Rol (1 o 2)", convertir_rol)
    usuario = app.servicio_usuarios.registrar(nombre, email, rol)
    app.persistir()
    mensaje_ok(
        f"Usuario {usuario.nombre} registrado con ID {usuario.id_usuario}. "
        "Ya aparece en la lista de usuarios."
    )


def listar_usuarios(app):
    encabezados, filas = app.reportes.usuarios_registrados()
    if not filas:
        mensaje_info("No hay usuarios registrados.")
        return
    print(f"\nUsuarios registrados: {len(filas)}")
    tabla(encabezados, filas)


def buscar_usuarios(app):
    aviso_cancelar()
    termino = pedir("Nombre o correo a buscar", validar_termino_busqueda)
    resultados = app.servicio_usuarios.buscar(termino)
    if not resultados:
        mensaje_info(f"No se encontraron usuarios que coincidan con '{termino}'.")
        return
    print(f"\nCoincidencias: {len(resultados)}")
    tabla(*app.reportes.usuarios_registrados(resultados))


def ver_ficha_usuario(app):
    aviso_cancelar()
    usuario = elegir_usuario(app)
    activos = len(app.servicio_prestamos.activos_de(usuario.id_usuario))
    deuda = app.servicio_prestamos.deuda_usuario(usuario.id_usuario)
    encabezado(f"FICHA DE {usuario.nombre.upper()}")
    print(f"  ID:                 {usuario.id_usuario}")
    print(f"  Correo:             {usuario.email}")
    print(f"  Rol:                {descripcion_rol(type(usuario))}")
    print(
        f"  Confiabilidad:      {usuario.puntaje_confiabilidad}/100 "
        f"({usuario.nivel_confiabilidad()})"
    )
    print(f"  Préstamos activos:  {activos} de {usuario.limite_prestamos()}")
    print(f"  Deuda por multas:   {formatear_pesos(deuda)} COP")
    encabezados, filas = app.reportes.historial_usuario(usuario.id_usuario)
    if filas:
        print("\nHistorial de préstamos:")
        tabla(encabezados, filas)
    else:
        mensaje_info("Este usuario aún no tiene préstamos.")


def editar_usuario(app):
    aviso_cancelar()
    usuario = elegir_usuario(app)
    print("\nPresione Enter para conservar el valor actual.")
    nombre = pedir("Nombre completo", validar_nombre, usuario.nombre)

    def validar_correo(valor):
        return app.servicio_usuarios.validar_email_disponible(
            valor, excluir_id=usuario.id_usuario
        )

    email = pedir("Correo electrónico", validar_correo, usuario.email)
    mostrar_rol_opciones()
    rol = pedir("Rol (1 o 2)", convertir_rol, usuario.rol)
    actualizado = app.servicio_usuarios.actualizar(
        usuario.id_usuario, nombre=nombre, email=email, rol=rol
    )
    app.persistir()
    mensaje_ok(f"Usuario {actualizado.id_usuario} actualizado correctamente.")


def eliminar_usuario(app):
    aviso_cancelar()
    usuario = elegir_usuario(app)
    if not confirmar(
        f"¿Eliminar definitivamente a {usuario.nombre} ({usuario.id_usuario})?"
    ):
        mensaje_info("No se eliminó ningún usuario.")
        return
    app.servicio_usuarios.eliminar(usuario.id_usuario)
    app.persistir()
    mensaje_ok(f"Usuario {usuario.nombre} eliminado.")


def registrar_libro(app):
    aviso_cancelar()
    titulo = pedir("Título", validar_titulo)
    autor = pedir("Autor", validar_autor)
    isbn = pedir("ISBN (10 o 13 dígitos)", app.servicio_libros.validar_isbn_disponible)
    stock = pedir("Cantidad de ejemplares", validar_stock)
    libro = app.servicio_libros.registrar(titulo, autor, isbn, stock)
    app.persistir()
    mensaje_ok(
        f"Libro '{libro.titulo}' registrado con ID {libro.id_libro} "
        f"({plural_ejemplares(libro.stock_total)}). Ya aparece en el catálogo."
    )


def listar_libros(app, solo_disponibles=False):
    libros = app.servicio_libros.listar(solo_disponibles=solo_disponibles)
    if not libros:
        mensaje_info(
            "No hay libros disponibles." if solo_disponibles else "No hay libros registrados."
        )
        return
    print(f"\nLibros en la lista: {len(libros)}")
    tabla(*app.reportes.catalogo_libros(libros))


def buscar_libros(app):
    aviso_cancelar()
    termino = pedir("Título, autor o ISBN a buscar", validar_termino_busqueda)
    resultados = app.servicio_libros.buscar(termino)
    if not resultados:
        mensaje_info(f"No se encontraron libros que coincidan con '{termino}'.")
        return
    print(f"\nCoincidencias: {len(resultados)}")
    tabla(*app.reportes.catalogo_libros(resultados))


def editar_libro(app):
    aviso_cancelar()
    libro = elegir_libro(app)
    print("\nPresione Enter para conservar el valor actual.")
    titulo = pedir("Título", validar_titulo, libro.titulo)
    autor = pedir("Autor", validar_autor, libro.autor)

    def validar_isbn_libre(valor):
        return app.servicio_libros.validar_isbn_disponible(
            valor, excluir_id=libro.id_libro
        )

    isbn = pedir("ISBN (10 o 13 dígitos)", validar_isbn_libre, libro.isbn)
    stock = pedir("Cantidad de ejemplares", validar_stock, libro.stock_total)
    actualizado = app.servicio_libros.actualizar(
        libro.id_libro, titulo=titulo, autor=autor, isbn=isbn, stock=stock
    )
    app.persistir()
    mensaje_ok(f"Libro {actualizado.id_libro} actualizado correctamente.")


def eliminar_libro(app):
    aviso_cancelar()
    libro = elegir_libro(app)
    if not confirmar(f"¿Eliminar definitivamente '{libro.titulo}' ({libro.id_libro})?"):
        mensaje_info("No se eliminó ningún libro.")
        return
    app.servicio_libros.eliminar(libro.id_libro)
    app.persistir()
    mensaje_ok(f"Libro '{libro.titulo}' eliminado.")


def registrar_prestamo(app):
    aviso_cancelar()
    usuario = elegir_usuario(app)
    libro = elegir_libro(app)
    prestamo = app.servicio_prestamos.crear_prestamo(
        usuario.id_usuario, libro.id_libro
    )
    app.persistir()
    mensaje_ok(
        f"Préstamo {prestamo.id_prestamo} registrado: '{libro.titulo}' para {usuario.nombre}."
    )
    print(
        f"Debe devolverlo a más tardar el {prestamo.fecha_vencimiento.strftime('%d/%m/%Y')}. "
        f"Por cada día de retraso se cobra {formatear_pesos(MULTA_DIARIA)} COP."
    )


def registrar_devolucion(app):
    activos = app.reportes.prestamos_activos()
    if not activos[1]:
        mensaje_info("No hay préstamos activos para devolver.")
        return
    tabla(*activos)
    print()
    aviso_cancelar()
    id_prestamo = leer("ID del préstamo que se devuelve: ").strip()
    prestamo = app.servicio_prestamos.obtener(id_prestamo)
    usuario = app.servicio_usuarios.obtener(prestamo.id_usuario)
    puntaje_anterior = usuario.puntaje_confiabilidad
    prestamo = app.servicio_prestamos.devolver(prestamo.id_prestamo)
    diferencia = usuario.puntaje_confiabilidad - puntaje_anterior
    app.persistir()
    mensaje_ok(f"Devolución del préstamo {prestamo.id_prestamo} registrada.")
    print(
        f"Puntaje de confiabilidad de {usuario.nombre}: "
        f"{usuario.puntaje_confiabilidad} ({diferencia:+d})."
    )
    if prestamo.multa <= 0:
        print("Devolución a tiempo: no se genera multa.")
        return
    print(
        f"Devolución con {prestamo.dias_retraso()} día(s) de retraso. "
        f"Multa generada: {formatear_pesos(prestamo.multa)} COP."
    )
    if confirmar("¿El usuario paga la multa ahora?"):
        app.servicio_prestamos.pagar_multa(prestamo.id_prestamo)
        app.persistir()
        mensaje_ok("Pago de la multa registrado.")
    else:
        mensaje_info(
            "La multa queda pendiente y el usuario no podrá pedir libros hasta pagarla."
        )


def ver_prestamos_activos(app):
    mostrar_reporte(
        app, "PRÉSTAMOS ACTIVOS", app.reportes.prestamos_activos(), "prestamos_activos.csv"
    )


def ver_prestamos_atrasados(app):
    mostrar_reporte(
        app,
        f"PRÉSTAMOS ATRASADOS (multa de {formatear_pesos(MULTA_DIARIA)} COP por día)",
        app.reportes.prestamos_atrasados(),
        "prestamos_atrasados.csv",
    )


def ver_multas_pendientes(app):
    mostrar_reporte(
        app, "MULTAS PENDIENTES", app.reportes.multas_pendientes(), "multas_pendientes.csv"
    )


def registrar_pago_multa(app):
    por_cobrar = app.reportes.multas_por_cobrar()
    if not por_cobrar[1]:
        mensaje_info("No hay multas pendientes de pago.")
        return
    tabla(*por_cobrar)
    print()
    aviso_cancelar()
    id_prestamo = leer("ID del préstamo cuya multa se paga: ").strip()
    prestamo = app.servicio_prestamos.validar_multa_cobrable(id_prestamo)
    if not confirmar(f"¿Confirmar el cobro de {formatear_pesos(prestamo.multa)} COP?"):
        mensaje_info("No se registró ningún pago.")
        return
    app.servicio_prestamos.pagar_multa(prestamo.id_prestamo)
    app.persistir()
    mensaje_ok(
        f"Pago de {formatear_pesos(prestamo.multa)} COP registrado para el préstamo "
        f"{prestamo.id_prestamo}."
    )


def exportar_todo(app):
    reportes = app.reportes
    archivos = [
        ("usuarios.csv", reportes.usuarios_registrados()),
        ("libros.csv", reportes.catalogo_libros()),
        ("historial_prestamos.csv", reportes.historial_prestamos()),
        ("prestamos_activos.csv", reportes.prestamos_activos()),
        ("prestamos_atrasados.csv", reportes.prestamos_atrasados()),
        ("multas_pendientes.csv", reportes.multas_pendientes()),
        ("ranking_confiabilidad.csv", reportes.ranking_usuarios()),
        ("libros_mas_prestados.csv", reportes.libros_mas_prestados()),
    ]
    for nombre, (encabezados, filas) in archivos:
        exportar_csv(app.carpeta / nombre, encabezados, filas)
    mensaje_ok(f"Se exportaron {len(archivos)} archivos CSV en: {app.carpeta}")


def guardar_ahora(app):
    app.guardar_datos()
    mensaje_ok("Datos guardados en los archivos JSON de la carpeta 'data'.")


def recargar_datos(app):
    if not confirmar(
        "Se descartarán los cambios que no estén guardados. ¿Recargar desde los archivos JSON?"
    ):
        mensaje_info("No se recargó nada.")
        return
    app.recargar()
    mensaje_ok(
        f"Datos cargados: {len(app.usuarios)} usuarios, {len(app.libros)} libros, "
        f"{len(app.prestamos)} préstamos."
    )


def cambiar_clave(app):
    actual = getpass("Contraseña actual: ")
    nueva = getpass("Contraseña nueva: ")
    repeticion = getpass("Repita la contraseña nueva: ")
    if nueva != repeticion:
        raise ReglaNegocioError("Las contraseñas nuevas no coinciden.")
    app.auth.cambiar_clave(app.sesion, actual, nueva)
    app.guardar_administradores()
    mensaje_ok("Contraseña actualizada correctamente.")


def menu_usuarios(app):
    ejecutar_menu(
        "MÓDULO USUARIOS",
        [
            ("Registrar usuario", lambda: registrar_usuario(app)),
            ("Listar usuarios", lambda: listar_usuarios(app)),
            ("Buscar usuario por nombre o correo", lambda: buscar_usuarios(app)),
            ("Ver ficha e historial de un usuario", lambda: ver_ficha_usuario(app)),
            ("Editar usuario", lambda: editar_usuario(app)),
            ("Eliminar usuario", lambda: eliminar_usuario(app)),
        ],
    )


def menu_libros(app):
    ejecutar_menu(
        "MÓDULO LIBROS",
        [
            ("Registrar libro", lambda: registrar_libro(app)),
            ("Listar catálogo completo", lambda: listar_libros(app)),
            ("Listar solo libros disponibles", lambda: listar_libros(app, True)),
            ("Buscar por título, autor o ISBN", lambda: buscar_libros(app)),
            ("Editar libro", lambda: editar_libro(app)),
            ("Eliminar libro", lambda: eliminar_libro(app)),
        ],
    )


def menu_prestamos(app):
    ejecutar_menu(
        "PRÉSTAMOS Y DEVOLUCIONES",
        [
            ("Registrar préstamo", lambda: registrar_prestamo(app)),
            ("Registrar devolución", lambda: registrar_devolucion(app)),
            ("Ver préstamos activos", lambda: ver_prestamos_activos(app)),
            ("Ver préstamos atrasados", lambda: ver_prestamos_atrasados(app)),
        ],
    )


def menu_multas(app):
    ejecutar_menu(
        "MULTAS",
        [
            ("Ver multas pendientes", lambda: ver_multas_pendientes(app)),
            ("Registrar pago de una multa", lambda: registrar_pago_multa(app)),
        ],
    )


def menu_reportes(app):
    reportes = app.reportes
    ejecutar_menu(
        "REPORTES Y EXPORTACIÓN",
        [
            ("Resumen general", lambda: mostrar_reporte(app, "RESUMEN GENERAL", reportes.resumen())),
            (
                "Ranking de usuarios más confiables",
                lambda: mostrar_reporte(
                    app,
                    "RANKING DE CONFIABILIDAD",
                    reportes.ranking_usuarios(),
                    "ranking_confiabilidad.csv",
                ),
            ),
            (
                "Libros más prestados",
                lambda: mostrar_reporte(
                    app,
                    "LIBROS MÁS PRESTADOS",
                    reportes.libros_mas_prestados(),
                    "libros_mas_prestados.csv",
                ),
            ),
            ("Préstamos activos", lambda: ver_prestamos_activos(app)),
            ("Préstamos atrasados", lambda: ver_prestamos_atrasados(app)),
            ("Multas pendientes", lambda: ver_multas_pendientes(app)),
            (
                "Historial completo de préstamos",
                lambda: mostrar_reporte(
                    app,
                    "HISTORIAL DE PRÉSTAMOS",
                    reportes.historial_prestamos(),
                    "historial_prestamos.csv",
                ),
            ),
            ("Exportar todo a CSV", lambda: exportar_todo(app)),
        ],
    )


def menu_datos(app):
    ejecutar_menu(
        "GUARDAR / CARGAR DATOS (JSON)",
        [
            ("Guardar datos ahora", lambda: guardar_ahora(app)),
            ("Recargar datos desde los archivos JSON", lambda: recargar_datos(app)),
        ],
    )


def iniciar_sesion(app):
    if app.auth.asegurar_admin_inicial():
        try:
            app.guardar_administradores()
        except PersistenciaError as error:
            mensaje_error(str(error))
        mensaje_info(
            f"Primer inicio: se creó el administrador '{USUARIO_INICIAL}' con la "
            f"contraseña '{CLAVE_INICIAL}'. Cámbiela desde el menú principal."
        )
    encabezado("INICIO DE SESIÓN")
    for intento in range(1, MAXIMO_INTENTOS_LOGIN + 1):
        usuario = input("Usuario: ").strip()
        clave = input("Contraseña: ")
        if app.auth.autenticar(usuario, clave):
            app.sesion = usuario
            mensaje_ok(f"Bienvenido, {usuario}.")
            return True
        mensaje_error(
            f"Credenciales incorrectas (intento {intento} de {MAXIMO_INTENTOS_LOGIN})."
        )
    return False


def recomendar_cambio_de_clave(app):
    if not app.auth.debe_cambiar_clave(app.sesion):
        return
    mensaje_info("Está usando la contraseña inicial, que es pública en la documentación.")
    if confirmar("¿Desea cambiarla ahora?"):
        try:
            cambiar_clave(app)
        except (ReglaNegocioError, PersistenciaError) as error:
            mensaje_error(str(error))


def menu_principal(app):
    ejecutar_menu(
        "LIBROLINK - MENÚ PRINCIPAL",
        [
            ("Usuarios", lambda: menu_usuarios(app)),
            ("Libros", lambda: menu_libros(app)),
            ("Préstamos y devoluciones", lambda: menu_prestamos(app)),
            ("Multas", lambda: menu_multas(app)),
            ("Reportes y exportación a CSV", lambda: menu_reportes(app)),
            ("Guardar / Cargar datos (JSON)", lambda: menu_datos(app)),
            ("Cambiar contraseña del administrador", lambda: cambiar_clave(app)),
        ],
        salida="Guardar y salir",
    )


def main():
    encabezado("LIBROLINK - GESTIÓN DE BIBLIOTECA COMUNITARIA")
    print(f"Multa por retraso: {formatear_pesos(MULTA_DIARIA)} COP por cada día.")
    app = Aplicacion(RUTA_DATOS)
    try:
        app.cargar_inicial()
    except ArranqueCancelado:
        mensaje_info(
            "No se modificó ningún archivo. Revise o restaure los archivos de la "
            f"carpeta '{RUTA_DATOS.name}' y vuelva a iniciar."
        )
        return 1
    except PersistenciaError as error:
        mensaje_error(str(error))
        return 1
    try:
        if not iniciar_sesion(app):
            mensaje_error("Demasiados intentos fallidos. El programa se cerrará.")
            return 1
        recomendar_cambio_de_clave(app)
        menu_principal(app)
    except (KeyboardInterrupt, EOFError):
        print("\n\nCierre solicitado. Guardando información...")
    if app.sesion is not None:
        if app.persistir():
            mensaje_ok("Información guardada. ¡Hasta pronto!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
