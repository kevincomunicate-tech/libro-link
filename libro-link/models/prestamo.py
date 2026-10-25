from datetime import date

MULTA_DIARIA = 2000


class Prestamo:
    def __init__(
        self,
        id_prestamo,
        id_usuario,
        id_libro,
        fecha_prestamo,
        fecha_vencimiento,
        fecha_devolucion=None,
        multa=0,
        multa_pagada=False,
        fecha_pago=None,
    ):
        self.id_prestamo = id_prestamo
        self.id_usuario = id_usuario
        self.id_libro = id_libro
        self.fecha_prestamo = fecha_prestamo
        self.fecha_vencimiento = fecha_vencimiento
        self.fecha_devolucion = fecha_devolucion
        self.multa = int(multa)
        self.multa_pagada = bool(multa_pagada)
        self.fecha_pago = fecha_pago

    @property
    def id(self):
        return self.id_prestamo

    @property
    def activo(self):
        return self.fecha_devolucion is None

    def dias_retraso(self, hoy=None):
        referencia = self.fecha_devolucion or hoy or date.today()
        return max(0, (referencia - self.fecha_vencimiento).days)

    def esta_atrasado(self, hoy=None):
        return self.activo and self.dias_retraso(hoy) > 0

    def multa_acumulada(self, hoy=None):
        if self.activo:
            return self.dias_retraso(hoy) * MULTA_DIARIA
        return self.multa

    def multa_pendiente(self, hoy=None):
        if self.multa_pagada:
            return 0
        return self.multa_acumulada(hoy)

    def cerrar(self, fecha_devolucion):
        self.fecha_devolucion = fecha_devolucion
        self.multa = self.dias_retraso() * MULTA_DIARIA

    def pagar(self, fecha_pago):
        self.multa_pagada = True
        self.fecha_pago = fecha_pago

    def to_dict(self):
        return {
            "id_prestamo": self.id_prestamo,
            "id_usuario": self.id_usuario,
            "id_libro": self.id_libro,
            "fecha_prestamo": self.fecha_prestamo.isoformat(),
            "fecha_vencimiento": self.fecha_vencimiento.isoformat(),
            "fecha_devolucion": (
                self.fecha_devolucion.isoformat() if self.fecha_devolucion else None
            ),
            "multa": self.multa,
            "multa_pagada": self.multa_pagada,
            "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None,
        }

    @classmethod
    def from_dict(cls, data):
        fecha_devolucion = data.get("fecha_devolucion")
        fecha_pago = data.get("fecha_pago")
        return cls(
            id_prestamo=data["id_prestamo"],
            id_usuario=data["id_usuario"],
            id_libro=data["id_libro"],
            fecha_prestamo=date.fromisoformat(data["fecha_prestamo"]),
            fecha_vencimiento=date.fromisoformat(data["fecha_vencimiento"]),
            fecha_devolucion=(
                date.fromisoformat(fecha_devolucion) if fecha_devolucion else None
            ),
            multa=int(data.get("multa", 0)),
            multa_pagada=bool(data.get("multa_pagada", False)),
            fecha_pago=date.fromisoformat(fecha_pago) if fecha_pago else None,
        )
