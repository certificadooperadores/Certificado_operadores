# Spec 021 — Eliminación Integral de Warnings y Cierre Limpio de Conexiones SQLite

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Estado  | aprobada                                                             |
| Autor   | Ing. Miguel Angel Ortiz Roldan                                       |
| Fecha   | 2026-10-10                                                           |
| Rama    | `feat/eliminar-warnings-sqlite`                                      |
| Relaciona | `CONSTITUTION.md` (Calidad y pruebas limpias)                      |

## 1. Contexto y problema

Al ejecutar la suite de pruebas (`pytest`), se generan actualmente **161 advertencias** (`ResourceWarning: unclosed database in <sqlite3.Connection>`).

Bajo Python 3.13, el recolector de basura emite `ResourceWarning` cuando las conexiones internas de SQLite se destruyen sin cerrarse explícitamente. Esto ocurre porque las fixtures de pruebas y pruebas aisladas en `tests/` instancian motores de SQLAlchemy (`create_engine`) sin `poolclass=NullPool` y sin ejecutar `motor.dispose()` en la fase de teardown de la fixture.

El usuario exige expresamente **cero advertencias (código puro) sin ocultarlas**: queda **terminantemente prohibido** silenciarlas con `filterwarnings = ["ignore"]`. Se debe resolver la causa raíz en el código fuente de las pruebas y la infraestructura.

## 2. Requerimientos Técnicos

### S-01: Prohibición de Silenciar Advertencias
No se permite usar `filterwarnings = ["ignore"]`, `@pytest.mark.filterwarnings` ni directivas que escondan advertencias. El código debe ser completamente limpio.

### S-02: Patrón Limpio en Fixtures de Motor SQLAlchemy
En todos los archivos bajo `tests/` que declaran fixtures de motor (`motor_sqlite`, `motor_vacio`, etc.):
1. Importar `from sqlalchemy.pool import NullPool` y `from collections.abc import Iterator`.
2. Crear el motor configurando `poolclass=NullPool`.
3. Estructurar la fixture como generador `Iterator[Engine]`:
   ```python
   @pytest.fixture
   def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
       motor = create_engine(f"sqlite:///{tmp_path / 'prueba.db'}", poolclass=NullPool)
       _crear_esquema(motor)
       _sembrar_datos(motor)
       yield motor
       motor.dispose()
   ```

### S-03: Cierre Limpio de Motores en Pruebas Aisladas (Inline)
En pruebas donde se crean motores directos (por ejemplo `sqlite:///:memory:` en `test_autenticacion.py`, `test_seguridad_sesion.py`, `test_facade.py`):
1. Usar `poolclass=NullPool`.
2. Garantizar `motor.dispose()` en bloque `try ... finally` o tras su uso.

### S-04: Criterio Duro Permanente en Configuración (`-W error`)
En `pyproject.toml`, configurar en `[tool.pytest.ini_options]`:
```toml
addopts = "-q -W error"
```
Esto asegura que, de ahora en adelante, cualquier advertencia nueva que se introduzca en el proyecto fallará inmediatamente la ejecución de pruebas.

## 3. Archivos Afectados

- `pyproject.toml`
- `tests/test_correccion_registros.py`
- `tests/test_reportes.py`
- `tests/test_reporte_comportamientos.py`
- `tests/test_gestion_usuarios.py`
- `tests/test_gestion_certificados.py`
- `tests/test_catalogos.py`
- `tests/test_autenticacion.py`
- `tests/test_facade.py`
- `tests/test_seguridad_sesion.py`

## 4. Criterios de Aceptación (verificables)

- [ ] **CA-01:** Todas las fixtures de base de datos en `tests/` usan `poolclass=NullPool` y ejecutan `motor.dispose()` en el teardown con `yield`.
- [ ] **CA-02:** Los motores temporales creados inline en funciones de prueba son liberados con `motor.dispose()`.
- [ ] **CA-03:** `pyproject.toml` tiene configurado `addopts = "-q -W error"`.
- [ ] **CA-04:** La ejecución de `uv run pytest` pasa al 100% en verde con **0 advertencias** (cero warnings).
- [ ] **CA-05:** `make check` (lint, formato y pruebas) pasa 100% en verde sin fallos.

## 5. Enlaces

- Plan: [`021-plan.md`](./021-plan.md)
- Tareas: [`021-tareas.md`](./021-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
