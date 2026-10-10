# Tareas 009 — Refactorización UI: Reportes Bitacora

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`009-spec.md`](./009-spec.md) |
| Plan   | [`009-plan.md`](./009-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [ ] **T-02** — Crear repositorio de comportamientos (`comportamientos_repository.py`) para registro, carga y reincidencia.
  - Criterio de aceptación: Operaciones de consultas de operadores, detalles de comportamiento y mutaciones aisladas.
  - Estado: pendiente
- [ ] **T-03** — Crear el paquete `modulos/reporte_comportamientos/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_reporte_comportamientos()` creada sin sentencias SQL.
  - Estado: pendiente
- [ ] **T-04** — Limpiar `pages/2_Administracion_Operadores.py` eliminando el último `exec`.
  - Criterio de aceptación: Importa y llama `render_reporte_comportamientos()`; 0 `exec` en la página.
  - Estado: pendiente
- [ ] **T-05** — Pruebas unitarias en `tests/test_reporte_comportamientos.py`.
  - Criterio de aceptación: `make test` pasa 100% en verde.
  - Estado: pendiente

## Progreso

| Tarea | Estado | Commit |
|-------|--------|--------|
| T-01  | hecho  | N/A    |
| T-02  | pendiente |        |
| T-03  | pendiente |        |
| T-04  | pendiente |        |
| T-05  | pendiente |        |

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
