# Tareas 010 — Refactorización UI: Pqr

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`010-spec.md`](./010-spec.md) |
| Plan   | [`010-plan.md`](./010-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [x] **T-02** — Crear repositorio de reportes (`reportes_repository.py`) para consultas, filtros y exportaciones.
  - Criterio de aceptación: Filtros y consultas de UTRYT y reportes consolidados aislados en infraestructura.
  - Estado: hecho
- [x] **T-03** — Crear el paquete `modulos/reportes/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_reportes()` creada sin sentencias SQL.
  - Estado: hecho
- [x] **T-04** — Limpiar `pages/3_Reportes.py` eliminando la llamada a `exec`.
  - Criterio de aceptación: Importa y llama `render_reportes()`; 0 `exec` en la página.
  - Estado: hecho
- [x] **T-05** — Pruebas unitarias en `tests/test_reportes.py`.
  - Criterio de aceptación: `make test` pasa 100% en verde.
  - Estado: hecho

## Progreso

| Tarea | Estado | Commit |
|-------|--------|--------|
| T-01  | hecho  | N/A    |
| T-02  | hecho  | `b243c44` |
| T-03  | hecho  | `b243c44` |
| T-04  | hecho  | `b243c44` |
| T-05  | hecho  | `b243c44` |

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
