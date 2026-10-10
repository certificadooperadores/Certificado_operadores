# Tareas 017 — Editor Seguro Tipo Excel con Listas Desplegables e Integridad Referencial

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`017-spec.md`](./017-spec.md)                     |
| Plan    | [`017-plan.md`](./017-plan.md)                     |
| Rama    | `feat/editor-excel-seguro`                         |
| Estado  | en progreso                                        |

## Lista de tareas

- [ ] **T-01:** Implementar en `eventos_repository.py` los métodos de validación de dependencias de operadores y existencia de códigos.
- [ ] **T-02:** Configurar `st.data_editor` en `modulos/correccion_registros/ui.py` con `column_config` (SelectboxColumn para estados y catálogos, columnas de auditoría protegidas).
- [ ] **T-03:** Añadir flujo transaccional con botón "💾 Guardar Cambios" que valide dependencias y registre auditoría.
- [ ] **T-04:** Bloquear borrado de registros con hijos dependientes mostrando mensaje preventivo.
- [ ] **T-05:** Actualizar pruebas en `tests/test_correccion_registros.py` y asegurar 100% verde con `uv run pytest`.
- [ ] **T-06:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
