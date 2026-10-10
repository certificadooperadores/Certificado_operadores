# Spec 019 — Columnas Completas de Negocio para la Tabla de Eventos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/columnas-completas-eventos`                  |
| Relaciona | `018-spec.md` (Corrección de Registros)            |

## 1. Contexto y problema

Al revisar la tabla `fact_eventos_operador`, se constató que la configuración de la sub-pestaña **Eventos** omitía columnas de negocio críticas de Metrocali:
- Fechas de certificado, retiro, notificación de retiro, suspensión y prueba.
- Evaluador y vehículo evaluado.
- Observaciones oficiales (oficios, motivos de retiro, etc.).

El usuario requiere que la tabla de Eventos exponga y permita editar todas estas columnas en el editor tipo Excel.

## 2. Definición Detallada de Columnas

### Columnas Visibles y Editables en Eventos:
1. `Código` (`e.id_codigo`): editable con validación en `dim_codigo`.
2. `Cédula` (`c.id_persona`): solo lectura (identificación del operador).
3. `Nombre` (Nombre completo del operador): solo lectura.
4. `Evento` (`te.nombre_evento`): editable con `SelectboxColumn` de tipos de evento.
5. `Fecha Certificado` (`e.fecha_certificado`): editable formato fecha.
6. `Fecha Retiro` (`e.fecha_retiro`): editable formato fecha.
7. `Fecha Notif. Retiro` (`e.fecha_notificacion_retiro`): editable formato fecha.
8. `Fecha Suspensión` (`e.fecha_suspension`): editable formato fecha.
9. `Fecha Prueba` (`e.fecha_prueba`): editable formato fecha.
10. `Evaluador` (`e.evaluador`): editable texto.
11. `Vehículo Evaluado` (`e.id_vehiculo_evaluado`): editable número.
12. `Observación` (`e.observacion`): editable texto.
13. `Registro` (`e.fecha_registro`): solo lectura.
14. `Estado` (`e.id_vigencia`): editable con `SelectboxColumn` (`vigente` / `anulado`).

## 3. Criterios de Aceptación (verificables)

- [ ] **CA-01:** La definición de la tabla `eventos` incluye todas las columnas de fechas (`certificado`, `retiro`, `notificación`, `suspensión`, `prueba`), evaluador, vehículo y observación.
- [ ] **CA-02:** Los campos correspondientes son editables en `st.data_editor` y persisten correctamente en `fact_eventos_operador`.
- [ ] **CA-03:** Pruebas unitarias en `tests/test_correccion_registros.py` cubren la presencia y edición de las nuevas columnas.
- [ ] **CA-04:** `uv run pytest` pasa 100% en verde.

## 10. Enlaces

- Plan: [`019-plan.md`](./019-plan.md)
- Tareas: [`019-tareas.md`](./019-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
