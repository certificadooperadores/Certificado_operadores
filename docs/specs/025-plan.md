# Plan — Spec 025

## 1. Enfoque de Implementación

1. **Fase 1: Motor SQLite e Índices Estratégicos:**
   - Añadir pragmas (`WAL`, `busy_timeout`) a `db.py` y `scripts/cargar_excel_a_sqlite.py`.
   - Crear script/función de migración que garantice la existencia de índices en `operadores.db`.
2. **Fase 2: Fachadas Especializadas por Dominio:**
   - Crear `facade_certificados.py` con pruebas unitarias.
   - Crear `facade_comportamientos.py` con pruebas unitarias.
   - Crear `facade_reportes.py` con pruebas unitarias.
   - Crear `facade_configuracion.py` con pruebas unitarias.
3. **Fase 3: Refactorización de la UI:**
   - Adaptar `modulos/gestion_certificados/ui.py` para usar `CertificadosFacade`.
   - Adaptar `modulos/reporte_comportamientos/ui.py` para usar `ComportamientosFacade`.
   - Adaptar `modulos/reportes/ui.py` para usar `ReportesFacade`.
   - Adaptar `modulos/catalogos/ui.py` y `correccion_registros/ui.py` para usar `ConfiguracionFacade`.
4. **Fase 4: Desacople de `utils.py` y Limpieza de Legado:**
   - Extraer consulta de versión a `BackupService` o servicio limpio en `utils.py`.
   - Mover `init_db.py` a `temp_agent/init_db_postgres_legacy.py`.
   - Eliminar `INSTRUCCIONES_OPENCODE.md` de la raíz.
5. **Fase 5: Dependencias y Gobernanza:**
   - Añadir `altair` en `pyproject.toml` y ejecutar `uv sync`.
   - Crear `LICENSE` y `CODE_OF_CONDUCT.md`.
   - Actualizar `docs/desacople.md`.
   - Ejecutar `make test` y verificar 100% de pruebas en verde.
