from datetime import date

from services.errores import PersistenciaError, ReglaNegocioError
from services.utilidades import formatear_pesos

COMANDO_CANCELAR = "/cancelar"
ANCHO_MAXIMO_COLUMNA = 38


class OperacionCancelada(Exception):
    pass


def mensaje_ok(texto):
    print(f"\n[OK] {texto}")


def mensaje_error(texto):
    print(f"\n[ERROR] {texto}")


def mensaje_info(texto):
    print(f"\n[INFO] {texto}")


def encabezado(texto):
    linea = "=" * (len(texto) + 8)
    print(f"\n{linea}\n    {texto}\n{linea}")


def leer(texto):
    respuesta = input(texto)
    if respuesta.strip().lower() == COMANDO_CANCELAR:
        raise OperacionCancelada()
    return respuesta


def aviso_cancelar():
    print(f"(Escriba {COMANDO_CANCELAR} en cualquier momento para abandonar la operación.)")


def pedir(etiqueta, validador, actual=None):
    sufijo = f" [{actual}]" if actual not in (None, "") else ""
    while True:
        bruto = leer(f"{etiqueta}{sufijo}: ")
        if actual is not None and not bruto.strip():
            return actual
        try:
            return validador(bruto)
        except ReglaNegocioError as error:
            mensaje_error(str(error))


def confirmar(pregunta):
    while True:
        respuesta = input(f"{pregunta} (s/n): ").strip().lower()
        if respuesta in ("s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("Responda con 's' para sí o 'n' para no.")


def formatear_celda(encabezado_columna, valor):
    if valor is None:
        return "-"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, int) and encabezado_columna.endswith("(COP)"):
        return formatear_pesos(valor)
    return str(valor)


def _recortar(texto, limite):
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3] + "..."


def tabla(encabezados, filas, limite=ANCHO_MAXIMO_COLUMNA):
    celdas = [
        [
            _recortar(formatear_celda(titulo, valor), limite)
            for titulo, valor in zip(encabezados, fila)
        ]
        for fila in filas
    ]
    anchos = [
        max([len(titulo)] + [len(fila[indice]) for fila in celdas])
        for indice, titulo in enumerate(encabezados)
    ]
    separador = "-+-".join("-" * ancho for ancho in anchos)
    print()
    print(" | ".join(titulo.ljust(ancho) for titulo, ancho in zip(encabezados, anchos)))
    print(separador)
    for fila in celdas:
        print(" | ".join(valor.ljust(ancho) for valor, ancho in zip(fila, anchos)))


def ejecutar_menu(titulo, opciones, salida="Volver"):
    while True:
        encabezado(titulo)
        for numero, (texto, _) in enumerate(opciones, start=1):
            print(f"  {numero}. {texto}")
        print(f"  0. {salida}")
        eleccion = input("\nSeleccione una opción: ").strip()
        if eleccion == "0":
            return
        if not (eleccion.isascii() and eleccion.isdigit()) or not 1 <= int(eleccion) <= len(opciones):
            mensaje_error("Opción no válida. Ingrese uno de los números del menú.")
            continue
        accion = opciones[int(eleccion) - 1][1]
        try:
            accion()
        except OperacionCancelada:
            mensaje_info("Operación cancelada.")
        except (ReglaNegocioError, PersistenciaError) as error:
            mensaje_error(str(error))
