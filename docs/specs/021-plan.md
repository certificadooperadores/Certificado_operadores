# Plan 021 — Eliminación Integral de Warnings y Cierre Limpio de Conexiones SQLite

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Spec    | [`021-spec.md`](./021-spec.md)                                       |
| Tareas  | [`021-tareas.md`](./021-tareas.md)                                   |
| Rama    | `feat/eliminar-warnings-sqlite`                                      |

## 1. Arquitectura y Enfoque Técnico

Para eliminar los 161 `ResourceWarning` sin ocultarlos:

1. **Estandarizar fixtures de prueba con `Iterator[Engine]` y `NullPool`:**
   En cada archivo de prueba que cree un `create_engine`:
   - Configurar `poolclass=NullPool`. Con `NullPool`, SQLAlchemy no retiene conexiones en un pool interno tras cerrar las transacciones.
   - Usar la sintaxis de generador de pytest:
     ```python
     @pytest.fixture
     def motor_sqlite(...) -> Iterator[Engine]:
         motor = create_engine(..., poolclass=NullPool)
         ...
         yield motor
         motor.dispose()
     ```
2. **Pruebas con motores en memoria inline:**
   - En `test_autenticacion.py`: envolver los motores `sqlite:///:memory:` para llamar a `motor.dispose()` al final de cada test.
   - En `test_seguridad_sesion.py`: cerrar el motor tras la prueba.
   - En `test_facade.py`: usar `motor_vacio.dispose()` en el teardown.
3. **Criterio permanente de pureza (`-W error`):**
   - Actualizar `pyproject.toml` con `addopts = "-q -W error"`.
   - Ejecutar `uv run pytest`. Si surge cualquier advertencia adicional (de openpyxl, pandas o SQLAlchemy), resolverla en su origen para lograr 0 warnings.
4. **Documentación:**
   - Actualizar `CONSTITUTION.md` registrando la regla de pureza estricta de advertencias en pruebas.

## 2. Secuencia de Trabajo

1. Refactorizar las fixtures de `motor_sqlite` en todos los archivos de `tests/` para usar `NullPool` y `yield ... motor.dispose()`.
2. Refactorizar las pruebas que crean motores inline para asegurar `motor.dispose()`.
3. Configurar `addopts = "-q -W error"` en `pyproject.toml`.
4. Ejecutar `uv run pytest` y corregir cualquier advertencia residual hasta obtener 100% verde con 0 warnings.
5. Actualizar `CONSTITUTION.md`.
