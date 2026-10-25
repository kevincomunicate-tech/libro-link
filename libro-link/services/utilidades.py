def generar_id(prefijo, ids_existentes):
    mayor = 0
    for identificador in ids_existentes:
        texto = str(identificador or "")
        if texto.startswith(prefijo) and texto[len(prefijo):].isdigit():
            mayor = max(mayor, int(texto[len(prefijo):]))
    return f"{prefijo}{mayor + 1:03d}"


def orden_natural(identificador):
    texto = str(identificador or "")
    return (len(texto), texto)


def formatear_pesos(valor):
    entero = int(valor)
    signo = "-" if entero < 0 else ""
    return f"{signo}${abs(entero):,}".replace(",", ".")


def plural_dias(cantidad):
    return "1 día" if cantidad == 1 else f"{cantidad} días"


def plural_ejemplares(cantidad):
    return "1 ejemplar" if cantidad == 1 else f"{cantidad} ejemplares"
