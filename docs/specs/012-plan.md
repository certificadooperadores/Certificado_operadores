# Plan 012 — Inicialización Resiliente de Usuarios y Auditoría en Base de Datos

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`012-spec.md`](./012-spec.md)         |
| Tareas    | [`012-tareas.md`](./012-tareas.md)     |
| Rama      | `fix/auto-inicializacion-db-usuarios`  |
| Enfoque   | TDD (red-green-refactor) + Clean Architecture |

## 1. Arquitectura y diseño

1. **Capa de Infraestructura (`src/certificado_operadores/infra/usuarios_repository.py`):**
   - Incorporar constantes DDL:
     - `_SQL_CREAR_TABLA_USUARIOS`:
       ```sql
       CREATE TABLE IF NOT EXISTS dim_usuarios (
           id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
           usuario TEXT UNIQUE NOT NULL,
           password_hash TEXT NOT NULL,
           rol TEXT NOT NULL,
           estado TEXT NOT NULL,
           fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       );
       ```
     - `_SQL_CREAR_TABLA_LOGS`:
       ```sql
       CREATE TABLE IF NOT EXISTS log_auditoria (
           id_log INTEGER PRIMARY KEY AUTOINCREMENT,
           usuario TEXT NOT NULL,
           accion TEXT NOT NULL,
           detalles TEXT,
           fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       );
       ```
     - `_SQL_CONTEO_USUARIOS`:
       ```sql
       SELECT COUNT(*) FROM dim_usuarios;
       ```
   - Implementar el método público o de inicialización `asegurar_tablas(self) -> None`:
     - Ejecuta las sentencias DDL dentro de una transacción.
     - Si el conteo de usuarios es 0, genera el hash con `hashear_contrasena("admin123")` e inserta al usuario `admin`.
   - Llamar a `self.asegurar_tablas()` en el constructor `__init__` de `UsuariosRepository`.

2. **Capa de Scripts (`scripts/cargar_excel_a_sqlite.py`):**
   - Actualizar la ruta por defecto del directorio de CSVs:
     ```python
     csv_dir = os.path.join(BASE_DIR, "data", "Modelo_Estrella_Final_CSVs")
     ```
   - Garantizar que si existe `data/Modelo_Estrella_Final_CSVs`, cargue los datos a `operadores.db`.

3. **Capa de Pruebas (`tests/test_autenticacion.py`):**
   - Agregar caso de prueba `test_usuarios_repository_auto_crea_tablas_y_admin_en_motor_vacio`:
     - Se inicializa un motor en memoria `create_engine("sqlite:///:memory:")`.
     - Se instancia `UsuariosRepository(engine)`.
     - Se verifica que la tabla `dim_usuarios` exista y contenga al usuario `admin`.
     - Se verifica que `UsuariosFacade(UsuariosRepository(engine)).autenticar("admin", "admin123")` devuelva éxito.

## 2. Fases de ejecución

1. **Fase 1 (TDD Red):** Escribir la prueba en `tests/test_autenticacion.py` validando la auto-creación y siembra de `admin` sobre un motor vacío.
2. **Fase 2 (Green):** Implementar `asegurar_tablas()` en `usuarios_repository.py` y actualizar `cargar_excel_a_sqlite.py`.
3. **Fase 3 (Verificación):** Ejecutar `uv run pytest` hasta 100% verde.
4. **Fase 4 (Documentación):** Actualizar `docs/referencia-funciones.md` y `012-tareas.md`.
