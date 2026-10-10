# Tareas 011 — Refactorización UI: Reporte Comportamientos

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`011-spec.md`](./011-spec.md) |
| Plan   | [`011-plan.md`](./011-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [ ] **T-02** — Extender dominio (`domain/usuarios.py`) y repositorio (`infra/usuarios_repository.py`) para credenciales.
  - Criterio de aceptación: DTO `ResultadoAutenticacion` y consulta segura de credenciales disponibles.
  - Estado: pendiente
- [ ] **T-03** — Implementar `autenticar()` en `UsuariosFacade`.
  - Criterio de aceptación: Validación de usuario, estado activo y comprobación con `verificar_contrasena`.
  - Estado: pendiente
- [ ] **T-04** — Refactorizar `Inicio.py`.
  - Criterio de aceptación: Elimina `run_query` y `bcrypt`; invoca `UsuariosFacade().autenticar()`.
  - Estado: pendiente
- [ ] **T-05** — Pruebas unitarias en `tests/test_autenticacion.py`.
  - Criterio de aceptación: `make test` pasa 100% en verde con todos los casos de login cubiertos.
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
