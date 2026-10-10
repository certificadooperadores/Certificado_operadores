# Tareas 004 — Refactorización UI: Gestion Usuarios

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`004-spec.md`](./004-spec.md) |
| Plan   | [`004-plan.md`](./004-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [ ] **T-02** — Proveer soporte de datos para usuarios en Facade/Repositorio sin SQL en la UI.
  - Criterio de aceptación: La capa de aplicación soporta listar, crear y actualizar usuarios.
  - Estado: pendiente
- [ ] **T-03** — Crear el paquete `modulos/gestion_usuarios/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Lógica visual extraída con `render_gestion_usuarios()`, cero SQL.
  - Estado: pendiente
- [ ] **T-04** — Actualizar `pages/1_Configuracion.py`.
  - Criterio de aceptación: Importa y ejecuta `render_gestion_usuarios()`, eliminando `exec(open(...))` de la pestaña 1.
  - Estado: pendiente
- [ ] **T-05** — Pruebas unitarias en `tests/test_gestion_usuarios.py`.
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
