# Plan 022 — Compatibilidad Total de Consultas de Reportes con SQLite

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Spec    | [`022-spec.md`](./022-spec.md)                                       |
| Tareas  | [`022-tareas.md`](./022-tareas.md)                                   |
| Rama    | `feat/fix-consultas-reportes-sqlite`                                 |

## 1. Arquitectura y Enfoque Técnico

El objetivo es erradicar toda sintaxis remanente de PostgreSQL en `src/certificado_operadores/infra/reportes_repository.py`:

1. **Constantes y columnas:**
   - `_COL_VENCIMIENTO_LICENCIA`: `DATE(l.vencimiento)`
   - `_COL_FECHA_EVENTOS`: `DATE(COALESCE(e.fecha_certificado, e.fecha_retiro, e.fecha_suspension, e.fecha_observacion, e.fecha_registro))`
   - `_COL_VENCIMIENTO_CERTIFICADO`: `DATE(e.fecha_certificado, '+3 years')`
2. **Consultas en `_REPORTES`:**
   - `utryt`: cambiar `dc.fecha_registro::date` por `DATE(dc.fecha_registro)`.
   - `licencias_vencer`:
     - `Dias Restantes`: `CAST(ROUND(JULIANDAY(l.vencimiento) - JULIANDAY('now')) AS INTEGER)`
     - Traer `c.id_persona AS "Cedula"` y `(p.nombres || ' ' || p.primer_apellido) AS "Nombre"` haciendo JOIN con `dim_codigo` y `dim_persona`.
   - `comportamientos_operador`:
     - Filtro fecha: `DATE(f.fecha_evento)`
   - `certificados_vencer` y `certificados_vencidos`:
     - Reemplazar `DISTINCT ON (id_codigo)` por subconsulta numerada con `ROW_NUMBER() OVER (PARTITION BY id_codigo ORDER BY fecha_certificado DESC) as rn` y filtrar `WHERE e.rn = 1`.
     - Vencimiento: `DATE(e.fecha_certificado, '+3 years')`.
     - Días restantes / vencidos: usando `JULIANDAY`.
3. **Condiciones dinámicas en `construir_condiciones()`:**
   - Para `tipo == "dias_vencer"`:
     - SQLite: `f"{columna} BETWEEN DATE('now') AND DATE('now', '+' || :dias || ' days')"`
4. **Pruebas en `tests/test_reportes.py`:**
   - Ejecutar los 8 reportes con `ejecutar_reporte` parametrizado o individual para validar que todas las consultas generen DataFrames sin errores.

## 2. Secuencia de Trabajo

1. Refactorizar constantes, expresiones y consultas en `reportes_repository.py`.
2. Actualizar `construir_condiciones()` para la sintaxis de fechas de SQLite.
3. Escribir pruebas unitarias para los 8 reportes en `tests/test_reportes.py`.
4. Ejecutar `uv run pytest` con `-W error` asegurando 100% verde.
5. Actualizar `CONSTITUTION.md` y `docs/referencia-funciones.md`.
