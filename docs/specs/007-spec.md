# Spec 007 — Refactorización UI: Catalogos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-catalogos`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/4_Catalogos.py` gestiona cinco catálogos del sistema (`dim_empresa`, `dim_vehiculo`, `dim_impacto`, `dim_comportamiento`, `dim_detalle_comportamiento`) mezclando la interfaz de Streamlit con más de 20 consultas SQL directas (`SELECT`, `INSERT`, `UPDATE`).
Actualmente, la página `src/certificado_operadores/pages/1_Configuracion.py` lo invoca como el último `exec` remanente: `exec(open("modulos/4_Catalogos.py").read(), globals())`.

## 2. Objetivos

- Extraer la lógica visual a una carpeta modular exclusiva: `src/certificado_operadores/modulos/catalogos/ui.py` con la función `render_catalogos()`.
- Crear una capa de acceso a datos (`src/certificado_operadores/infra/catalogos_repository.py` o Facade) que encapsule las operaciones CRUD de los cinco catálogos.
- En `src/certificado_operadores/pages/1_Configuracion.py`, reemplazar la llamada `exec(open("modulos/4_Catalogos.py").read(), globals())` por la importación limpia: `from modulos.catalogos.ui import render_catalogos`.
- Completar la Fase 1: `pages/1_Configuracion.py` queda 100% libre de `exec` y 100% desacoplada.
- Crear pruebas unitarias con `pytest` en `tests/test_catalogos.py`.

## 3. No-objetivos

- No modificar la lógica de validación de negocio ni los identificadores de tablas.

## 4. Requisitos funcionales

- **RF-01:** Listar, crear, activar/inactivar y renombrar empresas (`dim_empresa`).
- **RF-02:** Listar, crear y renombrar vehículos (`dim_vehiculo`).
- **RF-03:** Listar, crear y renombrar niveles de impacto (`dim_impacto`).
- **RF-04:** Listar, crear y renombrar tipos de comportamientos (`dim_comportamiento`).
- **RF-05:** Listar, crear y renombrar detalles de comportamientos (`dim_detalle_comportamiento`).

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero sentencias SQL en `modulos/catalogos/ui.py` ni en `pages/1_Configuracion.py`.
- **RNF-02 (Arquitectura):** Se elimina el último `exec` de `pages/1_Configuracion.py`.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/catalogos/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/1_Configuracion.py` no contiene ninguna llamada a `exec`; importa y llama a `render_catalogos()`.
- [ ] **CA-03:** Todas las operaciones de catálogos están desacopladas en el repositorio.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`007-plan.md`](./007-plan.md)
- Tareas: [`007-tareas.md`](./007-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
