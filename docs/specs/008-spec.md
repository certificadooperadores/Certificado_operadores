# Spec 008 — Refactorización UI: Gestion Certificados

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-gestion-certificados`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/6_Gestion_Certificados.py` gestiona el registro manual y por lote (Excel) de eventos e historial de certificaciones de operadores, mezclando la vista de Streamlit con más de 15 consultas SQL directas y transacciones a `fact_eventos_operador`, `dim_codigo` y `dim_persona`.
Actualmente, la página `src/certificado_operadores/pages/2_Administracion_Operadores.py` lo invoca en la pestaña 2 usando el antipatrón `exec(Path("modulos/6_Gestion_Certificados.py").read_text(encoding="utf-8"), globals())`.

## 2. Objetivos

- Extraer la vista a una estructura modular dedicada: `src/certificado_operadores/modulos/gestion_certificados/ui.py` con la función `render_gestion_certificados()`.
- Encapsular las consultas y mutaciones de eventos/certificados en la capa de datos/repositorio (`certificados_repository.py` o repositorios existentes de infraestructura).
- En `src/certificado_operadores/pages/2_Administracion_Operadores.py`, reemplazar la llamada `exec(...)` de la pestaña 2 por la importación limpia: `from modulos.gestion_certificados.ui import render_gestion_certificados`.
- Proveer pruebas unitarias con `pytest` en `tests/test_gestion_certificados.py`.

## 3. No-objetivos

- No refactorizar la pestaña 3 ("Reporte de Comportamientos"), la cual se abordará en la Spec 009.

## 4. Requisitos funcionales

- **RF-01 (Búsqueda):** Buscar operador por cédula o código de operación, validando que el operador esté activo.
- **RF-02 (Registro Individual):** Registrar eventos de certificación, validando fechas, evaluadores y vehículos, registrando auditoría.
- **RF-03 (Carga Masiva):** Procesar archivo Excel con validación de columnas, filas y códigos de operador antes de registrar eventos.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero sentencias SQL en `modulos/gestion_certificados/ui.py`.
- **RNF-02 (Arquitectura):** Se elimina el `exec` de la pestaña 2 en `pages/2_Administracion_Operadores.py`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/gestion_certificados/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/2_Administracion_Operadores.py` invoca `render_gestion_certificados()` sin usar `exec` en la pestaña 2.
- [ ] **CA-03:** Las consultas y mutaciones de base de datos se ejecutan a través de la capa de infraestructura / repositorio.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`008-plan.md`](./008-plan.md)
- Tareas: [`008-tareas.md`](./008-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
