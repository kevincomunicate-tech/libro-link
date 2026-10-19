class ReglaNegocioError(Exception):
    """Una operación no cumple las reglas del sistema."""


class EntidadNoEncontradaError(Exception):
    """No se encontró la entidad solicitada."""


class PersistenciaError(Exception):
    """Error al leer o guardar información persistente."""
