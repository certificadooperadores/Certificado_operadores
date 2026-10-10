# Spec 011 — Desacoplamiento de Autenticación y Login en Inicio.py

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-auth-login`                         |
| Relaciona | `002-spec.md` (Facade Arquitectura), `004-spec.md` (Usuarios) |

## 1. Contexto y problema

El archivo de entrada principal `src/certificado_operadores/Inicio.py` viola los principios de Clean Architecture y la regla Facade:
- Contiene consultas SQL directas en la vista: `run_query("SELECT password_hash, rol, estado FROM dim_usuarios WHERE usuario=:u", {"u": u})`.
- Ejecuta verificación criptográfica directa con `bcrypt.checkpw` en lugar de utilizar la capa de seguridad e infraestructura existente.
- Toda la aplicación Streamlit ya fue desacoplada en sus 3 páginas maestras, pero el punto de entrada `Inicio.py` aún mantiene acoplamiento directo a base de datos.

## 2. Objetivos

- Incorporar en el dominio `src/certificado_operadores/domain/usuarios.py` el DTO `ResultadoAutenticacion` y las constantes de mensajes de login.
- Agregar en `src/certificado_operadores/infra/usuarios_repository.py` el método para consultar credenciales seguras por nombre de usuario.
- Exponer en `src/certificado_operadores/facade_usuarios.py` el método `autenticar(usuario: str, contrasena: str) -> ResultadoAutenticacion` orquestando repositorio, dominio y `verificar_contrasena`.
- En `src/certificado_operadores/Inicio.py`, eliminar `from db import run_query` e `import bcrypt`, reemplazando el bloque de login por el llamado a `UsuariosFacade().autenticar(u, p)`.
- Crear pruebas unitarias con `pytest` en `tests/test_autenticacion.py`.

## 3. No-objetivos

- No modificar la lógica de persistencia en `session_state` tras el login exitoso (`logged_in`, `usuario`, `rol`).

## 4. Requisitos funcionales

- **RF-01:** Autenticación exitosa cuando el usuario existe, está activo y la contraseña coincide con el hash almacenado.
- **RF-02:** Manejo y reporte claro de error cuando el usuario no existe.
- **RF-03:** Manejo y reporte claro de error cuando el usuario se encuentra inactivo.
- **RF-04:** Manejo y reporte claro de error cuando la contraseña no coincide.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero sentencias SQL e importaciones de base de datos o bcrypt en `Inicio.py`.
- **RNF-02 (Arquitectura):** Se respeta estrictamente `UI → Facade → Dominio → Infraestructura`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** `UsuariosFacade` implementa `autenticar(usuario, contrasena)` devolviendo `ResultadoAutenticacion`.
- [ ] **CA-02:** `Inicio.py` no importa `run_query` ni `bcrypt`; delega la autenticación en `UsuariosFacade`.
- [ ] **CA-03:** Existen pruebas en `tests/test_autenticacion.py` validando todos los casos (éxito, inactivo, no existe, clave incorrecta).
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`011-plan.md`](./011-plan.md)
- Tareas: [`011-tareas.md`](./011-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
