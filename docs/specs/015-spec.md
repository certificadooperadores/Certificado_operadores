# Spec 015 — Rediseño Compacto de Corrección de Registros por Tablas

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/rediseno-correccion-registros`               |
| Relaciona | `006-spec.md` (Corrección de Registros)            |

## 1. Contexto y problema

La interfaz anterior de `Corrección de Registros` dividía la pantalla en "Registro Individual" y "Por Lote", y utilizaba dos filas completas con 6 campos de filtro voluminosos (Código, Cédula, Tipo, Estado, Fechas) que ocupaban casi la mitad de la pantalla y limitaban la visualización de datos.

Requerimiento del usuario:
1. Eliminar la división "Registro Individual" y "Por Lote".
2. Organizar la vista mediante **sub-pestañas por tabla del sistema**:
   - **Eventos** (`fact_eventos_operador`)
   - **Licencias** (`fact_licencias`)
   - **Comportamientos** (`fact_comportamiento`)
   - **Operadores** (`dim_persona`)
3. Eliminar los formularios externos gigantes. Usar las capacidades de filtrado y búsqueda nativas en la misma tabla (`st.dataframe` con `use_container_width=True` y selección múltiple de filas mediante `on_select="rerun"` / `selection_mode="multi-row"`).
4. Permitir aplicar acciones inmediatas (cambiar de estado: `Vigente/Activo`, `Anulado/Inactivo` o `Eliminar`) sobre una o varias filas seleccionadas a la vez.

## 2. Objetivos

1. **Capa de Infraestructura (`eventos_repository.py` y repositorios):**
   - Asegurar métodos de consulta compacta y actualización por lote de IDs para las tablas soportadas.
2. **Capa UI (`modulos/correccion_registros/ui.py`):**
   - Reemplazar las pestañas "Registro Individual / Por Lote" por sub-tabs temáticas de tablas.
   - En cada sub-tab, renderizar directamente la tabla interactiva sin bloques externos de formulario.
   - Habilitar selección de filas (individual o múltiple).
   - Colocar una barra de herramientas horizontal compacta con botones de acción directa:
     - `Reactivar / Vigente`
     - `Anular / Inactivo`
     - `Eliminar`
   - Al ejecutar la acción, aplicar la mutación sobre los IDs seleccionados, registrar auditoría y refrescar la tabla.
3. **Pruebas Unitarias:**
   - Adaptar `tests/test_correccion_registros.py` para validar la lógica del nuevo flujo.
   - 100% de pruebas verdes.

## 3. Criterios de aceptación

- [ ] **CA-01:** La interfaz organiza la corrección en sub-tabs por tabla.
- [ ] **CA-02:** No existen bloques externos masivos de filtros encima de la tabla.
- [ ] **CA-03:** La tabla soporta selección de filas individual o en grupo.
- [ ] **CA-04:** Los botones permiten cambiar de estado o eliminar los registros seleccionados.
- [ ] **CA-05:** Pruebas unitarias pasan 100% en verde con `uv run pytest`.

## 10. Enlaces

- Plan: [`015-plan.md`](./015-plan.md)
- Tareas: [`015-tareas.md`](./015-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
