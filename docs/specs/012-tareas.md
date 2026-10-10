# Tareas 012 — Inicialización Resiliente de Usuarios y Auditoría en Base de Datos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`012-spec.md`](./012-spec.md)                     |
| Plan    | [`012-plan.md`](./012-plan.md)                     |
| Rama    | `fix/auto-inicializacion-db-usuarios`              |
| Estado  | completado                                         |

## Lista de tareas

- [x] **T-01:** Añadir prueba unitaria en `tests/test_autenticacion.py` que compruebe la creación automática de tablas y usuario `admin` en motor en blanco.
- [x] **T-02:** Implementar `asegurar_tablas()` en `src/certificado_operadores/infra/usuarios_repository.py` con DDL de `dim_usuarios` y `log_auditoria`, más siembra automática de `admin` si la tabla está vacía.
- [x] **T-03:** Invocar `asegurar_tablas()` en el constructor de `UsuariosRepository`.
- [x] **T-04:** Actualizar `scripts/cargar_excel_a_sqlite.py` para usar `data/Modelo_Estrella_Final_CSVs`.
- [x] **T-05:** Ejecutar `uv run pytest` y confirmar 100% de pruebas en verde.
- [x] **T-06:** Actualizar `docs/referencia-funciones.md` con el nuevo método `asegurar_tablas`.
