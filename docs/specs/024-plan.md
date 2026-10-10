# Plan de Implementación — Spec 024

## Fases

### Fase 1: Ancho Fluido y Eliminación de Restricciones
- Editar `src/certificado_operadores/estilos.py` para eliminar `max-width: 1200px;` de `.block-container` y configurar ancho fluido `100%`.

### Fase 2: Corrección del Patrón de Códigos por Concesionario (COT)
- Modificar `OperadoresRepository.siguiente_codigo(id_empresa)` en `src/certificado_operadores/infra/repository.py` para calcular el siguiente código dentro del rango `[id_empresa * 10000, (id_empresa + 1) * 10000)`.
- Actualizar `tests/test_admin_operadores_guardado.py` con pruebas para cada concesionario (1: GIT, 2: ByN, 3: ETM, 4: Unimetro).

### Fase 3: Refinamiento de Reportes, Supresión de Gráficos Inútiles y KPIs Reales
- En `src/certificado_operadores/modulos/reportes/ui.py`:
  - En UTRyT: suprimir completamente la sección de gráficos.
  - En reportes de listados operacionales (Reincidencias, Comportamientos): omitir gráficos genéricos de filas individuales.
  - Reemplazar el cálculo de KPIs para eliminar `.sum()` sobre IDs y eliminar la tarjeta de "Columnas".
- En `src/certificado_operadores/infra/reportes_repository.py`:
  - Proyectar el nombre de la tipología (`t.nombre_tipologia` / `t.tipologia`) en el reporte de operadores por empresa y tipología.
  - Agregar filtro de concesionario en `licencias_vencer` y `certificados_vencer`.

### Fase 4: Pruebas y Cero Advertencias
- Ejecutar `make test` asegurando 100% verde con `pytest -q -W error`.
