# Tareas 002 — Modularización Arquitectónica del Facade

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`002-spec.md`](./002-spec.md) |
| Plan   | [`002-plan.md`](./002-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

> Una tarea = **una función** (o un cambio pequeño). Cada tarea cierra el ciclo:
> **implementar → probar → corregir → documentar → commit**.

## Tareas

- [x] **T-01** — Escribir especificación técnica (`002-spec.md`) para dividir `facade.py`.
  - Criterio de aceptación: La especificación define la extracción de Dominio e Infraestructura.
  - Estado: hecho
- [x] **T-02** — Redactar el Plan (`002-plan.md`) y Tareas (`002-tareas.md`).
  - Estado: hecho
- [x] **T-03** — Crear `domain/models.py`.
  - Criterio de aceptación: DTOs y lógica pura de fechas migrados correctamente. No contiene SQL ni SQLAlchemy.
  - Estado: hecho
- [x] **T-04** — Crear `infra/repository.py`.
  - Criterio de aceptación: Consultas SQL y gestión de conexiones SQLAlchemy extraídas y encapsuladas.
  - Estado: hecho
- [x] **T-05** — Refactorizar `facade.py`.
  - Criterio de aceptación: La clase Facade importa y usa el Repositorio; desaparecen las sentencias `text()` de este archivo.
  - Estado: hecho
- [x] **T-06** — Pasar pruebas unitarias.
  - Criterio de aceptación: El comando `make test` ejecuta y valida los 15 casos sin errores.
  - Estado: hecho

## Progreso

| Tarea | Estado | Commit |
|-------|--------|--------|
| T-01  | ✅     | N/A    |
| T-02  | ✅     | N/A    |
| T-03  | ✅     | 28a620a|
| T-04  | ✅     | 28a620a|
| T-05  | ✅     | 28a620a|
| T-06  | ✅     | 28a620a|

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
