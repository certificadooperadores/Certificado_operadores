# Tareas 015 — Rediseño Compacto de Corrección de Registros por Tablas

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`015-spec.md`](./015-spec.md)                     |
| Plan    | [`015-plan.md`](./015-plan.md)                     |
| Rama    | `feat/rediseno-correccion-registros`               |
| Estado  | en progreso                                        |

## Lista de tareas

- [x] **T-01:** Rediseñar `src/certificado_operadores/modulos/correccion_registros/ui.py` reemplazando los subtabs de lote/individual y filtros gigantes por sub-tabs temáticas de tablas.
- [x] **T-02:** Configurar `st.dataframe` con selección múltiple interactiva nativa y búsqueda integrada en la tabla.
- [x] **T-03:** Añadir barra de acción horizontal directa con botones de cambio de estado y eliminación para los seleccionados.
- [x] **T-04:** Actualizar `tests/test_correccion_registros.py` para validar la lógica del nuevo módulo.
- [x] **T-05:** Ejecutar `uv run pytest tests/test_correccion_registros.py` y asegurar 100% verde.
- [x] **T-06:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
