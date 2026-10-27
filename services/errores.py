class ReglaNegocioError(Exception):
    pass


class ValidacionError(ReglaNegocioError):
    pass


class EntidadNoEncontradaError(ReglaNegocioError):
    pass


class PersistenciaError(Exception):
    pass
