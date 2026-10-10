# Tareas — Spec 024

- [x] **T01:** En `estilos.py`, remover `max-width: 1200px;` de `.block-container` y dar ancho fluido completo.
- [x] **T02:** En `modulos/reportes/ui.py`, suprimir la sección de gráficos en Consolidado UTRyT y omitir gráficos genéricos de filas individuales.
- [x] **T03:** En `modulos/reportes/ui.py`, erradicar la suma de IDs/códigos en KPIs y eliminar completamente la tarjeta de "Columnas".
- [x] **T04:** En `modulos/reportes/ui.py`, mover los botones `Exportar a Excel` y `Exportar a CSV` arriba de la tabla de datos.
- [x] **T05:** En `reportes_repository.py` y UI, resolver la columna `Empresa` en Reincidencias por el prefijo COT para que nunca salga `None` e incorporar filtro de rango de fechas.
- [x] **T06:** En `reportes_repository.py` y UI, proyectar nombres legibles de tipología en lugar de IDs `1, 2, 3`.
- [x] **T07:** En `reportes_repository.py` y UI, agregar filtro de empresa concesionaria y generar diagrama de Gantt temporal de vencimientos por concesionario con criticidad por color (<30 días rojo, 30-60 días ámbar, >60 días azul).
- [x] **T08:** En `repository.py`, modificar `siguiente_codigo(id_empresa)` para respetar los rangos oficiales de cada COT (`base = id_empresa * 10000`).
- [x] **T09:** Ejecutar `pytest -q -W error` garantizando 100% de pruebas pasando en verde con 0 warnings.
