# Spec 001 — Desacoplamiento Facade y Pruebas de SQLite

| Campo     | Valor                                              |
|-----------|----------------------------------------------------|
| Estado    | aprobada                                           |
| Autor     | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha     | 2026-10-09                                         |
| Rama      | `main`                                             |
| Relaciona | CONSTITUTION.md (Regla Facade)                     |

## 1. Contexto y problema

La aplicación fue migrada exitosamente a SQLite local (`operadores.db`). Sin embargo, según la regla arquitectónica de `CONSTITUTION.md`:
"La UI no ejecuta tareas (patrón Facade): la interfaz (incluida Streamlit) solo captura entrada, llama al Facade y muestra el resultado; cero lógica de negocio y cero acceso directo a BD/APIs desde la UI. `UI → Facade → Dominio → Infraestructura`."

Actualmente, las vistas en `src/certificado_operadores/` acceden directamente al motor o funciones de base de datos sin una fachada unificada ni pruebas unitarias asociadas.

## 2. Objetivos

- Implementar un módulo Facade (`src/certificado_operadores/facade.py`) que exponga las operaciones del sistema (consultas de operadores, validación de certificados, estadísticas básicas) aislando el acceso a datos.
- Proveer pruebas unitarias con `pytest` en `tests/test_facade.py` con el patrón AAA.
- Asegurar que `uv run pytest` pase 100% en verde.

## 3. No-objetivos

- No rediseñar la interfaz visual de Streamlit en este ciclo.
- No alterar los archivos de respaldo en `version_1/`.

## 4. Requisitos funcionales

- **RF-01:** La fachada `OperadoresFacade` debe proveer un método para verificar el estado de la conexión a la base de datos SQLite.
- **RF-02:** La fachada debe proveer métodos para consultar información de operadores por cédula / código.
- **RF-03:** Todas las llamadas a base de datos deben usar sesiones/conexiones limpias y seguras sin queries quemadas sin tipar.

## 5. Requisitos no funcionales

- **RNF-01 (Arquitectura):** La UI solo invoca métodos de `OperadoresFacade`.
- **RNF-02 (Estilo y documentación):** Docstrings en español, tipado estricto, sin hardcodear rutas (usar variables o configuración).
- **RNF-03 (Pruebas):** Pruebas unitarias en `tests/` con patrón AAA.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe `src/certificado_operadores/facade.py` con la clase `OperadoresFacade`.
- [ ] **CA-02:** Existe `tests/test_facade.py` probando los métodos clave contra SQLite con fixtures adecuadas.
- [ ] **CA-03:** `uv run pytest` pasa exitosamente.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
