# Spec 010 — Refactorización UI: Reportes y Exportaciones

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-reportes`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/10_Reportes.py` (342 líneas) genera reportes consolidados (UTRYT, historial, etc.) y exportaciones Excel/CSV, mezclando la vista de Streamlit con consultas SQL dinámicas (`SELECT dc.id_codigo ...`) y registro directo de auditoría.
Actualmente, la página `src/certificado_operadores/pages/3_Reportes.py` lo invoca como un cascarón con `exec(open("modulos/10_Reportes.py").read(), globals())`.

## 2. Objetivos

- Extraer la vista a una carpeta modular exclusiva: `src/certificado_operadores/modulos/reportes/ui.py` con la función `render_reportes()`.
- Encapsular la construcción de reportes, consultas de empresas, tipologías y exportaciones en una capa de repositorio/infraestructura (`reportes_repository.py` o Facade).
- En `src/certificado_operadores/pages/3_Reportes.py`, reemplazar la llamada `exec(...)` por la importación limpia: `from modulos.reportes.ui import render_reportes`.
- Culminar la Fase 3: la página `3_Reportes.py` queda 100% libre de `exec` y 100% desacoplada, completando la refactorización de todas las páginas maestras del sistema.
- Proveer pruebas unitarias con `pytest` en `tests/test_reportes.py`.

## 3. No-objetivos

- No alterar las columnas requeridas por el formato UTRYT.

## 4. Requisitos funcionales

- **RF-01:** Obtener opciones de filtros para empresas, estados y tipologías de operadores.
- **RF-02:** Consultar datos para reportes consolidados (UTRYT y otros) con filtros dinámicos.
- **RF-03:** Generar descargas en formato Excel y CSV con registro de auditoría.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero sentencias SQL en `modulos/reportes/ui.py` ni en `pages/3_Reportes.py`.
- **RNF-02 (Arquitectura):** Se elimina el `exec` de `pages/3_Reportes.py`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/reportes/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/3_Reportes.py` invoca `render_reportes()` sin ninguna llamada a `exec`.
- [ ] **CA-03:** Todas las consultas SQL de generación de reportes se ejecutan a través de la capa de infraestructura / repositorio.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`010-plan.md`](./010-plan.md)
- Tareas: [`010-tareas.md`](./010-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
