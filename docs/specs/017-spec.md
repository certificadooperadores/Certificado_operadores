# Spec 017 — Editor Seguro Tipo Excel con Listas Desplegables e Integridad Referencial

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/editor-excel-seguro`                         |
| Relaciona | `006-spec.md` (Corrección de Registros), `015-spec.md` (Pestañas) |

## 1. Contexto y problema

La edición de registros en bases de datos relacionales sin controles adecuados representa un riesgo severo de corrupción de datos y generación de registros huérfanos.
El usuario requiere:
1. Una experiencia interactiva intuitiva tipo hoja de cálculo (Excel) con **listas desplegables** en las columnas permitidas.
2. **Máxima seguridad e integridad referencial:**
   - No permitir valores arbitrarios fuera de los catálogos oficiales.
   - Bloquear la eliminación de operadores o códigos que tengan eventos o comportamientos asociados.
   - Al editar un código, validar que el nuevo código exista previamente en `dim_codigo`.
   - Proteger llaves primarias y fechas de auditoría para que sean de solo lectura.
   - Transaccionalidad atómica (rollback ante cualquier error) y registro en `log_auditoria`.

## 2. Requisitos de Seguridad

### S-01: Integridad Referencial Anti-Huérfanos
- Antes de permitir la eliminación de cualquier registro de `dim_persona` o `dim_codigo`, el backend ejecuta una consulta de comprobación previa de dependencias en `fact_eventos_operador`, `fact_comportamiento` y `fact_licencias`.
- Si el registro tiene registros dependientes asociados, la operación se **aborta de inmediato** con un mensaje explícito:
  *"No se puede eliminar: el registro tiene X eventos y Y comportamientos dependientes. Debe anularlo o depurar los registros hijos primero."*

### S-02: Reasignación Validada de Códigos
- Si se modifica el campo `Código` en eventos, licencias o comportamientos, el backend valida que el valor ingresado exista en `dim_codigo`. De lo contrario, se cancela la edición con aviso de error.

### S-03: Columnas de Solo Lectura (Protegidas)
- Las llaves primarias internas (`id_hecho_evento`, `id_hecho_comportamiento`, etc.), fechas de creación y el usuario registrador son estrictamente de solo lectura (`disabled=True`).

### S-04: Listas Desplegables Restringidas (`SelectboxColumn`)
- **Estado:** estrictamente `["vigente", "anulado"]` (mapeado a `id_vigencia` 1 y 2).
- **Tipo de Evento:** restringido a los valores de `dim_tipo_evento`.
- **Género:** `["M", "F"]`.

### S-05: Transacciones Atómicas y Auditoría
- Todos los cambios se ejecutan dentro de una transacción con `commit` o `rollback` total.
- Cada modificación se registra en `log_auditoria` con el usuario en sesión y detalle del cambio.

## 3. Criterios de aceptación (verificables)

- [ ] **CA-01:** La UI utiliza `st.data_editor` con columnas protegidas y `SelectboxColumn` para estados y catálogos.
- [ ] **CA-02:** El backend bloquea el borrado de operadores con eventos o comportamientos asociados.
- [ ] **CA-03:** El backend valida la existencia de códigos antes de reasignar.
- [ ] **CA-04:** Las transacciones aplican rollback si ocurre un error y se auditan.
- [ ] **CA-05:** Pruebas unitarias en `tests/test_correccion_registros.py` cubren validaciones y pasan 100% en verde con `uv run pytest`.

## 10. Enlaces

- Plan: [`017-plan.md`](./017-plan.md)
- Tareas: [`017-tareas.md`](./017-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
