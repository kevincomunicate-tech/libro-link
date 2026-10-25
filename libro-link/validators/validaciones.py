import re
import unicodedata

from services.errores import ValidacionError

ROLES_VALIDOS = ("regular", "premium")
LONGITUD_MINIMA_CLAVE = 6
LONGITUD_MAXIMA_CLAVE = 64
STOCK_MAXIMO = 1000

PATRON_EMAIL = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$"
)
PATRON_ENTERO = re.compile(r"^[+-]?[0-9]+$")


def limpiar(valor):
    if valor is None:
        return ""
    return " ".join(str(valor).split())


def normalizar_texto(valor):
    descompuesto = unicodedata.normalize("NFKD", limpiar(valor))
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return sin_tildes.lower()


def validar_obligatorio(valor, campo):
    texto = limpiar(valor)
    if not texto:
        raise ValidacionError(f"El campo '{campo}' es obligatorio.")
    return texto


def validar_longitud(texto, campo, minimo, maximo):
    if len(texto) < minimo:
        raise ValidacionError(
            f"El campo '{campo}' debe tener al menos {minimo} caracteres."
        )
    if len(texto) > maximo:
        raise ValidacionError(
            f"El campo '{campo}' no puede superar los {maximo} caracteres."
        )
    return texto


def validar_nombre(valor):
    texto = validar_obligatorio(valor, "nombre")
    validar_longitud(texto, "nombre", 2, 80)
    solo_permitidos = all(c.isalpha() or c in " '.-" for c in texto)
    if not solo_permitidos or not any(c.isalpha() for c in texto):
        raise ValidacionError(
            "El nombre solo puede contener letras, espacios, apóstrofes, puntos y guiones."
        )
    return texto


def validar_email(valor):
    texto = validar_obligatorio(valor, "correo").lower()
    validar_longitud(texto, "correo", 5, 120)
    if not PATRON_EMAIL.match(texto):
        raise ValidacionError(
            "El correo no tiene un formato válido (ejemplo: nombre@dominio.com)."
        )
    return texto


def validar_rol(valor):
    texto = normalizar_texto(validar_obligatorio(valor, "rol"))
    if texto not in ROLES_VALIDOS:
        raise ValidacionError("El rol debe ser 'regular' o 'premium'.")
    return texto


def validar_titulo(valor):
    texto = validar_obligatorio(valor, "título")
    return validar_longitud(texto, "título", 1, 150)


def validar_autor(valor):
    texto = validar_obligatorio(valor, "autor")
    return validar_longitud(texto, "autor", 2, 100)


def validar_isbn(valor):
    texto = validar_obligatorio(valor, "ISBN")
    compacto = texto.replace("-", "").replace(" ", "").upper()
    if len(compacto) == 13 and compacto.isascii() and compacto.isdigit():
        return compacto
    if (
        len(compacto) == 10
        and compacto[:9].isascii()
        and compacto[:9].isdigit()
        and (compacto[9].isdigit() or compacto[9] == "X")
        and compacto[9].isascii()
    ):
        return compacto
    raise ValidacionError(
        "El ISBN debe tener 10 o 13 dígitos (se permiten guiones o espacios)."
    )


def validar_entero(valor, campo, minimo, maximo):
    texto = limpiar(valor)
    if not texto:
        raise ValidacionError(f"El campo '{campo}' es obligatorio.")
    if not PATRON_ENTERO.match(texto):
        raise ValidacionError(f"El campo '{campo}' debe ser un número entero.")
    numero = int(texto)
    if numero < minimo or numero > maximo:
        raise ValidacionError(
            f"El campo '{campo}' debe estar entre {minimo} y {maximo}."
        )
    return numero


def validar_stock(valor):
    return validar_entero(valor, "ejemplares", 1, STOCK_MAXIMO)


def validar_termino_busqueda(valor):
    texto = validar_obligatorio(valor, "término de búsqueda")
    return validar_longitud(texto, "término de búsqueda", 1, 80)


def validar_clave(valor):
    if valor is None or not str(valor).strip():
        raise ValidacionError("La contraseña es obligatoria.")
    texto = str(valor)
    if len(texto) < LONGITUD_MINIMA_CLAVE:
        raise ValidacionError(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA_CLAVE} caracteres."
        )
    if len(texto) > LONGITUD_MAXIMA_CLAVE:
        raise ValidacionError(
            f"La contraseña no puede superar los {LONGITUD_MAXIMA_CLAVE} caracteres."
        )
    return texto
