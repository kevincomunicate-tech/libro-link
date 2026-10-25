class Usuario:
    def __init__(self, id_usuario: str, nombre: str, email: str):
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.email = email

    def to_dict(self) -> dict:
        """Convierte la instancia de Usuario a un diccionario para JSON."""
        return {
            "id_usuario": self.id_usuario,
            "nombre": self.nombre,
            "email": self.email
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Crea una instancia de Usuario a partir de un diccionario."""
        return cls(
            id_usuario=data.get("id_usuario"),
            nombre=data.get("nombre"),
            email=data.get("email")
        )