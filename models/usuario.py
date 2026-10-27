PUNTAJE_INICIAL = 50
PUNTAJE_MINIMO = 0
PUNTAJE_MAXIMO = 100
BONO_DEVOLUCION_A_TIEMPO = 2
PENALIZACION_DEVOLUCION_TARDIA = 5


class Usuario:
    ROL = "regular"
    LIMITE_PRESTAMOS = 3
    DIAS_PRESTAMO = 14

    def __init__(self, id_usuario, nombre, email="", puntaje_confiabilidad=PUNTAJE_INICIAL):
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.email = email
        self.puntaje_confiabilidad = int(puntaje_confiabilidad)

    @property
    def rol(self):
        return self.ROL

    def limite_prestamos(self):
        return self.LIMITE_PRESTAMOS

    def dias_prestamo(self):
        return self.DIAS_PRESTAMO

    def registrar_devolucion_a_tiempo(self):
        nuevo = self.puntaje_confiabilidad + BONO_DEVOLUCION_A_TIEMPO
        self.puntaje_confiabilidad = min(PUNTAJE_MAXIMO, nuevo)

    def registrar_devolucion_tardia(self):
        nuevo = self.puntaje_confiabilidad - PENALIZACION_DEVOLUCION_TARDIA
        self.puntaje_confiabilidad = max(PUNTAJE_MINIMO, nuevo)

    def nivel_confiabilidad(self):
        if self.puntaje_confiabilidad >= 80:
            return "Excelente"
        if self.puntaje_confiabilidad >= 60:
            return "Bueno"
        if self.puntaje_confiabilidad >= 40:
            return "Regular"
        return "En riesgo"

    def to_dict(self):
        return {
            "id_usuario": self.id_usuario,
            "nombre": self.nombre,
            "email": self.email,
            "rol": self.ROL,
            "puntaje_confiabilidad": self.puntaje_confiabilidad,
        }

    @classmethod
    def from_dict(cls, data):
        return crear_usuario(
            data.get("rol", "regular"),
            data["id_usuario"],
            data["nombre"],
            data.get("email", ""),
            data.get("puntaje_confiabilidad", PUNTAJE_INICIAL),
        )


class UsuarioRegular(Usuario):
    ROL = "regular"
    LIMITE_PRESTAMOS = 3
    DIAS_PRESTAMO = 14


class UsuarioPremium(Usuario):
    ROL = "premium"
    LIMITE_PRESTAMOS = 5
    DIAS_PRESTAMO = 21


CLASES_POR_ROL = {
    UsuarioRegular.ROL: UsuarioRegular,
    UsuarioPremium.ROL: UsuarioPremium,
}


def crear_usuario(rol, id_usuario, nombre, email="", puntaje_confiabilidad=PUNTAJE_INICIAL):
    clase = CLASES_POR_ROL.get(str(rol).strip().lower())
    if clase is None:
        raise ValueError(f"Rol de usuario desconocido: {rol!r}")
    return clase(id_usuario, nombre, email, puntaje_confiabilidad)
