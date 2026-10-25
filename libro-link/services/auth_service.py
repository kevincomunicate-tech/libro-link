import hashlib
import hmac
import os

from services.errores import ReglaNegocioError
from validators.validaciones import validar_clave

USUARIO_INICIAL = "admin"
CLAVE_INICIAL = "admin123"
ITERACIONES = 200_000
SAL_FICTICIA = "00" * 16


def registro_admin_desde_dict(data):
    sal = str(data["sal"])
    bytes.fromhex(sal)
    return {
        "usuario": str(data["usuario"]),
        "sal": sal,
        "hash": str(data["hash"]),
        "debe_cambiar": bool(data.get("debe_cambiar", False)),
    }


def _calcular_hash(clave, sal_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(sal_hex), ITERACIONES
    ).hex()


def _crear_registro(usuario, clave, debe_cambiar):
    sal = os.urandom(16).hex()
    return {
        "usuario": usuario,
        "sal": sal,
        "hash": _calcular_hash(clave, sal),
        "debe_cambiar": debe_cambiar,
    }


class AuthService:
    def __init__(self, administradores):
        self.administradores = administradores

    def asegurar_admin_inicial(self):
        if self.administradores:
            return False
        self.administradores.append(
            _crear_registro(USUARIO_INICIAL, CLAVE_INICIAL, debe_cambiar=True)
        )
        return True

    def _buscar(self, usuario):
        clave = str(usuario).strip().lower()
        for registro in self.administradores:
            if registro["usuario"].lower() == clave:
                return registro
        return None

    def autenticar(self, usuario, clave):
        registro = self._buscar(usuario)
        sal = registro["sal"] if registro else SAL_FICTICIA
        calculado = _calcular_hash(str(clave), sal)
        esperado = registro["hash"] if registro else ""
        if registro and hmac.compare_digest(calculado, esperado):
            return registro
        return None

    def debe_cambiar_clave(self, usuario):
        registro = self._buscar(usuario)
        return bool(registro and registro["debe_cambiar"])

    def cambiar_clave(self, usuario, clave_actual, clave_nueva):
        registro = self.autenticar(usuario, clave_actual)
        if registro is None:
            raise ReglaNegocioError("La contraseña actual es incorrecta.")
        clave_nueva = validar_clave(clave_nueva)
        if clave_nueva == clave_actual:
            raise ReglaNegocioError(
                "La nueva contraseña debe ser distinta de la actual."
            )
        registro["sal"] = os.urandom(16).hex()
        registro["hash"] = _calcular_hash(clave_nueva, registro["sal"])
        registro["debe_cambiar"] = False
        return registro
