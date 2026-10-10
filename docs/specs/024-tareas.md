# Tareas — Spec 024

- [ ] **T01:** En `estilos.py`, remover `max-width: 1200px;` de `.block-container` y dar ancho fluido completo.
- [ ] **T02:** En `modulos/reportes/ui.py`, suprimir la sección de gráficos en Consolidado UTRyT y omitir gráficos genéricos de filas individuales.
- [ ] **T03:** En `modulos/reportes/ui.py`, erradicar la suma de IDs/códigos en KPIs y eliminar completamente la tarjeta de "Columnas".
- [ ] **T04:** En `modulos/reportes/ui.py`, mover los botones `Exportar a Excel` y `Exportar a CSV` arriba de la tabla de datos.
- [ ] **T05:** En `reportes_repository.py` y UI, resolver la columna `Empresa` en Reincidencias por el prefijo COT para que nunca salga `None` e incorporar filtro de rango de fechas.
- [ ] **T06:** En `reportes_repository.py` y UI, proyectar nombres legibles de tipología en lugar de IDs `1, 2, 3`.
- [ ] **T07:** En `reportes_repository.py` y UI, agregar filtro de empresa concesionaria a "Licencias por Vencer" y "Certificados por Vencer".
- [ ] **T08:** En `repository.py`, modificar `siguiente_codigo(id_empresa)` para respetar los rangos oficiales de cada COT (`base = id_empresa * 10000`).
- [ ] **T09:** Ejecutar `pytest -q -W error` garantizando 100% de pruebas pasando en verde con 0 warnings.
