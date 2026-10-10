# Spec 020 — Validación, Blindaje y Bloqueo de Campos por Categoría de Evento

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Estado  | aprobada                                                             |
| Autor   | Ing. Miguel Angel Ortiz Roldan                                       |
| Fecha   | 2026-10-10                                                           |
| Rama    | `feat/bloqueo-campos-por-categoria-evento`                           |
| Relaciona | `019-spec.md` (Columnas Completas de Eventos)                      |

## 1. Contexto y problema

Tras exponer la totalidad de las columnas de fechas y observaciones en la tabla `fact_eventos_operador` (Spec 019), el editor permite potencialmente alterar o asignar fechas incongruentes con la naturaleza del evento. Por ejemplo:
- Asignar una `Fecha Retiro` a un evento de `certificación`.
- Asignar una `Fecha Certificado` a un evento de `suspensión` o `cancelación`.
- Dejar residuos de fechas o vehículos anteriores cuando se cambia el tipo de evento.
- Ingresar fechas futuras imposibles o formatos no cronológicos.

En Metrocali, los 33.595 eventos de operadores determinan la habilitación para conducir en el sistema MIO. Una inconsistencia cruzada en estas columnas genera anomalías legales y desvirtúa los reportes de vigencia de certificados.

## 2. Requerimientos de Dominio y Negocio

### S-01: Matriz de Compatibilidad de Campos por Categoría de Evento
Cada registro en `fact_eventos_operador` pertenece a un `id_tipo_evento` en `dim_tipo_evento`. Los campos editables permitidos son estrictamente:

1. **Acreditación / Habilitación (`certificacion`, `renovacion`, `reactivacion` - IDs 1, 3, 2):**
   - Permitidos: `id_codigo`, `id_tipo_evento`, `fecha_certificado`, `fecha_prueba`, `evaluador`, `id_vehiculo_evaluado`, `observacion`.
   - Prohibidos (incompatibles): `fecha_retiro`, `fecha_notificacion_retiro`, `fecha_suspension`.
2. **Novedad de Retiro / Desvinculación (`cancelacion` - ID 7):**
   - Permitidos: `id_codigo`, `id_tipo_evento`, `fecha_retiro`, `fecha_notificacion_retiro`, `observacion`.
   - Prohibidos: `fecha_certificado`, `fecha_prueba`, `evaluador`, `id_vehiculo_evaluado`, `fecha_suspension`.
3. **Sanción / Medida Temporal (`suspension` - ID 6):**
   - Permitidos: `id_codigo`, `id_tipo_evento`, `fecha_suspension`, `observacion`.
   - Prohibidos: `fecha_retiro`, `fecha_notificacion_retiro`, `fecha_certificado`, `fecha_prueba`, `evaluador`, `id_vehiculo_evaluado`.
4. **Salud Ocupacional (`restriccion medica` - ID 5):**
   - Permitidos: `id_codigo`, `id_tipo_evento`, `observacion`.
   - Prohibidos: `fecha_retiro`, `fecha_notificacion_retiro`, `fecha_suspension`, `fecha_certificado`, `fecha_prueba`, `evaluador`, `id_vehiculo_evaluado`.
5. **Bitácora Simple (`observacion` - ID 4):**
   - Permitidos: `id_codigo`, `id_tipo_evento`, `observacion`.
   - Prohibidos: todas las fechas operativas (`fecha_certificado`, `fecha_retiro`, `fecha_notificacion_retiro`, `fecha_suspension`, `fecha_prueba`, `evaluador`, `id_vehiculo_evaluado`).

### S-02: Rechazo Atómico ante Campos Incompatibles
Si en `actualizar_registros()` se intenta asignar un valor no nulo a un campo prohibido para la categoría del evento de la fila, se cancela la transacción lanzando `CampoIncompatibleError` (hereda de `ValueError`), con el mensaje:
> *"El evento de tipo «{nombre_evento}» no admite la columna «{etiqueta}»."*

### S-03: Limpieza Automática al Mutar Tipo de Evento
Si un usuario edita la columna `Evento` (`id_tipo_evento`), el backend debe resetear a `NULL` todos los campos exclusivos que no pertenezcan al nuevo tipo de evento para no dejar datos huérfanos residuales.

### S-04: Plausibilidad de Fechas
Las fechas editadas deben tener formato válido `YYYY-MM-DD` y no pueden ser fechas futuras mayores a la fecha del día actual + 1 día.

### S-05: Adaptación Dinámica en la UI
En la sub-pestaña **Eventos** de `correccion_registros`:
- Cuando el usuario filtre por un tipo de evento específico en la cabecera (ej. `cancelacion`), el `st.data_editor` mostrará únicamente las columnas aplicables a esa categoría, reduciendo el ruido visual.
- Cuando seleccione "Todos", se muestran todas las columnas acompañadas de un mensaje orientativo sobre las restricciones de campos.

## 3. Criterios de Aceptación (verificables)

- [ ] **CA-01:** La excepción `CampoIncompatibleError` y la matriz `CAMPOS_PERMITIDOS_POR_EVENTO` quedan definidas en `eventos_repository.py`.
- [ ] **CA-02:** Intentar guardar una `Fecha Retiro` en un evento de `certificacion` o una `Fecha Certificado` en una `cancelacion` o `suspension` es rechazado con rollback atómico y mensaje descriptivo.
- [ ] **CA-03:** Cambiar el tipo de evento limpia a `NULL` los campos incompatibles del tipo previo.
- [ ] **CA-04:** La UI en `correccion_registros/ui.py` adapta las columnas visibles al filtrar por un tipo de evento específico.
- [ ] **CA-05:** Pruebas unitarias exhaustivas en `tests/test_correccion_registros.py` validan cada restricción de la matriz.
- [ ] **CA-06:** Toda la suite de pruebas (`pytest`) pasa al 100% en verde.

## 4. Enlaces

- Plan: [`020-plan.md`](./020-plan.md)
- Tareas: [`020-tareas.md`](./020-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
