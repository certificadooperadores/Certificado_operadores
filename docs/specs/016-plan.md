# Plan 016 — Orden Descendente y Barra de Búsqueda Rápida en Tablas de Corrección

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`016-spec.md`](./016-spec.md)         |
| Tareas    | [`016-tareas.md`](./016-tareas.md)     |
| Rama      | `feat/orden-descendente-y-buscador-tabla` |
| Enfoque   | Clean Architecture + Usabilidad compacta |

## 1. Diseño técnico

1. **Orden Descendente en Repositorio (`src/certificado_operadores/infra/eventos_repository.py`):**
   - Asegurar que las consultas de listado finalicen con `ORDER BY id DESC` (o fecha descendente), garantizando que los registros recién insertados figuren en las primeras filas.
2. **Buscador en Memoria (`src/certificado_operadores/modulos/correccion_registros/ui.py`):**
   - Antes de cada tabla, renderizar un campo de entrada horizontal:
     ```python
     busqueda = st.text_input(
         "Buscar",
         placeholder="🔍 Escriba código, cédula, nombre, evento o estado para filtrar...",
         key=f"filtro_{nombre_tabla}",
         label_visibility="collapsed",
     )
     ```
   - Si `busqueda` tiene contenido:
     ```python
     termino = busqueda.strip().lower()
     df = df[df.astype(str).apply(lambda row: row.str.lower().str.contains(termino).any(), axis=1)]
     ```
   - Pasar el `df` filtrado a `st.dataframe`.
