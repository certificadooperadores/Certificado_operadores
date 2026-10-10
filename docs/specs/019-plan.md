# Plan 019 — Columnas Completas de Negocio para la Tabla de Eventos

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`019-spec.md`](./019-spec.md)         |
| Tareas    | [`019-tareas.md`](./019-tareas.md)     |
| Rama      | `feat/columnas-completas-eventos`      |
| Enfoque   | Clean Architecture + Fidelidad del Esquema |

## 1. Diseño técnico

En `src/certificado_operadores/infra/eventos_repository.py`:
- Actualizar la `DefinicionTabla` de `eventos`:
  ```python
  columnas=(
      ColumnaTabla("Código", "e.id_codigo"),
      ColumnaTabla("Cédula", "c.id_persona"),
      ColumnaTabla("Nombre", _NOMBRE_OPERADOR),
      ColumnaTabla("Evento", "te.nombre_evento"),
      ColumnaTabla("Fecha Certificado", "e.fecha_certificado"),
      ColumnaTabla("Fecha Retiro", "e.fecha_retiro"),
      ColumnaTabla("Fecha Notif. Retiro", "e.fecha_notificacion_retiro"),
      ColumnaTabla("Fecha Suspensión", "e.fecha_suspension"),
      ColumnaTabla("Fecha Prueba", "e.fecha_prueba"),
      ColumnaTabla("Evaluador", "e.evaluador"),
      ColumnaTabla("Vehículo Evaluado", "e.id_vehiculo_evaluado"),
      ColumnaTabla("Observación", "e.observacion"),
      ColumnaTabla("Registro", "e.fecha_registro"),
  ),
  editables=(
      ColumnaEditable("Código", "id_codigo", TIPO_EDICION_CODIGO),
      ColumnaEditable("Evento", "id_tipo_evento", TIPO_EDICION_EVENTO),
      ColumnaEditable("Fecha Certificado", "fecha_certificado", TIPO_EDICION_FECHA),
      ColumnaEditable("Fecha Retiro", "fecha_retiro", TIPO_EDICION_FECHA),
      ColumnaEditable("Fecha Notif. Retiro", "fecha_notificacion_retiro", TIPO_EDICION_FECHA),
      ColumnaEditable("Fecha Suspensión", "fecha_suspension", TIPO_EDICION_FECHA),
      ColumnaEditable("Fecha Prueba", "fecha_prueba", TIPO_EDICION_FECHA),
      ColumnaEditable("Evaluador", "evaluador", TIPO_EDICION_TEXTO),
      ColumnaEditable("Vehículo Evaluado", "id_vehiculo_evaluado", TIPO_EDICION_ENTERO),
      ColumnaEditable("Observación", "observacion", TIPO_EDICION_TEXTO),
  )
  ```
