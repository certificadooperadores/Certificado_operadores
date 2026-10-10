# Plan 017 — Editor Seguro Tipo Excel con Listas Desplegables e Integridad Referencial

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`017-spec.md`](./017-spec.md)         |
| Tareas    | [`017-tareas.md`](./017-tareas.md)     |
| Rama      | `feat/editor-excel-seguro`             |
| Enfoque   | Clean Architecture + Seguridad de Datos |

## 1. Diseño técnico

1. **Capa de Infraestructura (`src/certificado_operadores/infra/eventos_repository.py`):**
   - Método `contar_dependencias_operador(id_persona: int, id_codigo: int | None = None) -> dict[str, int]`:
     - Consulta conteos en `fact_eventos_operador`, `fact_comportamiento` y `fact_licencias`.
   - Método `validar_codigo_existe(id_codigo: int) -> bool`:
     - Comprueba si el código existe en `dim_codigo`.
   - Método `actualizar_registros_seguros(...)`:
     - Valida las reglas de seguridad antes de ejecutar UPDATE.
     - Aplica transacción con `begin()` y audita.

2. **Capa UI (`src/certificado_operadores/modulos/correccion_registros/ui.py`):**
   - Configuración de `st.data_editor` por tabla:
     - `column_config` con `st.column_config.SelectboxColumn` para:
       - Estado: `options=["vigente", "anulado"]`.
       - Evento: `options=tipos_evento`.
     - `disabled=["ID", "Fecha Registro", "Usuario Registra"]`.
   - Botón explícito: **"💾 Guardar Cambios"**.
   - Procesa `st.session_state` de celdas modificadas, valida reglas de negocio con el backend y reporta resultados o errores controlados.
