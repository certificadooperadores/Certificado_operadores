# Tareas 008 — Refactorización UI: Gestion Certificados

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`008-spec.md`](./008-spec.md) |
| Plan   | [`008-plan.md`](./008-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [ ] **T-02** — Proveer repositorio/servicios para registro y consulta de eventos y certificados.
  - Criterio de aceptación: Operaciones de búsqueda, validación de operador activo y registro desacopladas.
  - Estado: pendiente
- [ ] **T-03** — Crear el paquete `modulos/gestion_certificados/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_gestion_certificados()` implementada sin sentencias SQL.
  - Estado: pendiente
- [ ] **T-04** — Actualizar `pages/2_Administracion_Operadores.py`.
  - Criterio de aceptación: Pestaña 2 invoca `render_gestion_certificados()`, eliminando `exec`.
  - Estado: pendiente
- [ ] **T-05** — Pruebas unitarias en `tests/test_gestion_certificados.py`.
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
