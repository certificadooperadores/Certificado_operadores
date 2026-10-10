# Plan 015 — Rediseño Compacto de Corrección de Registros por Tablas

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`015-spec.md`](./015-spec.md)         |
| Tareas    | [`015-tareas.md`](./015-tareas.md)     |
| Rama      | `feat/rediseno-correccion-registros`  |
| Enfoque   | Clean Architecture + UI optimizada en espacio |

## 1. Diseño de Interfaz

En `src/certificado_operadores/modulos/correccion_registros/ui.py`:

1. **Sub-tabs principales:**
   ```python
   tab_eventos, tab_licencias, tab_comportamientos, tab_operadores = st.tabs([
       "Eventos", "Licencias", "Comportamientos", "Operadores"
   ])
   ```

2. **Estructura dentro de cada pestaña:**
   - Barra de acciones superior compacta:
     - Contador de seleccionados: `X filas seleccionadas`.
     - Botones horizontales: `Reactivar / Vigente`, `Anular / Inactivo`, `Eliminar`.
   - `st.dataframe` con `selection_mode="multi-row"`, `on_select="rerun"`, `use_container_width=True`.
   - La tabla de Streamlit ya incluye su barra integrada de búsqueda y ordenamiento por columna, eliminando todos los filtros externos redundantes.

3. **Ejecución y mutación:**
   - Recuperar índices/IDs seleccionados de `event.selection.rows`.
   - Invocar repositorio correspondiente (`mutar_vigencia` o `eliminar_registros`).
   - `st.success(...)` y `st.rerun()`.
