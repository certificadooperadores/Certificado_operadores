# Tareas — Spec 025

- [x] **T01:** En `db.py` y `scripts/cargar_excel_a_sqlite.py`, configurar pragmas SQLite (`journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`) y crear los índices de alto impacto (`idx_persona_cedula`, `idx_codigo_operador`, `idx_eventos_operador`, `idx_comportamiento_codigo`, `idx_codigo_persona`, `idx_eventos_fecha`, `idx_reincidencia_codigo`).
- [x] **T02:** Crear `src/certificado_operadores/facade_certificados.py` y adaptar `modulos/gestion_certificados/ui.py`.
- [x] **T03:** Crear `src/certificado_operadores/facade_comportamientos.py` y adaptar `modulos/reporte_comportamientos/ui.py`.
- [x] **T04:** Crear `src/certificado_operadores/facade_reportes.py` y adaptar `modulos/reportes/ui.py`.
- [x] **T05:** Crear `src/certificado_operadores/facade_configuracion.py` y adaptar `modulos/catalogos/ui.py` y `modulos/correccion_registros/ui.py`.
- [x] **T06:** En `utils.py`, eliminar el SQL directo y consumir el estado de versión a través de `BackupService` (`version_actual`/`estado_version`); eliminar rutas quemadas.
- [x] **T07:** Mover `init_db.py` a `temp_agent/` y eliminar `INSTRUCCIONES_OPENCODE.md`.
- [x] **T08:** En `pyproject.toml`, agregar `altair = ">=5.0.0"` y retirar `python-dotenv` (no usada); crear `LICENSE` y `CODE_OF_CONDUCT.md`.
- [x] **T09:** Actualizar `docs/desacople.md` y `docs/referencia-funciones.md` con las nuevas fachadas y el conteo de pruebas.
- [x] **T10:** Ejecutar `uv run pytest -q -W error` garantizando 100% de pruebas en verde y cero advertencias (373 funciones de prueba; 402 casos).
