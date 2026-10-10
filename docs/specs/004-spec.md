# Spec 004 — Refactorización UI: Gestion Usuarios

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-gestion-usuarios`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/1_Gestion_Usuarios.py` viola los principios de Clean Architecture al mezclar la interfaz visual de Streamlit con consultas directas a la base de datos (`run_query`, `run_transaction` y `registrar_auditoria` de `db.py`).
Actualmente, la página `src/certificado_operadores/pages/1_Configuracion.py` lo invoca usando el antipatrón peligroso `exec(open("modulos/1_Gestion_Usuarios.py").read(), globals())`.

## 2. Objetivos

- Extraer la lógica de presentación a una carpeta modular exclusiva: `src/certificado_operadores/modulos/gestion_usuarios/ui.py` con la función `render_gestion_usuarios()`.
- Crear o extender los métodos correspondientes en la capa de datos/Facade para usuarios (`listar_usuarios`, `crear_usuario`, `modificar_usuario`) de modo que la UI no contenga sentencias SQL (`SELECT`, `INSERT`, `UPDATE`).
- En `src/certificado_operadores/pages/1_Configuracion.py`, reemplazar la llamada `exec(open("modulos/1_Gestion_Usuarios.py").read(), globals())` por la importación limpia: `from modulos.gestion_usuarios.ui import render_gestion_usuarios`.
- Crear pruebas unitarias con `pytest` en `tests/test_gestion_usuarios.py`.

## 3. No-objetivos

- No alterar las demás pestañas de `1_Configuracion.py` en este ciclo (Backups, Corrección y Catálogos se abordarán en sus respectivas specs).
- No modificar el algoritmo de hashing (mantener `bcrypt`).

## 4. Requisitos funcionales

- **RF-01:** Visualizar el listado de usuarios del sistema (`dim_usuarios`).
- **RF-02:** Crear nuevos usuarios con validación de existencia previa y contraseña hasheada con `bcrypt`.
- **RF-03:** Modificar rol, estado y contraseña de usuarios existentes, respetando la regla de que solo `Super Administrador` puede modificar cuentas con ese rol y evitando que un usuario inactive su propia cuenta.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero sentencias SQL en `modulos/gestion_usuarios/ui.py` ni en `pages/1_Configuracion.py`.
- **RNF-02 (Arquitectura):** Se elimina el `exec` en la pestaña de Gestión de Usuarios en `pages/1_Configuracion.py`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/gestion_usuarios/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/1_Configuracion.py` importa `render_gestion_usuarios` y ya NO usa `exec` para la pestaña 1.
- [ ] **CA-03:** No existen sentencias SQL (`SELECT`, `INSERT`, `UPDATE`) en `modulos/gestion_usuarios/ui.py`.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`004-plan.md`](./004-plan.md)
- Tareas: [`004-tareas.md`](./004-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
