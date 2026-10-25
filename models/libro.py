class Libro:
    def __init__(self, id_libro: str, titulo: str, autor: str, disponible: bool = True):
        self.id_libro = id_libro
        self.titulo = titulo
        self.autor = autor
        self.disponible = disponible

    def to_dict(self) -> dict:
        """Convierte la instancia de Libro a un diccionario para JSON."""
        return {
            "id_libro": self.id_libro,
            "titulo": self.titulo,
            "autor": self.autor,
            "disponible": self.disponible
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Crea una instancia de Libro a partir de un diccionario."""
        return cls(
            id_libro=data.get("id_libro"),
            titulo=data.get("titulo"),
            autor=data.get("autor"),
            disponible=data.get("disponible", True)
        )