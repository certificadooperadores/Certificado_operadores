# Tareas 011 — Desacoplamiento de Autenticación y Login en Inicio.py

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`011-spec.md`](./011-spec.md) |
| Plan   | [`011-plan.md`](./011-plan.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |

## Tareas

- [x] **T-01** — Escribir especificación técnica, plan y tareas.
  - Estado: hecho
- [x] **T-02** — Extender dominio (`domain/usuarios.py`) y repositorio (`infra/usuarios_repository.py`) para credenciales.
  - Criterio de aceptación: DTO `ResultadoAutenticacion` y consulta segura de credenciales disponibles.
  - Estado: hecho (`ResultadoAutenticacion`, `CredencialesUsuario` y `obtener_para_autenticacion`).
- [x] **T-03** — Implementar `autenticar()` en `UsuariosFacade`.
  - Criterio de aceptación: Validación de usuario, estado activo y comprobación con `verificar_contrasena`.
  - Estado: hecho.
- [x] **T-04** — Refactorizar `Inicio.py`.
  - Criterio de aceptación: Elimina `run_query` y `bcrypt`; invoca `UsuariosFacade().autenticar()`.
  - Estado: hecho.
- [x] **T-05** — Pruebas unitarias en `tests/test_autenticacion.py`.
  - Criterio de aceptación: `make test` pasa 100% en verde con todos los casos de login cubiertos.
  - Estado: hecho (225 pruebas en verde; `tests/test_autenticacion.py` con 13 casos).

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
