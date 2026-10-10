# Spec 018 — Perfeccionamiento de Corrección de Registros: Filtros, Listas Oficiales, Tabla Códigos y Acciones en Bloque

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/perfeccionamiento-correccion-registros`      |
| Relaciona | `015-spec.md` (Pestañas), `017-spec.md` (Editor Excel) |

## 1. Contexto y problema

Tras revisar la implementación de la Spec 017, el usuario detectó las siguientes oportunidades de mejora funcional:
1. **Filtro no visible:** No se incluyó la barra de búsqueda rápida encima de la tabla para filtrar registros.
2. **Licencias:** La columna `Tipo` debe ser una lista desplegable con las categorías oficiales de conducción colombianas: `["C1", "C2", "C3"]`.
3. **Comportamientos:** Las columnas `Fuente` y `Descripción` deben ser listas desplegables con las opciones oficiales de la base de datos (no texto libre).
4. **Tabla Códigos ausente:** Falta la sub-pestaña **Códigos** (`dim_codigo`) que muestre Código, Cédula, Nombre, Empresa, fecha desde cuándo funciona (`fecha_registro`) y Estado.
5. **Acciones en bloque:** Se requieren de vuelta los botones para mutar en bloque varias filas seleccionadas a la vez (`Vigente`, `Anulado`, `Eliminar`), conviviendo armónicamente con el botón `Guardar Cambios` del editor.

## 2. Objetivos y Requisitos

1. **Buscador Rápido Visible (Filtro):**
   - Incorporar en cada sub-pestaña una barra horizontal:
     `st.text_input("🔍 Filtrar tabla:", placeholder="Buscar por código, cédula, nombre, evento, fecha o estado...", key=f"filtro_{clave}")`
   - Si tiene texto, filtra el DataFrame en memoria antes de renderizar el editor.
2. **Listas Desplegables Oficiales:**
   - **Licencias:** Columna `Tipo` como `SelectboxColumn` con `["C1", "C2", "C3"]`.
   - **Comportamientos:**
     - Columna `Fuente` como `SelectboxColumn` con fuentes oficiales del catálogo.
     - Columna `Descripción` como `SelectboxColumn` con descripciones de `dim_detalle_comportamiento`.
3. **Sub-pestaña Códigos (`dim_codigo`):**
   - Agregar `Códigos` a `TABLAS_CORRECCION` con:
     - `Código` (`id_codigo`)
     - `Cédula` (`id_persona`)
     - `Nombre` (Nombre del operador)
     - `Empresa` (`dim_empresa.nombre_empresa`)
     - `Desde` (`fecha_registro`)
     - `Estado` (`vigente` / `anulado`)
4. **Acciones en Bloque + Edición Excel:**
   - La tabla permite seleccionar múltiples filas (`selection_mode="multi-row"` / `num_rows="dynamic"`).
   - Botones horizontales de acción en bloque:
     - `Marcar Vigente (Seleccionados)`
     - `Marcar Anulado (Seleccionados)`
     - `Eliminar (Seleccionados)` (solo Super Administrador y sin hijos dependientes).
   - Botón `💾 Guardar Cambios` para persistir modificaciones celda por celda.
5. **Pruebas Unitarias:**
   - 100% de pruebas en verde con `uv run pytest`.

## 3. Criterios de aceptación (verificables)

- [ ] **CA-01:** Existe un buscador rápido funcional en cada tabla.
- [ ] **CA-02:** Licencias tiene desplegable con `C1`, `C2`, `C3`.
- [ ] **CA-03:** Comportamientos tiene desplegables para Fuente y Descripción.
- [ ] **CA-04:** Existe la sub-pestaña Códigos con fecha de vigencia y operador.
- [ ] **CA-05:** Los botones de acción en bloque mutan el estado de las filas seleccionadas.
- [ ] **CA-06:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`018-plan.md`](./018-plan.md)
- Tareas: [`018-tareas.md`](./018-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
