# Tareas 018 — Perfeccionamiento de Corrección de Registros

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`018-spec.md`](./018-spec.md)                     |
| Plan    | [`018-plan.md`](./018-plan.md)                     |
| Rama    | `feat/perfeccionamiento-correccion-registros`      |
| Estado  | en progreso                                        |

## Lista de tareas

- [ ] **T-01:** Agregar definición de tabla `Códigos` (`dim_codigo`) y opciones oficiales de licencias (`C1`, `C2`, `C3`) y fuentes/descripciones en `eventos_repository.py`.
- [ ] **T-02:** Configurar `SelectboxColumn` para Licencias (C1, C2, C3) y Comportamientos (Fuente y Descripción) en `ui.py`.
- [ ] **T-03:** Añadir barra de búsqueda rápida encima de cada tabla en `ui.py` con filtrado dinámico.
- [ ] **T-04:** Incorporar botones de acción en bloque (`Vigente`, `Anulado`, `Eliminar`) conviviendo con el guardado celda a celda.
- [ ] **T-05:** Actualizar pruebas unitarias en `tests/test_correccion_registros.py` y asegurar 100% verde con `uv run pytest`.
- [ ] **T-06:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
