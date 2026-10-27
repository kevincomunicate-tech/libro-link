from models.libro import Libro
from services.errores import EntidadNoEncontradaError, ReglaNegocioError
from services.utilidades import generar_id, orden_natural
from validators.validaciones import (
    normalizar_texto,
    validar_autor,
    validar_isbn,
    validar_stock,
    validar_termino_busqueda,
    validar_titulo,
)


class LibroService:
    def __init__(self, libros, prestamos=None):
        self.libros = libros
        self.prestamos = prestamos if prestamos is not None else []

    def validar_isbn_disponible(self, valor, excluir_id=None):
        isbn = validar_isbn(valor)
        for libro in self.libros:
            if libro.id_libro == excluir_id:
                continue
            if libro.isbn == isbn:
                raise ReglaNegocioError(
                    f"El ISBN {isbn} ya está registrado para '{libro.titulo}'."
                )
        return isbn

    def registrar(self, titulo, autor, isbn, stock):
        titulo = validar_titulo(titulo)
        autor = validar_autor(autor)
        isbn = self.validar_isbn_disponible(isbn)
        stock = validar_stock(stock)
        identificadores = [libro.id_libro for libro in self.libros]
        identificadores += [p.id_libro for p in self.prestamos]
        libro = Libro(generar_id("L", identificadores), titulo, autor, isbn, stock)
        self.libros.append(libro)
        return libro

    def obtener(self, id_libro):
        clave = str(id_libro).strip().upper()
        for libro in self.libros:
            if str(libro.id_libro).upper() == clave:
                return libro
        raise EntidadNoEncontradaError(f"No existe un libro con ID '{id_libro}'.")

    def listar(self, solo_disponibles=False):
        libros = [l for l in self.libros if l.disponible or not solo_disponibles]
        return sorted(libros, key=lambda l: orden_natural(l.id_libro))

    def buscar(self, termino):
        termino = normalizar_texto(validar_termino_busqueda(termino))
        termino_isbn = termino.replace("-", "").replace(" ", "")
        coincidencias = []
        for libro in self.libros:
            en_titulo = termino in normalizar_texto(libro.titulo)
            en_autor = termino in normalizar_texto(libro.autor)
            en_isbn = bool(termino_isbn) and termino_isbn in str(libro.isbn).lower()
            if en_titulo or en_autor or en_isbn:
                coincidencias.append(libro)
        return sorted(coincidencias, key=lambda l: orden_natural(l.id_libro))

    def actualizar(self, id_libro, titulo=None, autor=None, isbn=None, stock=None):
        libro = self.obtener(id_libro)
        nuevo_titulo = validar_titulo(titulo) if titulo is not None else libro.titulo
        nuevo_autor = validar_autor(autor) if autor is not None else libro.autor
        nuevo_isbn = (
            self.validar_isbn_disponible(isbn, excluir_id=libro.id_libro)
            if isbn is not None
            else libro.isbn
        )
        nuevo_stock = validar_stock(stock) if stock is not None else libro.stock_total
        prestados = libro.ejemplares_prestados
        if nuevo_stock < prestados:
            raise ReglaNegocioError(
                f"No se puede reducir a {nuevo_stock} ejemplares: "
                f"hay {prestados} actualmente prestados."
            )
        libro.titulo = nuevo_titulo
        libro.autor = nuevo_autor
        libro.isbn = nuevo_isbn
        libro.stock_total = nuevo_stock
        libro.stock_disponible = nuevo_stock - prestados
        return libro

    def eliminar(self, id_libro):
        libro = self.obtener(id_libro)
        con_prestamo_activo = any(
            p.activo and p.id_libro == libro.id_libro for p in self.prestamos
        )
        if con_prestamo_activo or libro.ejemplares_prestados > 0:
            raise ReglaNegocioError(
                f"No se puede eliminar '{libro.titulo}': tiene ejemplares prestados."
            )
        self.libros.remove(libro)
        return libro
