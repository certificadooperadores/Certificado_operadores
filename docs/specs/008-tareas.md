# Tareas 008 — Refactorización UI: Gestion Certificados

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`008-spec.md`](./008-spec.md) |
| Plan   | [`008-plan.md`](./008-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [x] **T-02** — Proveer repositorio/servicios para registro y consulta de eventos y certificados.
  - Criterio de aceptación: Operaciones de búsqueda, validación de operador activo y registro desacopladas.
  - Estado: hecho
- [x] **T-03** — Crear el paquete `modulos/gestion_certificados/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_gestion_certificados()` implementada sin sentencias SQL.
  - Estado: hecho
- [x] **T-04** — Actualizar `pages/2_Administracion_Operadores.py`.
  - Criterio de aceptación: Pestaña 2 invoca `render_gestion_certificados()`, eliminando `exec`.
  - Estado: hecho
- [x] **T-05** — Pruebas unitarias en `tests/test_gestion_certificados.py`.
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
