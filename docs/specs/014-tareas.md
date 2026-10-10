# Tareas 014 — Restauración de Backups con Comparación Preventiva de Registros

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`014-spec.md`](./014-spec.md)                     |
| Plan    | [`014-plan.md`](./014-plan.md)                     |
| Rama    | `feat/restauracion-backups-comparacion`            |
| Estado  | en progreso                                        |

## Lista de tareas

- [ ] **T-01:** Agregar pruebas en `tests/test_backups.py` para `comparar_backup` y `restaurar_backup`.
- [ ] **T-02:** Implementar `comparar_backup` en `src/certificado_operadores/infra/backup_service.py`.
- [ ] **T-03:** Implementar `restaurar_backup` en `src/certificado_operadores/infra/backup_service.py` con respaldo preventivo y actualización de `dim_version_bd`.
- [ ] **T-04:** Añadir en `src/certificado_operadores/modulos/administrar_backups/ui.py` el flujo visual de análisis de diferencias y confirmación de restauración.
- [ ] **T-05:** Ejecutar `uv run pytest tests/test_backups.py` y validar 100% verde.
- [ ] **T-06:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
