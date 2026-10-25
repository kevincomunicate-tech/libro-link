# Plan técnico

## Requisitos
- Python 3.9 o superior (probado con Python 3.13).
- Sin librerías externas ni bases de datos: solo biblioteca estándar, archivos JSON y CSV.

## Cómo ejecutar
Desde la carpeta raíz del proyecto:

```
python main.py
```

En Windows también funciona `py main.py`. Credenciales del primer inicio: usuario `admin`, contraseña `admin123`.

## Cómo probar
```
python -m unittest -v
```

## Arquitectura

```
main.py                      arranque, login y menús
models/
  usuario.py                 Usuario, UsuarioRegular, UsuarioPremium, puntaje de confiabilidad
  libro.py                   Libro con ejemplares y estado DISPONIBLE / PRESTADO
  prestamo.py                Prestamo, cálculo de retraso y multa (MULTA_DIARIA = 2000)
services/
  usuario_service.py         CRUD y búsqueda de usuarios
  libro_service.py           CRUD y búsqueda de libros
  prestamo_service.py        préstamos, devoluciones, pago de multas, deudas
  reporte_service.py         reportes y datasets para consola y CSV
  auth_service.py            administrador y contraseña con hash
  errores.py                 excepciones del dominio
  utilidades.py              IDs consecutivos y formato de pesos
persistence/
  json_repository.py         carga y guardado atómico de JSON, respaldo de archivos dañados
  csv_exporter.py            exportación a CSV (UTF-8 con BOM, abre bien en Excel)
validators/
  validaciones.py            validación de nombre, correo, ISBN, stock, contraseña
ui/
  consola.py                 tablas, preguntas, menús
data/                        archivos JSON y CSV generados al usar el programa
tests/                       pruebas automáticas y plan de pruebas
```

## Archivos de datos
| Archivo | Contenido |
|---------|-----------|
| `data/usuarios.json` | usuarios con rol y puntaje |
| `data/libros.json` | libros con ISBN y ejemplares |
| `data/prestamos.json` | préstamos, devoluciones y multas |
| `data/admin.json` | administrador con contraseña cifrada |
| `data/*.csv` | reportes exportados |

Estos archivos se crean solos la primera vez y están en `.gitignore`.

## Historias de usuario cubiertas
| HU | Dónde |
|----|-------|
| HU-01 Registrar usuario | `usuario_service.registrar`, menú Usuarios |
| HU-02 Listar y buscar usuarios | `usuario_service.buscar`, menú Usuarios |
| HU-03 Registrar libro | `libro_service.registrar`, menú Libros |
| HU-04 Listar y buscar libros | `libro_service.buscar`, menú Libros |
| HU-05 Menú principal | `main.menu_principal` |
| HU-06 Persistencia en JSON | `persistence/json_repository.py` |
| HU-07 Validaciones de entrada | `validators/validaciones.py` |
| HU-08 a HU-12 Préstamos, devoluciones, puntaje, activos y atrasados | `prestamo_service`, menú Préstamos y devoluciones |
| HU-13 a HU-15 Reportes, CSV, búsquedas | `reporte_service`, `csv_exporter`, menú Reportes |
| HU-16 Errores y archivos | `json_repository` y arranque en `main.Aplicacion` |

Además se agregó el CRUD completo (editar y eliminar usuarios y libros) y la gestión de multas.
