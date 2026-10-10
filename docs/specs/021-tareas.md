# Tareas 021 — Eliminación Integral de Warnings y Cierre Limpio de Conexiones SQLite

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Spec    | [`021-spec.md`](./021-spec.md)                                       |
| Plan    | [`021-plan.md`](./021-plan.md)                                       |
| Rama    | `feat/eliminar-warnings-sqlite`                                      |
| Estado  | completado                                         |

## Lista de tareas

- [x] **T-01:** Convertir las fixtures de `motor_sqlite` en `tests/test_correccion_registros.py`, `tests/test_reportes.py`, `tests/test_reporte_comportamientos.py` a `Iterator[Engine]` con `NullPool` y `motor.dispose()`.
- [x] **T-02:** Convertir las fixtures de `motor_sqlite` en `tests/test_gestion_usuarios.py`, `tests/test_gestion_certificados.py`, `tests/test_catalogos.py` a `Iterator[Engine]` con `NullPool` y `motor.dispose()`.
- [x] **T-03:** Refactorizar motores en `tests/test_autenticacion.py`, `tests/test_facade.py` y `tests/test_seguridad_sesion.py` con `NullPool` y `motor.dispose()`.
- [x] **T-04:** Configurar `addopts = "-q -W error"` en `pyproject.toml`.
- [x] **T-05:** Ejecutar `uv run pytest` verificando que 341 pruebas pasen sin una sola advertencia (código de salida 0 con cero warnings).
- [x] **T-06:** Actualizar `CONSTITUTION.md` con la política de cero advertencias y pruebas puras.
