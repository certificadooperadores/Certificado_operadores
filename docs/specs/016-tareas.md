# Tareas 016 — Orden Descendente y Barra de Búsqueda Rápida en Tablas de Corrección

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`016-spec.md`](./016-spec.md)                     |
| Plan    | [`016-plan.md`](./016-plan.md)                     |
| Rama    | `feat/orden-descendente-y-buscador-tabla`          |
| Estado  | en progreso                                        |

## Lista de tareas

- [ ] **T-01:** Actualizar consultas en `src/certificado_operadores/infra/eventos_repository.py` para devolver registros con orden descendente por defecto (más recientes primero).
- [ ] **T-02:** Agregar barra de búsqueda de una sola línea en `src/certificado_operadores/modulos/correccion_registros/ui.py` con filtrado dinámico en memoria.
- [ ] **T-03:** Adaptar `tests/test_correccion_registros.py` para validar orden descendente y filtrado.
- [ ] **T-04:** Ejecutar `uv run pytest tests/test_correccion_registros.py` y asegurar 100% verde.
- [ ] **T-05:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
