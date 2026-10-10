# Tareas 006 — Refactorización UI: Modificacion Tablas

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`006-spec.md`](./006-spec.md) |
| Plan   | [`006-plan.md`](./006-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [ ] **T-02** — Implementar repositorio de eventos (`eventos_repository.py`) para filtrado y mutación.
  - Criterio de aceptación: Operaciones sobre eventos y lotes aisladas con soporte de auditoría.
  - Estado: pendiente
- [ ] **T-03** — Crear el paquete `modulos/correccion_registros/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_correccion_registros()` creada sin sentencias SQL.
  - Estado: pendiente
- [ ] **T-04** — Limpiar `pages/1_Configuracion.py`.
  - Criterio de aceptación: Funciones inlined de corrección eliminadas; se llama `render_correccion_registros()`.
  - Estado: pendiente
- [ ] **T-05** — Pruebas unitarias en `tests/test_correccion_registros.py`.
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
