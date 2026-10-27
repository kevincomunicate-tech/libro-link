# Decisiones de diseño

## Multa por retraso
- Cada día de retraso cuesta **$2.000 COP**. La constante está en `models/prestamo.py` (`MULTA_DIARIA`).
- Un préstamo vence al cumplirse los días de su rol (regular 14, premium 21). Devolver el mismo día del vencimiento no genera multa.
- Mientras el libro no se devuelve, la multa **crece cada día** (se calcula al consultar, no se guarda).
- Al registrar la devolución la multa **se congela** con los días de retraso de ese momento y queda pendiente hasta que el administrador registra el pago.
- Un usuario con préstamos atrasados o multas pendientes **no puede pedir nuevos libros** hasta devolver y pagar.
- Los montos se manejan como enteros (pesos colombianos no usan centavos).

## Valor agregado: puntaje de confiabilidad
- Cada usuario empieza con 50 puntos (rango 0 a 100).
- Devolución a tiempo: +2. Devolución con retraso: -5.
- Niveles: Excelente (80+), Bueno (60+), Regular (40+), En riesgo (menos de 40).
- Se muestra en la ficha del usuario y en el ranking de usuarios más confiables, que se puede exportar a CSV.

## Roles de usuario
| Rol | Libros simultáneos | Días de préstamo |
|-----|--------------------|------------------|
| Regular | 3 | 14 |
| Premium | 5 | 21 |

## Persistencia
- JSON para la información del sistema: `usuarios.json`, `libros.json`, `prestamos.json` y `admin.json`, todos en `data/`.
- CSV solo para exportar reportes (se guardan también en `data/`).
- El guardado es automático después de cada cambio y también se puede forzar desde el menú. Se escribe primero en un archivo `.tmp` y luego se reemplaza, para que un corte a mitad de escritura no deje un JSON roto.
- Si un archivo está dañado el programa no lo borra ni lo sobrescribe: avisa y ofrece guardarlo como `*.danado-FECHA` para continuar con datos vacíos de esa entidad.
- Los CSV prefijan con una comilla los textos que empiezan por `=`, `+`, `-` o `@` para que Excel no los interprete como fórmulas.

## Administrador
- El primer inicio crea el usuario `admin` con contraseña `admin123` y recomienda cambiarla.
- La contraseña se guarda con sal y PBKDF2-SHA256 (200.000 iteraciones), nunca en texto plano.
- Tras 3 intentos fallidos el programa se cierra.

## Integridad de datos
- Los IDs (`U001`, `L001`, `P001`) son consecutivos y **no se reutilizan** aunque se elimine el último registro, porque el historial de préstamos los referencia.
- No se puede eliminar un usuario con préstamos activos o multas pendientes, ni un libro con ejemplares prestados.
- No se puede reducir el número de ejemplares de un libro por debajo de los que están prestados.
- El correo del usuario y el ISBN del libro son únicos.
- Los reportes toleran usuarios o libros eliminados mostrando el ID con la marca "(eliminado)".

## Validaciones (HU-07)
- Campos obligatorios, longitudes, nombre solo con letras, correo con formato válido, ISBN de 10 o 13 dígitos (se aceptan guiones y espacios, y la X final del ISBN-10), ejemplares entre 1 y 1000.
- En los formularios el error se muestra y se vuelve a pedir el dato sin perder lo ya ingresado. Escribir `/cancelar` abandona la operación.
- Las búsquedas ignoran mayúsculas y tildes.

## Estructura de capas
- `models`: entidades y reglas propias (puntaje, multa, estado del libro).
- `services`: reglas de negocio, sin entrada ni salida por consola.
- `persistence`: lectura y escritura de JSON y exportación CSV.
- `validators`: validaciones de entrada reutilizables.
- `ui`: utilidades de consola (tablas, preguntas, menús).
- `main.py`: arranque, inicio de sesión y menús.
