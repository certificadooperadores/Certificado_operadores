# Tareas 005 — Refactorización UI: Administrar Backups

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`005-spec.md`](./005-spec.md) |
| Plan   | [`005-plan.md`](./005-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [x] **T-02** — Crear servicio de copias de seguridad en infraestructura con ruta configurable.
  - Criterio de aceptación: Operaciones de listar, crear copia SQLite, proteger y eliminar encapsuladas.
  - Estado: hecho
- [x] **T-03** — Crear el paquete `modulos/administrar_backups/` con `ui.py` y `__init__.py`.
  - Criterio de aceptación: Función `render_administrar_backups()` implementada sin lógica de SO ni SQL en la UI.
  - Estado: hecho
- [x] **T-04** — Actualizar `pages/1_Configuracion.py`.
  - Criterio de aceptación: Importa `render_administrar_backups` y elimina `exec(open(...))` en pestaña 2.
  - Estado: hecho
- [x] **T-05** — Pruebas unitarias en `tests/test_backups.py`.
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
