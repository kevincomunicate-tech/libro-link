import json
import os
from datetime import datetime
from pathlib import Path

from services.errores import PersistenciaError


class JsonRepository:
    def __init__(self, ruta, factory=dict):
        self.ruta = Path(ruta)
        self.factory = factory

    def existe(self):
        return self.ruta.exists()

    def cargar(self):
        if not self.ruta.exists():
            return []
        try:
            contenido = self.ruta.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise PersistenciaError(
                f"No se pudo leer el archivo '{self.ruta.name}': {error}"
            ) from error
        if not contenido.strip():
            return []
        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError as error:
            raise PersistenciaError(
                f"El archivo '{self.ruta.name}' está dañado "
                f"(línea {error.lineno}, columna {error.colno})."
            ) from error
        if not isinstance(datos, list):
            raise PersistenciaError(
                f"El archivo '{self.ruta.name}' debe contener una lista de registros."
            )
        try:
            return [self.factory(registro) for registro in datos]
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise PersistenciaError(
                f"El archivo '{self.ruta.name}' contiene registros inválidos: {error!r}"
            ) from error

    def guardar(self, elementos):
        registros = [
            elemento.to_dict() if hasattr(elemento, "to_dict") else elemento
            for elemento in elementos
        ]
        temporal = self.ruta.with_name(self.ruta.name + ".tmp")
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            with open(temporal, "w", encoding="utf-8") as archivo:
                json.dump(registros, archivo, ensure_ascii=False, indent=2)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, self.ruta)
        except (OSError, TypeError, ValueError) as error:
            try:
                temporal.unlink()
            except OSError:
                pass
            raise PersistenciaError(
                f"No se pudo guardar el archivo '{self.ruta.name}': {error}"
            ) from error

    def respaldar(self):
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = self.ruta.with_name(f"{self.ruta.name}.danado-{marca}")
        try:
            os.replace(self.ruta, destino)
        except OSError as error:
            raise PersistenciaError(
                f"No se pudo respaldar el archivo '{self.ruta.name}': {error}"
            ) from error
        return destino
