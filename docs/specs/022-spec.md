# Spec 022 — Compatibilidad Total de Consultas de Reportes con SQLite

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Estado  | aprobada                                                             |
| Autor   | Ing. Miguel Angel Ortiz Roldan                                       |
| Fecha   | 2026-10-10                                                           |
| Rama    | `feat/fix-consultas-reportes-sqlite`                                 |
| Relaciona | `010-spec.md` (Reportes y Exportaciones)                           |

## 1. Contexto y problema

Al abrir la página **Reportes y Exportaciones** (`3_Reportes.py`), la aplicación falla con el error de base de datos:
```text
sqlite3.OperationalError: unrecognized token: ":"
pandas.errors.DatabaseError: Execution failed on sql '... dc.fecha_registro::date ...'
```
Y al cambiar al reporte de licencias por vencer:
```text
sqlite3.OperationalError: unrecognized token: ":" en '(l.vencimiento::date - CURRENT_DATE)' y 'CURRENT_DATE + :dias'
```

Las consultas de `src/certificado_operadores/infra/reportes_repository.py` conservaban sintaxis nativa de PostgreSQL:
1. Casteos de tipo con dos puntos dobles (`::date`).
2. Suma de intervalos de fecha (`INTERVAL '3 years'`).
3. Cláusula `DISTINCT ON (id_codigo)` inexistente en SQLite.
4. Restas de fecha directas (`(l.vencimiento::date - CURRENT_DATE)`).
5. Expresiones de filtro de fechas (`CURRENT_DATE + :dias`).

## 2. Requerimientos de Compatibilidad SQLite

### S-01: Conversión de Casteos y Funciones de Fecha
- Sustituir `::date` por `DATE(columna)` o `SUBSTR(columna, 1, 10)`.
- Sustituir `CURRENT_DATE` por `DATE('now')` o `CURRENT_DATE`.
- Para sumar años: `DATE(fecha, '+3 years')`.
- Para diferencias de días: `CAST(ROUND(JULIANDAY(fecha1) - JULIANDAY(fecha2)) AS INTEGER)`.
- Para filtros de días futuros: `DATE('now', '+' || :dias || ' days')`.

### S-02: Reemplazo de `DISTINCT ON` en Reportes de Certificados
En los reportes `certificados_vencer` y `certificados_vencidos`, reemplazar `DISTINCT ON (id_codigo)` por la función de ventana estándar de SQLite `ROW_NUMBER() OVER (PARTITION BY id_codigo ORDER BY fecha_certificado DESC)` en la subconsulta, filtrando por `rn = 1`.

### S-03: Cobertura Completa de Pruebas de Reportes
En `tests/test_reportes.py`, agregar pruebas unitarias que ejecuten `ejecutar_reporte()` para **los 8 reportes soportados**:
1. `utryt`
2. `operadores_empresa`
3. `licencias_vencer`
4. `eventos_tipo`
5. `reincidencias`
6. `comportamientos_operador`
7. `certificados_vencer`
8. `certificados_vencidos`
Garantizando que ninguno arroje errores de sintaxis en SQLite.

### S-04: Pureza de Advertencias y Calidad
Las pruebas deben cumplir la política de cero advertencias (`-W error`), manteniendo 100% de pruebas en verde y código comentado en español.

## 3. Criterios de Aceptación (verificables)

- [ ] **CA-01:** Todas las consultas SQL en `reportes_repository.py` usan sintaxis 100% compatible con SQLite (cero tokens `::`, cero `INTERVAL`, cero `DISTINCT ON`).
- [ ] **CA-02:** Los reportes `utryt`, `licencias_vencer`, `certificados_vencer` y `certificados_vencidos` ejecutan sin `OperationalError` en SQLite.
- [ ] **CA-03:** `tests/test_reportes.py` prueba la ejecución de los 8 reportes contra la base de datos de prueba.
- [ ] **CA-04:** `uv run pytest` pasa al 100% en verde con cero warnings (`-W error`).
- [ ] **CA-05:** `CONSTITUTION.md` y `docs/referencia-funciones.md` actualizados.

## 4. Enlaces

- Plan: [`022-plan.md`](./022-plan.md)
- Tareas: [`022-tareas.md`](./022-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
