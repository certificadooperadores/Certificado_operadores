# Tareas 007 — Refactorización UI: Catalogos

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`007-spec.md`](./007-spec.md) |
| Plan   | [`007-plan.md`](./007-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [x] **T-02** — Crear repositorio de catálogos (`catalogos_repository.py`) para operaciones CRUD de las 5 dimensiones.
  - Criterio de aceptación: Operaciones sobre dim_empresa, dim_vehiculo, dim_impacto, dim_comportamiento, dim_detalle_comportamiento desacopladas.
  - Estado: hecho
- [x] **T-03** — Crear el paquete `modulos/catalogos/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_catalogos()` creada sin sentencias SQL.
  - Estado: hecho
- [x] **T-04** — Limpiar `pages/1_Configuracion.py` eliminando el último `exec`.
  - Criterio de aceptación: Importa y llama `render_catalogos()`; 0 `exec` en la página.
  - Estado: hecho
- [x] **T-05** — Pruebas unitarias en `tests/test_catalogos.py`.
  - Criterio de aceptación: `make test` pasa 100% en verde.
  - Estado: hecho

## Progreso

| Tarea | Estado | Commit |
|-------|--------|--------|
| T-01  | hecho  | N/A    |
| T-02  | hecho  |        |
| T-03  | hecho  |        |
| T-04  | hecho  |        |
| T-05  | hecho  |        |

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
