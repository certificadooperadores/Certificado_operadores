# Spec 005 — Refactorización UI: Administrar Backups

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-administrar-backups`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/2_Administrar_Backups.py` presenta serios problemas de arquitectura:
- La página `src/certificado_operadores/pages/1_Configuracion.py` lo carga mediante `exec(open("modulos/2_Administrar_Backups.py").read(), globals())`.
- Tiene una ruta absoluta dura (`/Backups`) que falla fuera de un contenedor Linux específico.
- Asume `pg_dump` para PostgreSQL cuando la aplicación fue migrada a SQLite local (`operadores.db`). Para SQLite, el backup debe realizarse mediante copia segura o la API de backup de SQLite / SQLAlchemy, o delegarse a un servicio de infraestructura.
- Realiza operaciones de sistema de archivos (`os.remove`, `os.rename`, `os.listdir`) y SQL directo (`INSERT INTO dim_version_bd`) mezcladas en la vista.

## 2. Objetivos

- Extraer la vista a una carpeta modular exclusiva: `src/certificado_operadores/modulos/administrar_backups/ui.py` con la función `render_administrar_backups()`.
- Crear una capa de servicio/infraestructura (`src/certificado_operadores/infra/backup_service.py` o Facade) que encapsule las operaciones de backup (crear copia, listar backups, proteger/desproteger, eliminar) usando directorio configurable (por defecto carpeta local `backups/`).
- En `src/certificado_operadores/pages/1_Configuracion.py`, reemplazar `exec(open("modulos/2_Administrar_Backups.py").read(), globals())` por la importación limpia: `from modulos.administrar_backups.ui import render_administrar_backups`.
- Proveer pruebas unitarias con `pytest` en `tests/test_backups.py`.

## 3. No-objetivos

- No modificar las demás pestañas de `1_Configuracion.py` (Corrección de Registros y Catálogos se atenderán en Specs 006 y 007).

## 4. Requisitos funcionales

- **RF-01:** Listar backups existentes con nombre, tamaño, fecha de modificación y estado (protegido/desprotegido).
- **RF-02:** Crear nuevo backup de la base de datos SQLite actual con versionado de nombres.
- **RF-03:** Proteger/desproteger backups cambiando la extensión/metadato según corresponda.
- **RF-04:** Eliminar backups desprotegidos con confirmación.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero comandos de shell quemados o rutas duras tipo `/Backups`. La ruta de backups debe ser configurable o relativa por defecto (`backups/`).
- **RNF-02 (Arquitectura):** Se elimina el `exec` en la pestaña 2 de `pages/1_Configuracion.py`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/administrar_backups/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/1_Configuracion.py` invoca `render_administrar_backups` sin usar `exec`.
- [ ] **CA-03:** La gestión física de archivos de backup está delegada en una capa de servicio/infraestructura.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`005-plan.md`](./005-plan.md)
- Tareas: [`005-tareas.md`](./005-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
