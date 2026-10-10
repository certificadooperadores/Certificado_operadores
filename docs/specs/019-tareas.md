# Tareas 019 — Columnas Completas de Negocio para la Tabla de Eventos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`019-spec.md`](./019-spec.md)                     |
| Plan    | [`019-plan.md`](./019-plan.md)                     |
| Rama    | `feat/columnas-completas-eventos`                  |
| Estado  | en progreso                                        |

## Lista de tareas

- [x] **T-01:** Incorporar las 10 columnas adicionales de negocio en la definición de la tabla `eventos` de `eventos_repository.py`.
- [x] **T-02:** Asegurar que los tipos de edición (fechas, texto de observación, vehículo) se mapeen correctamente en `ui.py`.
- [x] **T-03:** Adaptar las pruebas en `tests/test_correccion_registros.py` para validar la presencia y persistencia de las nuevas columnas.
- [x] **T-04:** Ejecutar `uv run pytest tests/test_correccion_registros.py` y asegurar 100% verde.
- [x] **T-05:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
