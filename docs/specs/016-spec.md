# Spec 016 — Orden Descendente y Barra de Búsqueda Rápida en Tablas de Corrección

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/orden-descendente-y-buscador-tabla`          |
| Relaciona | `015-spec.md` (Corrección de Registros)            |

## 1. Contexto y problema

1. **Orden:** Actualmente los eventos aparecen en orden ascendente (los registros más antiguos primero con ID 1, 2, 3...). El usuario requiere que **los últimos eventos cargados aparezcan siempre de primero** (`ORDER BY id DESC` o fecha más reciente primero).
2. **Filtro visible:** La tabla de Streamlit nativa no incluye una caja de texto visible para filtrar el contenido cargado. Se requiere una **barra de búsqueda rápida de una sola línea** justo encima de la tabla que filtre instantáneamente por cualquier coincidencia (código, cédula, nombre, evento, fecha o estado).

## 2. Objetivos

1. **En `eventos_repository.py`:**
   - Asegurar que todas las consultas de listado de tablas (`listar_eventos`, `listar_licencias`, `listar_comportamientos`, `listar_operadores`) ordenen en forma descendente (`ORDER BY id DESC` o fecha).
2. **En `modulos/correccion_registros/ui.py`:**
   - Incorporar en cada sub-pestaña una barra de búsqueda ultra-compacta de una sola línea:
     `st.text_input("Buscar...", placeholder="Escriba código, cédula, nombre, evento o estado para filtrar...", label_visibility="collapsed")`.
   - Filtrar dinámicamente las filas del DataFrame según el texto ingresado.
   - Presentar la tabla filtrada y ordenada con los más recientes de primero.
3. **Pruebas Unitarias:**
   - Adaptar `tests/test_correccion_registros.py` para validar el orden descendente y la lógica de filtrado.
   - 100% de pruebas en verde.

## 3. Criterios de aceptación

- [ ] **CA-01:** Los registros se listan en orden descendente (los más recientes arriba).
- [ ] **CA-02:** Existe una barra de búsqueda de una sola línea arriba de cada tabla que filtra en tiempo real.
- [ ] **CA-03:** Pruebas unitarias pasan 100% en verde con `uv run pytest`.

## 10. Enlaces

- Plan: [`016-plan.md`](./016-plan.md)
- Tareas: [`016-tareas.md`](./016-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
