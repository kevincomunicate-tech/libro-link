import csv
from pathlib import Path

from services.errores import PersistenciaError

PREFIJOS_PELIGROSOS = ("=", "+", "-", "@", "\t", "\r")


def _seguro(valor):
    if valor is None:
        return ""
    if isinstance(valor, str) and valor.startswith(PREFIJOS_PELIGROSOS):
        return "'" + valor
    return valor


def exportar_csv(ruta, encabezados, filas):
    ruta = Path(ruta)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(encabezados)
            for fila in filas:
                escritor.writerow([_seguro(valor) for valor in fila])
    except OSError as error:
        raise PersistenciaError(
            f"No se pudo exportar el archivo '{ruta.name}': {error}"
        ) from error
    return ruta
