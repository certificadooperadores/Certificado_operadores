# Spec 006 — Refactorización UI: Modificacion Tablas

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-modificacion-tablas`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

En `src/certificado_operadores/pages/1_Configuracion.py`, la pestaña "🗑️ Corrección de Registros" tiene incrustadas más de 140 líneas de código visual y consultas SQL crudas directas (`modulo_correccion`, `correccion_individual`, `correccion_lote`) con sentencias `SELECT`, `UPDATE` y `DELETE` sobre `fact_eventos_operador`.
Adicionalmente, existe el archivo huérfano heredado `src/certificado_operadores/modulos/3_Modificacion_Tablas.py` que duplica parcialmente esta misma lógica con acceso directo a base de datos.

## 2. Objetivos

- Extraer toda la lógica visual de corrección de registros a un módulo dedicado: `src/certificado_operadores/modulos/correccion_registros/ui.py` con la función `render_correccion_registros()`.
- Crear una capa de datos/repositorio (`eventos_repository.py` o Facade) que encapsule la búsqueda de eventos, tipos de eventos, reactivación, anulación y eliminación de lotes o registros individuales.
- Eliminar de `src/certificado_operadores/pages/1_Configuracion.py` las funciones inlined `modulo_correccion`, `correccion_individual` y `correccion_lote`, llamando en su lugar a `render_correccion_registros()`.
- Retirar/deprecar el archivo duplicado `src/certificado_operadores/modulos/3_Modificacion_Tablas.py`.
- Añadir pruebas unitarias con `pytest` en `tests/test_correccion_registros.py`.

## 3. No-objetivos

- No refactorizar la pestaña de Catálogos (se abordará en Spec 007).

## 4. Requisitos funcionales

- **RF-01 (Registro Individual):** Filtrar eventos por código, cédula, tipo de evento, estado y rango de fechas. Permitir reactivar, anular o eliminar (Super Admin) registros seleccionados.
- **RF-02 (Por Lote):** Listar lotes de eventos agrupados por minuto de cargue y permitir reactivar, anular o eliminar (Super Admin) el lote completo.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** Cero consultas SQL (`SELECT`, `UPDATE`, `DELETE`) en `pages/1_Configuracion.py` ni en `modulos/correccion_registros/ui.py`.
- **RNF-02 (Desacople):** Todo acceso a base de datos pasa por la capa de repositorio / Facade.
- **RNF-03 (Pruebas):** Pruebas unitarias en verde con `make test`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe el paquete `src/certificado_operadores/modulos/correccion_registros/` con `__init__.py` y `ui.py`.
- [ ] **CA-02:** `pages/1_Configuracion.py` no contiene código SQL crudo ni funciones inlined de corrección; invoca `render_correccion_registros()`.
- [ ] **CA-03:** Las acciones de base de datos se ejecutan a través de un repositorio/Facade con auditoría.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`006-plan.md`](./006-plan.md)
- Tareas: [`006-tareas.md`](./006-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
