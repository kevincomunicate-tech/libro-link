# LibroLink
Sistema de Gestión de Préstamos Bibliotecarios Comunitarios

## ¿Qué es este proyecto?

LibroLink es una aplicación de consola en Python que permite administrar una biblioteca comunitaria.  
Con ella se pueden registrar usuarios y libros, realizar préstamos y devoluciones, aplicar reglas de negocio, calcular un puntaje de confiabilidad de los usuarios y generar reportes.

El sistema guarda la información en archivos JSON para que no se pierda al cerrar el programa, y permite exportar reportes en formato CSV.

No usa bases de datos, ni interfaces gráficas, ni frameworks externos. Todo funciona desde la terminal.

---

## Objetivo del producto (Product Goal)

Permitir a una biblioteca comunitaria registrar, consultar, prestar y devolver libros de forma confiable, aplicar reglas de negocio (límites de préstamos, fechas y puntaje de confiabilidad), generar reportes útiles y conservar la información entre ejecuciones.

---

## Valor agregado del proyecto

Además de las funcionalidades básicas, el sistema incluye un **puntaje de confiabilidad** para cada usuario:

- La devolución a tiempo sube el puntaje.
- La devolución con retraso baja el puntaje.
- Se puede generar un ranking de los usuarios más confiables.

Esto es lógica pura (sin parte visual) y le da un diferenciador claro al proyecto.

---

## Roles del equipo

Todos somos Developers. Además:

| Integrante | Rol adicional     | Responsabilidad principal                  |
|------------|-------------------|--------------------------------------------|
| Integrante A | Product Owner   | Priorizar el backlog y validar el valor    |
| Integrante B | Scrum Master    | Facilitar el proceso y remover impedimentos|
| Integrante C | Developer       | Desarrollo, pruebas e integración          |

Cualquier integrante debe poder explicar cualquier parte del proyecto.

---

## Estructura del proyecto (a crear)
librolink/
├── main.py
├── models/
│   ├── usuario.py
│   ├── libro.py
│   └── prestamo.py
├── services/
│   ├── usuario_service.py
│   ├── libro_service.py
│   ├── prestamo_service.py
│   └── reporte_service.py
├── persistence/
│   ├── json_repository.py
│   └── csv_exporter.py
├── validators/
│   └── validaciones.py
├── data/
├── tests/
└── docs

---

## Plan de trabajo por sprints

Vamos a trabajar en **3 sprints**. Cada sprint debe entregar un incremento funcional (algo que se pueda probar).

### Sprint 1 – Fundación
**Objetivo:** Tener el esqueleto de la aplicación funcionando.

**Qué se debe lograr al final de este sprint:**
- Menú principal navegable
- Registrar usuarios
- Listar y buscar usuarios
- Registrar libros
- Listar y buscar libros
- Guardar y cargar la información en archivos JSON
- Validaciones básicas de entrada (que el programa no se caiga)

**Historias que entran en este sprint:**
- HU-01 Registrar usuario
- HU-02 Listar y buscar usuarios
- HU-03 Registrar libro
- HU-04 Listar y buscar libros
- HU-05 Menú principal
- HU-06 Persistencia en JSON
- HU-07 Validaciones de entrada

**Resultado esperado:**  
Se puede abrir el programa, registrar varios usuarios y libros, cerrarlo y al volver a abrirlo la información sigue ahí.

---

### Sprint 2 – Núcleo de negocio
**Objetivo:** Poder prestar y devolver libros aplicando las reglas del negocio.

**Qué se debe lograr al final de este sprint:**
- Registrar un préstamo (validando que el libro esté disponible y que el usuario no supere su límite)
- Registrar una devolución
- Calcular si la devolución fue a tiempo o con retraso
- Actualizar el puntaje de confiabilidad del usuario
- Consultar préstamos activos
- Consultar préstamos atrasados
- Cambiar el estado del libro (disponible / prestado)

**Historias que entran en este sprint:**
- HU-08 Registrar préstamo
- HU-09 Registrar devolución
- HU-10 Consultar préstamos activos
- HU-11 Calcular y actualizar puntaje de confiabilidad
- HU-12 Consultar préstamos atrasados

**Resultado esperado:**  
Se puede prestar un libro a un usuario, devolverlo, ver cómo cambia el puntaje y consultar qué está prestado o atrasado.

---

### Sprint 3 – Reportes, robustez y cierre
**Objetivo:** Completar la aplicación con reportes, exportación y manejo correcto de errores.

**Qué se debe lograr al final de este sprint:**
- Generar reportes en consola (préstamos activos, atrasados, ranking de usuarios, libros más prestados)
- Exportar información a CSV
- Búsquedas y filtros más completos
- Manejo correcto de archivos inexistentes o dañados
- Casos de prueba documentados (mínimo 8)
- Pulir el menú y los mensajes

**Historias que entran en este sprint:**
- HU-13 Generar reportes
- HU-14 Exportar información a CSV
- HU-15 Búsquedas y filtros avanzados
- HU-16 Manejo de errores y archivos

**Resultado esperado:**  
La aplicación está completa, estable, genera reportes útiles y exporta CSV. Lista para la sustentación.

---

## Definition of Done (cuándo una historia se considera terminada)

Una historia solo se marca como terminada cuando cumple todo esto:

- Cumple sus criterios de aceptación
- El código funciona correctamente
- Está integrada en el proyecto
- Fue probada
- Tiene commit y Pull Request relacionado
- Está actualizada en el tablero de GitHub
- Cualquier integrante del equipo puede explicar cómo funciona

---

## Reglas de trabajo en GitHub

- Cada historia o tarea importante se trabaja en su propia rama (`feature/HU-01-registrar-usuario`)
- Los commits deben ser claros y describir el cambio real
- Se trabaja con Pull Requests
- El tablero de GitHub Projects debe reflejar el estado real del trabajo (Backlog, Todo, In Progress, In Review, Done)
- No se marca nada como terminado si no cumple la Definition of Done

---

## Cómo empezar (primeros pasos)

1. Crear el repositorio en GitHub
2. Crear el tablero de GitHub Projects con las columnas: Backlog, Todo, In Progress, In Review, Done
3. Subir este README
4. Crear las Issues de las historias del Sprint 1
5. Hacer el Sprint Planning del Sprint 1
6. Crear la estructura de carpetas del proyecto
7. Empezar a desarrollar las historias del Sprint 1

---

## Notas importantes

- Todos deben entender el proyecto completo, no solo la parte que desarrollaron.
- Se permite usar inteligencia artificial como apoyo, pero cada uno debe entender y poder explicar lo que se implemente.
- El proyecto debe ser nuevo. No se aceptan copias de los laboratorios.
- La aplicación solo se muestra en terminal.

Cualquier duda sobre el alcance o las historias se resuelve en el equipo o se consulta con el Product Owner.
