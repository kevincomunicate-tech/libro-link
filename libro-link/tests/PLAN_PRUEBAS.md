# Plan de pruebas

Las pruebas automáticas están en `tests/test_librolink.py` y se ejecutan con:

```
python -m unittest -v
```

Resultado actual: 61 pruebas, todas aprobadas.

## Casos documentados

| N.º | Caso | Resultado esperado | Prueba automática |
|-----|------|--------------------|-------------------|
| 1 | Registrar usuario con datos válidos | Se crea con ID `U001`, correo en minúsculas y aparece en la lista | `test_registrar_asigna_id_y_normaliza_correo` |
| 2 | Registrar usuario con correo repetido | Se rechaza con mensaje claro | `test_correo_duplicado_se_rechaza` |
| 3 | Registrar con campos vacíos, correo mal formado o nombre con números | Se rechaza y no se guarda nada | `test_campos_obligatorios_y_formatos` |
| 4 | Buscar usuarios por nombre o correo sin importar tildes ni mayúsculas | Devuelve solo las coincidencias; sin coincidencias devuelve lista vacía | `test_buscar_por_nombre_o_correo_sin_tildes_ni_mayusculas` |
| 5 | Registrar libro con ISBN con guiones | Se guarda el ISBN normalizado y el stock | `test_registrar_libro_completo` |
| 6 | Registrar libro con ISBN repetido, ISBN inválido o stock 0 | Se rechaza | `test_isbn_duplicado_y_formatos_invalidos` |
| 7 | Buscar libros por título, autor o ISBN | Devuelve solo los que coinciden | `test_buscar_por_titulo_autor_o_isbn` |
| 8 | Préstamo válido | Fecha de vencimiento a 14 días y libro queda PRESTADO | `test_prestamo_valido_y_estado_libro` |
| 9 | Prestar un libro sin ejemplares | Se rechaza | `test_no_prestar_libro_ya_prestado` |
| 10 | Devolución a tiempo | Sin multa y puntaje +2 | `test_devolucion_a_tiempo_puntaje` |
| 11 | Devolución con 2 días de retraso | Multa de $4.000 y puntaje -5 | `test_devolucion_tarde_multa_y_puntaje` |
| 12 | Multa de 5 días de retraso | $10.000 (2.000 por día) | `test_multa_es_dos_mil_por_dia` |
| 13 | Libro sin devolver | La multa crece cada día | `test_multa_crece_cada_dia_mientras_no_se_devuelve` |
| 14 | Usuario con multa pendiente pide otro libro | Se rechaza hasta que pague | `test_usuario_con_multa_pendiente_no_puede_pedir_prestado` |
| 15 | Pagar la multa | El usuario vuelve a poder pedir libros | `test_pagar_multa_libera_al_usuario` |
| 16 | Límite de préstamos por rol | Regular 3, premium 5 | `test_limite_de_prestamos_por_rol` |
| 17 | Devolver dos veces el mismo préstamo | Se rechaza | `test_no_devolver_dos_veces` |
| 18 | Editar usuario y cambiar su rol | Conserva el puntaje y cambia límites | `test_actualizar_cambia_datos_y_rol` |
| 19 | Eliminar usuario con préstamo activo o multa | Se rechaza; con todo saldado se elimina | `test_no_eliminar_usuario_con_prestamo_activo_o_multa` |
| 20 | Eliminar el último usuario y registrar otro | El ID no se reutiliza si hay historial | `test_eliminar_y_no_reutilizar_ids` |
| 21 | Reducir ejemplares por debajo de los prestados | Se rechaza | `test_actualizar_respeta_ejemplares_prestados` |
| 22 | Guardar y cargar JSON | La información queda igual | `test_json_guardar_y_cargar`, `test_ciclo_completo_usuarios_libros_prestamos` |
| 23 | JSON dañado | Error claro y el archivo no se borra | `test_json_danado_falla_sin_borrarse` |
| 24 | Archivo inexistente | Se inicia con lista vacía | `test_archivo_inexistente_devuelve_lista_vacia` |
| 25 | Ranking de confiabilidad | Ordenado por puntaje | `test_ranking_ordena_por_puntaje` |
| 26 | Exportar CSV con tildes y textos peligrosos | UTF-8 correcto y fórmulas neutralizadas | `test_exportar_csv_con_tildes_y_proteccion_de_formulas` |
| 27 | Inicio de sesión | Acepta la contraseña correcta y rechaza las demás | `test_autenticacion` |

## Pruebas manuales realizadas por consola
- Primer inicio: se crea el administrador y se muestra el aviso.
- Registro de usuarios y libros con datos inválidos: se muestra el error y se vuelve a pedir el dato.
- Préstamo, devolución con retraso, bloqueo por deuda, pago de multa y reportes.
- `/cancelar` abandona una operación sin guardar nada.
- Cerrar el programa de golpe guarda la información.
- Con un JSON dañado: responder "no" cierra sin tocar nada; responder "sí" conserva una copia y continúa.
- Tres contraseñas incorrectas cierran el programa.
