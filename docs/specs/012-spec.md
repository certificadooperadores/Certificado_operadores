# Spec 012 — Inicialización Resiliente de Usuarios y Auditoría en Base de Datos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `fix/auto-inicializacion-db-usuarios`              |
| Relaciona | `004-spec.md` (Usuarios), `011-spec.md` (Autenticación) |

## 1. Contexto y problema

Al arrancar `Inicio.py` e ingresar las credenciales de administrador (`admin` / `admin123`), el sistema arroja la siguiente excepción:
```text
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: dim_usuarios 
[SQL: SELECT usuario, password_hash, rol, estado FROM dim_usuarios WHERE usuario = ?]
```

Causa raíz:
- La capa de infraestructura (`UsuariosRepository`) asume que la tabla `dim_usuarios` ya fue previamente aprovisionada en el motor relacional.
- Si la base de datos local `operadores.db` es nueva o carece de la tabla `dim_usuarios`, el login falla en tiempo de ejecución.
- Adicionalmente, el script auxiliar `scripts/cargar_excel_a_sqlite.py` apunta a rutas obsoletas de CSVs en lugar de `data/Modelo_Estrella_Final_CSVs`.

## 2. Objetivos

1. **Auto-inicialización en Infraestructura:**
   - Incorporar en `src/certificado_operadores/infra/usuarios_repository.py` un método `asegurar_tablas()` invocado al inicializar el repositorio o en su primer uso.
   - Debe ejecutar DDL con `CREATE TABLE IF NOT EXISTS dim_usuarios` y `CREATE TABLE IF NOT EXISTS log_auditoria`.
   - Si la tabla `dim_usuarios` está vacía (0 registros), debe insertar automáticamente el usuario inicial `'admin'` con hash seguro para `'admin123'`, rol `'Super Administrador'` y estado `'Activo'`.
2. **Resiliencia en SQLite:**
   - La aplicación debe ser capaz de arrancar y autenticar al usuario `admin` de forma inmediata, incluso si la base de datos es nueva o no tiene datos iniciales.
3. **Actualización de Scripts:**
   - En `scripts/cargar_excel_a_sqlite.py`, actualizar las rutas de insumos para que tome los archivos CSV desde `data/Modelo_Estrella_Final_CSVs`.
4. **Pruebas Automatizadas:**
   - Agregar pruebas unitarias en `tests/test_autenticacion.py` que verifiquen el arranque contra una base de datos en blanco y la autenticación exitosa de `admin`.
   - Validar que `make test` pase al 100% en verde.

## 3. No-objetivos

- No modificar la interfaz de usuario de Streamlit (`Inicio.py` ni `modulos/gestion_usuarios/ui.py`).
- No alterar las validaciones de dominio de `UsuariosFacade`.

## 4. Requisitos funcionales

- **RF-01:** Si la tabla `dim_usuarios` no existe en la base de datos conectada, el repositorio la crea automáticamente sin errores.
- **RF-02:** Si la tabla `dim_usuarios` está vacía, se siembra de inmediato el registro del usuario `'admin'` con hash bcrypt válido para `'admin123'`, rol `'Super Administrador'` y estado `'Activo'`.
- **RF-03:** Si la tabla `log_auditoria` no existe, el repositorio la crea automáticamente.
- **RF-04:** La autenticación de `admin` con clave `admin123` retorna éxito sin lanzar excepciones `OperationalError`.

## 5. Requisitos no funcionales

- **RNF-01 (Clean Architecture):** La auto-inicialización pertenece a la capa de infraestructura (`usuarios_repository.py`), manteniendo el dominio y la UI completamente desacoplados de detalles de DDL.
- **RNF-02 (Rendimiento e Idempotencia):** `asegurar_tablas()` debe ser idempotente (`CREATE TABLE IF NOT EXISTS`) y no degradar consultas subsecuentes.
- **RNF-03 (Pruebas):** Cobertura unitaria exhaustiva con `pytest`.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** `UsuariosRepository` incluye `asegurar_tablas()` que crea `dim_usuarios` y `log_auditoria` si no existen.
- [ ] **CA-02:** Si la tabla `dim_usuarios` no contiene registros, se inserta el usuario `'admin'` por defecto.
- [ ] **CA-03:** Pruebas unitarias en `tests/test_autenticacion.py` validan que sobre un motor SQLite vacío, `UsuariosFacade().autenticar("admin", "admin123")` es exitoso.
- [ ] **CA-04:** Todas las pruebas pasan en verde con `uv run pytest`.

## 10. Enlaces

- Plan: [`012-plan.md`](./012-plan.md)
- Tareas: [`012-tareas.md`](./012-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
