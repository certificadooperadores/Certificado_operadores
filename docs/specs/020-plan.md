# Plan 020 — Validación, Blindaje y Bloqueo de Campos por Categoría de Evento

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Spec    | [`020-spec.md`](./020-spec.md)                                       |
| Tareas  | [`020-tareas.md`](./020-tareas.md)                                   |
| Rama    | `feat/bloqueo-campos-por-categoria-evento`                           |

## 1. Arquitectura y Enfoque Técnico

El objetivo es aplicar **defensa en profundidad**:
1. **Infraestructura (`eventos_repository.py`):**
   - Declarar `CAMPOS_PERMITIDOS_POR_EVENTO: dict[int, frozenset[str]]`.
   - Crear `CampoIncompatibleError(ValueError)`.
   - En `actualizar_registros()`, para la tabla `fact_eventos_operador`:
     - Resolver el `id_tipo_evento` efectivo de cada fila (el nuevo si cambió, o el actual en base de datos).
     - Validar que cada campo mutado pertenezca al conjunto permitido.
     - Si no pertenece y el valor propuesto no es nulo/vacío, rechazar inmediatamente antes de ejecutar el `UPDATE`.
     - Si se modificó `id_tipo_evento`, emitir cláusula `UPDATE` que asigne `NULL` a todas las columnas incompatibles con el nuevo tipo.
     - Validar que las fechas sean sintácticamente correctas y no superen `date.today() + timedelta(days=1)`.
2. **Interfaz de Usuario (`correccion_registros/ui.py`):**
   - En la sub-pestaña **Eventos**, inspeccionar el filtro `tipo_evento_filtro`.
   - Si se selecciona un tipo específico, filtrar la tupla de `columnas` y `editables` para enviar al `data_editor` únicamente las que aplican para ese tipo.
   - Capturar `CampoIncompatibleError` y mostrar alerta amigable en Streamlit.
3. **Pruebas (`test_correccion_registros.py`):**
   - Pruebas unitarias para cada caso de rechazo:
     - Asignar `fecha_retiro` a `certificacion` -> falla.
     - Asignar `fecha_certificado` a `cancelacion` -> falla.
     - Asignar `fecha_suspension` a `observacion` -> falla.
     - Cambiar `certificacion` a `cancelacion` -> limpia `fecha_certificado` y vehiculo a `NULL`.
     - Fecha futura lejana (ej. 2030) -> falla.

## 2. Secuencia de Trabajo

1. Implementar la matriz de compatibilidad y excepciones en `eventos_repository.py`.
2. Implementar la validación y limpieza en `actualizar_registros()`.
3. Ajustar `ui.py` para proyectar columnas contextuales según el filtro activo.
4. Escribir pruebas unitarias en `test_correccion_registros.py`.
5. Ejecutar `uv run pytest` asegurando 100% verde.
6. Actualizar `CONSTITUTION.md` y `docs/referencia-funciones.md`.
