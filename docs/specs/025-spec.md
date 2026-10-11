# Spec 025 — Plan Integral de Optimización, Arquitectura Facade y Robustecimiento Técnico

| Campo     | Valor                                                                          |
|-----------|--------------------------------------------------------------------------------|
| Estado    | aprobada                                                                       |
| Autor     | Ing. Miguel Angel Ortiz Roldan                                                 |
| Fecha     | 2026-10-10                                                                     |
| Rama      | `feat/optimizacion-facades-indices`                                            |
| Relaciona | Recomendaciones de Auditoría OpenCode, `024-spec.md`, `CONSTITUTION.md`         |

---

## 1. Contexto y Objetivos

Tras la auditoría integral realizada por OpenCode en modo Plan, se identificaron oportunidades críticas para llevar la plataforma al siguiente nivel de calidad técnica, seguridad y rendimiento:
1. **Rendimiento e Indexación de SQLite:** La base de datos física (`operadores.db`, ~139 MB) carece de índices explícitos en campos de búsqueda frecuente (`id_persona`, `id_codigo`, `id_empresa`, `fecha_evento`, `id_tipo_evento`). Además, la configuración del motor SQLite no tiene activado el modo WAL (*Write-Ahead Logging*) ni `busy_timeout`, lo que degrada la concurrencia.
2. **Arquitectura y Desacople (Patrón Facade 100%):** Actualmente varios módulos de la UI importan directamente sus `*Repository` de la capa de infraestructura. Se deben introducir Fachadas especializadas por dominio de caso de uso para cumplir estrictamente `UI → Facade → Dominio → Infraestructura`.
3. **Erradicación de Residuos Legacy y SQL en la UI:** `src/certificado_operadores/utils.py` ejecuta SQL crudo para el badge de versión y tiene rutas quemadas. `src/certificado_operadores/init_db.py` es código muerto de PostgreSQL con credenciales viejas. `INSTRUCCIONES_OPENCODE.md` quedó en la raíz.
4. **Declaración y Limpieza de Dependencias:** Declarar `altair` en `pyproject.toml` (usado intensivamente en reportes) y limpiar dependencias no usadas.
5. **Gobernanza y Documentación:** Crear `LICENSE` y `CODE_OF_CONDUCT.md` para resolver enlaces rotos en `README.md`, actualizar `docs/desacople.md` y sincronizar el conteo de pruebas.

*(Nota: De acuerdo a la directriz del usuario, se omite expresamente obligar a cambiar la contraseña del usuario en el primer inicio).*

---

## 2. Requerimientos Técnicos

### R-01: Indexación Estratégica y Optimización de Motor SQLite
- En `src/certificado_operadores/db.py` y `scripts/cargar_excel_a_sqlite.py`:
  - Configurar pragmas de alto rendimiento para SQLite:
    - `PRAGMA journal_mode = WAL;` (permite lecturas concurrentes sin bloquear escrituras).
    - `PRAGMA busy_timeout = 5000;` (espera hasta 5 segundos ante concurrencia en lugar de fallar inmediatamente con *database locked*).
    - `PRAGMA synchronous = NORMAL;`.
  - Crear índices explícitos `CREATE INDEX IF NOT EXISTS`:
    - `idx_persona_cedula` en `dim_persona(id_persona)`.
    - `idx_codigo_operador` en `dim_codigo(id_codigo, id_empresa, id_vigencia)`.
    - `idx_codigo_persona` en `dim_codigo(id_persona)`.
    - `idx_eventos_operador` en `fact_eventos_operador(id_codigo, id_tipo_evento, id_vigencia)`.
    - `idx_eventos_fecha` en `fact_eventos_operador(fecha_inicio, fecha_fin)`.
    - `idx_comportamiento_codigo` en `fact_comportamiento(id_codigo, fecha)`.
    - `idx_reincidencia_codigo` en `fact_reincidencia(id_codigo, estado)`.

### R-02: Fachadas Especializadas por Dominio de Caso de Uso (Opción B)
Implementar fachadas en `src/certificado_operadores/` para que la UI **jamás** importe clases `*Repository`:
- `CertificadosFacade` (`src/certificado_operadores/facade_certificados.py`):
  - Encapsula `CertificadosRepository`. Expone listado de eventos, cálculo de vigencias, alertas y creación de certificaciones/cancelaciones.
- `ComportamientosFacade` (`src/certificado_operadores/facade_comportamientos.py`):
  - Encapsula `ComportamientosRepository`. Expone ingreso individual, validación/carga masiva, evaluación de reincidencia y registro de acciones Metrocali.
- `ReportesFacade` (`src/certificado_operadores/facade_reportes.py`):
  - Encapsula `ReportesRepository`. Expone métricas analíticas, filtros tridireccionales, vencimientos de licencias y certificados.
- `ConfiguracionFacade` (`src/certificado_operadores/facade_configuracion.py`):
  - Encapsula `CatalogosRepository` y `EventosRepository` (edición masiva de tablas). Expone operaciones de catálogos maestros y corrección segura de registros.
- Actualizar los archivos `ui.py` de cada módulo para inyectar y consumir exclusivamente su Fachada correspondiente.

### R-03: Desacoplamiento de `utils.py` y Eliminación de Residuos Legacy
- En `src/certificado_operadores/utils.py`:
  - Eliminar `run_query("SELECT ... FROM dim_version_bd")` directo y la ruta hardcodeada `/Backups`.
  - Consumir el estado de versión a través de `BackupService` o un método limpio de consulta desacoplado.
- Mover `src/certificado_operadores/init_db.py` fuera del paquete a `temp_agent/` (o archivarlo) ya que contiene credenciales viejas de PostgreSQL y no se utiliza en el runtime SQLite.
- Eliminar el archivo obsoleto `INSTRUCCIONES_OPENCODE.md` de la raíz del proyecto.

### R-04: Declaración de Dependencias y Gobernanza
- Agregar `altair = ">=5.0.0"` a las dependencias de `pyproject.toml`.
- Crear los archivos formales `LICENSE` (Licencia Privada Institucional Metrocali S.A.) y `CODE_OF_CONDUCT.md` en la raíz.
- Actualizar `docs/desacople.md` reflejando el mapa completo de Fachadas especializadas y retirando cualquier mención a carpetas inexistentes.
- Sincronizar el conteo de pruebas en la documentación al valor exacto de funciones `test_`.

---

## 3. Criterios de Aceptación
1. Todos los módulos UI (`modulos/*/ui.py`) importan y consumen Fachadas, con **cero** importaciones directas de `*Repository`.
2. Las consultas analíticas sobre `fact_comportamiento` y filtros por cédula/código utilizan índices SQLite verificados (`EXPLAIN QUERY PLAN`).
3. El motor SQLite opera con `journal_mode=WAL` y `busy_timeout=5000`.
4. `pyproject.toml` incluye `altair`.
5. La suite completa de pruebas (`pytest`) pasa al 100% en verde con cero errores y cero advertencias.
