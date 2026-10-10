# Tareas — Spec 024

- [ ] **T01:** Modificar `src/certificado_operadores/estilos.py` para remover `max-width: 1200px;` de `.block-container` y dar ancho completo fluido.
- [ ] **T02:** Modificar `siguiente_codigo(id_empresa)` en `OperadoresRepository` para generar códigos con el patrón oficial del concesionario (base `id_empresa * 10000`).
- [ ] **T03:** En `modulos/reportes/ui.py`, quitar gráficos en Consolidado UTRyT y listados de auditoría.
- [ ] **T04:** En `modulos/reportes/ui.py`, corregir KPIs eliminando sumas de IDs y conteo de columnas.
- [ ] **T05:** En `reportes_repository.py` y UI, proyectar nombres reales de tipología en lugar de IDs `1, 2, 3`.
- [ ] **T06:** En `reportes_repository.py` y UI, agregar filtro de empresa concesionaria a "Licencias por Vencer" y "Certificados por Vencer".
- [ ] **T07:** Ejecutar `pytest -q -W error` garantizando 100% de pruebas pasando en verde con 0 warnings.
