from services.errores import ReglaNegocioError


class Libro:
    def __init__(self, id_libro, titulo, autor, isbn="", stock_total=1, stock_disponible=None):
        self.id_libro = id_libro
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.stock_total = int(stock_total)
        if stock_disponible is None:
            stock_disponible = self.stock_total
        self.stock_disponible = int(stock_disponible)

    @property
    def disponible(self):
        return self.stock_disponible > 0

    @property
    def estado(self):
        return "DISPONIBLE" if self.disponible else "PRESTADO"

    @property
    def ejemplares_prestados(self):
        return self.stock_total - self.stock_disponible

    def prestar(self):
        if not self.disponible:
            raise ReglaNegocioError(
                f"No hay ejemplares disponibles de '{self.titulo}'."
            )
        self.stock_disponible -= 1

    def devolver(self):
        if self.stock_disponible < self.stock_total:
            self.stock_disponible += 1

    def to_dict(self):
        return {
            "id_libro": self.id_libro,
            "titulo": self.titulo,
            "autor": self.autor,
            "isbn": self.isbn,
            "stock_total": self.stock_total,
            "stock_disponible": self.stock_disponible,
        }

    @classmethod
    def from_dict(cls, data):
        if "stock_total" in data:
            stock_total = int(data["stock_total"])
            stock_disponible = int(data.get("stock_disponible", stock_total))
        else:
            stock_total = 1
            stock_disponible = 1 if data.get("disponible", True) else 0
        return cls(
            id_libro=data["id_libro"],
            titulo=data["titulo"],
            autor=data["autor"],
            isbn=data.get("isbn", ""),
            stock_total=stock_total,
            stock_disponible=stock_disponible,
        )
