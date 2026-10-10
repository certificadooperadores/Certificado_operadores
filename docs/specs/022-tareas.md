# Tareas 022 — Compatibilidad Total de Consultas de Reportes con SQLite

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Spec    | [`022-spec.md`](./022-spec.md)                                       |
| Plan    | [`022-plan.md`](./022-plan.md)                                       |
| Rama    | `feat/fix-consultas-reportes-sqlite`                                 |
| Estado  | en progreso                                                          |

## Lista de tareas

- [ ] **T-01:** Reemplazar `::date` y `INTERVAL` por funciones nativas de SQLite (`DATE()`, `JULIANDAY()`) en `reportes_repository.py`.
- [ ] **T-02:** Reemplazar `DISTINCT ON` por funciones de ventana `ROW_NUMBER() OVER (...)` en los reportes de certificados de `reportes_repository.py`.
- [ ] **T-03:** Actualizar `construir_condiciones()` para que los filtros de rango de días usen `DATE('now', '+' || :dias || ' days')`.
- [ ] **T-04:** Añadir pruebas en `tests/test_reportes.py` que ejecuten los 8 reportes verificando que ninguno falle en SQLite.
- [ ] **T-05:** Ejecutar `uv run pytest` con `-W error` asegurando 100% verde y cero warnings.
- [ ] **T-06:** Actualizar `CONSTITUTION.md` y `docs/referencia-funciones.md`.
