# Plan 018 — Perfeccionamiento de Corrección de Registros

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`018-spec.md`](./018-spec.md)         |
| Tareas    | [`018-tareas.md`](./018-tareas.md)     |
| Rama      | `feat/perfeccionamiento-correccion-registros` |
| Enfoque   | Clean Architecture + Usabilidad Integral |

## 1. Diseño técnico

1. **Ampliación de `TABLAS_CORRECCION` en `infra/eventos_repository.py`:**
   - Incorporar `DefinicionTabla` para `codigos`:
     - `tabla="dim_codigo"`, `alias="c"`, `columna_id="id_codigo"`.
     - `columnas`: Código, Cédula, Nombre, Empresa, Desde (`fecha_registro`).
     - `desde`: `FROM dim_codigo AS c JOIN dim_persona AS p ON c.id_persona = p.id_persona LEFT JOIN dim_empresa AS e ON c.id_empresa = e.id_empresa`.
   - Constantes de opciones:
     - `OPCIONES_LICENCIA: tuple[str, ...] = ("C1", "C2", "C3")`.
   - Métodos auxiliares en repositorio:
     - `listar_fuentes_comportamiento(self) -> list[str]`.
     - `listar_descripciones_comportamiento(self) -> list[str]`.

2. **Configuración de Columnas en `modulos/correccion_registros/ui.py`:**
   - `SelectboxColumn` para Licencias con `OPCIONES_LICENCIA`.
   - `SelectboxColumn` para Fuentes y Descripciones de Comportamiento.
   - En cada tabla:
     ```python
     busqueda = st.text_input(
         "🔍 Filtrar:",
         placeholder="Escriba código, cédula, nombre, fecha o estado...",
         key=f"filtro_{definicion.clave}",
     )
     ```
   - Si `busqueda`: filtrar filas del DataFrame antes de pasarlo al editor.

3. **Acciones en Bloque y Guardado:**
   - Barra superior con:
     - Botón `Marcar Vigente (Seleccionados)`
     - Botón `Marcar Anulado (Seleccionados)`
     - Botón `Eliminar (Seleccionados)` (solo Super Administrador y sin dependencias).
     - Botón `💾 Guardar Cambios en Celdas`
