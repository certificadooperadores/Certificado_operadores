# Plan 014 — Restauración de Backups con Comparación Preventiva de Registros

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`014-spec.md`](./014-spec.md)         |
| Tareas    | [`014-tareas.md`](./014-tareas.md)     |
| Rama      | `feat/restauracion-backups-comparacion`|
| Enfoque   | TDD (red-green-refactor) + Clean Architecture |

## 1. Diseño técnico

1. **Constante de tablas a comparar:**
   ```python
   TABLAS_COMPARACION: tuple[str, ...] = (
       "dim_persona",
       "dim_codigo",
       "fact_licencias",
       "fact_eventos_operador",
       "fact_comportamiento",
       "dim_usuarios",
   )
   ```

2. **Lógica de `comparar_backup` en `BackupService`:**
   - Abre conexión a `self.origen_db` y a `self._ruta(nombre_backup)`.
   - Consulta `SELECT COUNT(*) FROM tabla` en ambas bases (manejando tablas que no existan como 0).
   - Genera filas: `{"Tabla": t, "Actual": c_act, "Respaldo": c_bak, "Diferencia": c_bak - c_act}`.

3. **Lógica de `restaurar_backup` en `BackupService`:**
   - Si `crear_respaldo_seguridad`: ejecuta `self.crear_backup()`.
   - Ejecuta `_copiar_con_sqlite(self._ruta(nombre_backup), self.origen_db)`.
   - Inserta fila en `dim_version_bd`:
     ```sql
     INSERT INTO dim_version_bd (fecha_backup, archivo_origen, restaurado_por)
     VALUES (:fecha, :archivo, :usuario);
     ```

4. **Integración UI en `modulos/administrar_backups/ui.py`:**
   - Subsección "Restaurar Copia de Seguridad".
   - `selectbox` de backups disponibles.
   - Botón "Analizar Diferencias" que muestra `st.dataframe` comparativo.
   - Botón `st.button("⚠️ Confirmar y Restaurar Base de Datos")` que ejecuta la restauración y limpia cachés.
