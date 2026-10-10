# Tareas 020 — Validación, Blindaje y Bloqueo de Campos por Categoría de Evento

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Spec    | [`020-spec.md`](./020-spec.md)                                       |
| Plan    | [`020-plan.md`](./020-plan.md)                                       |
| Rama    | `feat/bloqueo-campos-por-categoria-evento`                           |
| Estado  | en progreso                                                          |

## Lista de tareas

- [ ] **T-01:** Definir `CAMPOS_PERMITIDOS_POR_EVENTO` y `CampoIncompatibleError` en `eventos_repository.py`.
- [ ] **T-02:** Implementar en `actualizar_registros()` la validación previa de compatibilidad campo-categoría y la limpieza a `NULL` de campos huérfanos al mutar tipo.
- [ ] **T-03:** Añadir validación de fechas (no fechas futuras inverosímiles y formato válido).
- [ ] **T-04:** Ajustar la proyección de columnas visibles y editables en `correccion_registros/ui.py` cuando se filtre por tipo de evento.
- [ ] **T-05:** Crear pruebas unitarias exhaustivas en `tests/test_correccion_registros.py` que comprueben rechazo, rollback y reseteo.
- [ ] **T-06:** Validar con `uv run pytest` que todas las pruebas pasen al 100% en verde.
- [ ] **T-07:** Actualizar `CONSTITUTION.md` y `docs/referencia-funciones.md`.
