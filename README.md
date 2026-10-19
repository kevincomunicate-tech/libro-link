# LibroLink
Sistema de consola para administrar usuarios, libros, préstamos y devoluciones de una biblioteca comunitaria.

## Requisitos
Python 3.10 o superior. No requiere dependencias externas.

## Ejecutar
Desde la carpeta `librolink`:
```bash
python main.py
```

## Pruebas
```bash
python -m unittest discover -s tests -v
```

Los datos se guardan en `data/` como JSON. Los valores iniciales de reglas son: usuario regular (3 préstamos, 14 días), premium (5 préstamos, 21 días), multa 1.00 por día tarde y puntaje inicial 50. Cambien estas reglas según lo que acuerde el equipo.
