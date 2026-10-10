# Tareas 003 — Refactorización UI: Administración de Operadores

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`003-spec.md`](./003-spec.md) |
| Plan   | [`003-plan.md`](./003-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

> Una tarea = **una función** (o un cambio pequeño). Cada tarea cierra el ciclo:
> **implementar → probar → corregir → documentar → commit**.

## Tareas

- [x] **T-01** — Escribir especificación técnica (`003-spec.md`), plan y tareas.
  - Criterio de aceptación: Documentos oficiales creados.
  - Estado: hecho
- [ ] **T-02** — Actualizar Facade / Repositorio con métodos de guardado (si aplica).
  - Criterio de aceptación: La capa de infraestructura permite crear/actualizar operadores.
  - Estado: pendiente
- [ ] **T-03** — Crear la carpeta `modulos/admin_operadores/` y su archivo `ui.py`.
  - Criterio de aceptación: La lógica visual pesada se extrae a funciones puras en `ui.py`. No hay SQL.
  - Estado: pendiente
- [ ] **T-04** — Refactorizar página principal (`pages/2_Administracion_Operadores.py`).
  - Criterio de aceptación: Importa `render_page()` desde `admin_operadores` y no hace más que pintar.
  - Estado: pendiente
- [ ] **T-05** — Borrar archivo residual de la carpeta heredada `modulos/`.
  - Criterio de aceptación: `5_Administracion_Operadores.py` eliminado.
  - Estado: pendiente

## Progreso

| Tarea | Estado | Commit |
|-------|--------|--------|
| T-01  | ✅     | N/A    |
| T-02  | ⏳     |        |
| T-03  | ⏳     |        |
| T-04  | ⏳     |        |

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
