# GUIA DE PARTES DE STREAMLIT

```
┌─────────────────────────────────────────────────────────┐
│  BARRA SUPERIOR (streamlit)                              │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  SIDEBAR     │         PAGINA (contenido principal)     │
│  (barra      │                                          │
│   lateral)   │  ┌──────────────────────────────────┐    │
│              │  │  TITULO (st.title)               │    │
│  ┌────────┐  │  │  st.caption / st.markdown        │    │
│  │ LOGO   │  │  ├──────────────────────────────────┤    │
│  ├────────┤  │  │  METRICAS (st.metric)            │    │
│  │ MENU   │  │  │  [ 9,198 ] [ 1,725 ] [ 18.8% ]  │    │
│  │  Item1 │  │  ├──────────────────────────────────┤    │
│  │  Item2 │  │  │  TABLAS (st.dataframe)           │    │
│  │  Item3 │  │  │  ┌──────┬──────┬──────┐          │    │
│  ├────────┤  │  │  │      │      │      │          │    │
│  │ USUARIO│  │  │  ├──────┼──────┼──────┤          │    │
│  │ LOGOUT │  │  │  │      │      │      │          │    │
│  └────────┘  │  │  └──────┴──────┴──────┘          │    │
│              │  ├──────────────────────────────────┤    │
│              │  │  TABS (st.tabs)                  │    │
│              │  │  ┌──────┬──────┬──────┐          │    │
│              │  │  │ Tab1 │ Tab2 │ Tab3 │          │    │
│              │  │  ├──────┴──────┴──────┤          │    │
│              │  │  │ contenido del tab  │          │    │
│              │  │  └────────────────────┘          │    │
│              │  ├──────────────────────────────────┤    │
│              │  │  FORMULARIO (st.form)            │    │
│              │  │  ┌────────────────────────┐      │    │
│              │  │  │ st.text_input          │      │    │
│              │  │  │ st.selectbox           │      │    │
│              │  │  │ st.date_input          │      │    │
│              │  │  │ [st.form_submit_button]│      │    │
│              │  │  └────────────────────────┘      │    │
│              │  ├──────────────────────────────────┤    │
│              │  │  EXPANDER (st.expander)          │    │
│              │  │  ┌ Editar Operador ▾ ──────┐     │    │
│              │  │  │ contenido ocultable      │     │    │
│              │  │  └──────────────────────────┘     │    │
│              │  ├──────────────────────────────────┤    │
│              │  │  BOTONES (st.button)             │    │
│              │  │  [Guardar] [Cancelar]            │    │
│              │  ├──────────────────────────────────┤    │
│              │  │  MENSAJES                        │    │
│              │  │  ✅ st.success / ❌ st.error     │    │
│              │  │  ⚠️ st.warning / ℹ️ st.info      │    │
│              │  └──────────────────────────────────┘    │
└──────────────┴──────────────────────────────────────────┘
```

## NOMBRES PARA COMUNICARNOS

| Lo que ves | Como lo llamamos |
|-----------|-----------------|
| Barra izquierda con menú | **Sidebar** |
| Cada página del menú | **Página** (1_Gestion, 2_Backups...) |
| Pestañas dentro de una página | **Tabs** |
| Tabs dentro de otro tab | **Sub-tabs** |
| Campos para escribir | **Inputs** (text_input, selectbox, date_input) |
| Grupo de inputs con botón | **Formulario** (st.form) |
| Sección que se abre/cierra | **Expander** |
| Tabla de datos | **Dataframe** |
| Números grandes (9,198) | **Métricas** |
| Badge verde/amarillo de backup | **Badge de versión** |
| Mensaje verde de éxito | **Success** |
| Mensaje rojo de error | **Error** |
| Menú principal del .bat | **Menú del lanzador** |
