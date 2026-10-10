# Spec 009 — Refactorización UI: Reporte de Comportamientos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-reporte-comportamientos`          |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/9_Reporte_Comportamientos.py` (561 líneas) gestiona el registro individual de comportamientos, carga masiva desde Excel y reporte de reincidencia, mezclando la vista de Streamlit con consultas y mutaciones SQL directas a `fact_eventos_operador`, `dim_detalle_comportamiento`, `dim_codigo` y `dim_persona`.
Actualmente, la página `src/certificado_operadores/pages/2_Administracion_Operadores.py` lo invoca como el último `exec` remanente de la página en la pestaña 3: `exec(Path("modulos/9_Reporte_Comportamientos.py").read_text(encoding="utf-8"), globals())`.

## 2. Objetivos

- Extraer la vista a una carpeta modular exclusiva: `src/certificado_operadores/modulos/reporte_comportamientos/ui.py` con la función `render_reporte_comportamientos()`.
- Encapsular las consultas de comportamientos, reincidencia y validación de carga masiva en una capa de repositorio/infraestructura (`comportamientos_repository.py` o Facade).
- En `src/certificado_operadores/pages/2_Administracion_Operadores.py`, reemplazar la llamada `exec(...)` de la pestaña 3 por la importación limpia: `from modulos.reporte_comportamientos.ui import render_reporte_comportamientos`.
- Culminar la Fase 2: `pages/2_Administracion_Operadores.py` queda 100% libre de `exec` y 100% desacoplada.
- Proveer pruebas unitarias con `pytest` en `tests/test_reporte_comportamientos.py`.

## 3. No-objetivos

- No modificar la lógica ni los umbrales de reincidencia.

## 4. Requisitos funcionales

- **RF-01 (Registro Individual):** Búsqueda de operador por cédula o código activo, selección de jerarquía de comportamiento, fecha/hora y registro del evento con auditoría.
- **RF-02 (Carga Masiva):** Procesamiento y validación de archivo Excel de comportamientos, verificando códigos existentes y columnas requeridas.
- **RF-03 (Reincidencia):** Consulta y visualización del reporte de reincidencia de comportamientos por operador.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero sentencias SQL en `modulos/reporte_comportamientos/ui.py`.
- **RNF-02 (Arquitectura):** Se elimina el último `exec` en `pages/2_Administracion_Operadores.py`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/reporte_comportamientos/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/2_Administracion_Operadores.py` invoca `render_reporte_comportamientos()` sin ningún `exec`.
- [ ] **CA-03:** Las consultas y mutaciones de datos se ejecutan a través de la capa de infraestructura / repositorio.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`009-plan.md`](./009-plan.md)
- Tareas: [`009-tareas.md`](./009-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
