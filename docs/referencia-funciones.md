# Referencia de funciones — Certificado_operadores

Catálogo de **todas las funciones** del proyecto: su ubicación y su descripción.
Mantener actualizado en el mismo commit que cualquier cambio de código.

> Regla: cada archivo/módulo y cada función tiene **una única responsabilidad** y
> está súper-comentada (docstring en español).

## Índice por módulo

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| `db` | `src/certificado_operadores/db.py` | Motor y utilidades de conexión a SQLite. |
| `facade` | `src/certificado_operadores/facade.py` | Fachada de casos de uso de operadores (consultas, certificados y estadísticas); aísla a la UI del acceso a datos. |

## Funciones

### Módulo `facade`

| Función | Ubicación (archivo:línea) | Firma | Descripción | Devuelve |
|---------|---------------------------|-------|-------------|----------|
| `OperadoresFacade.__init__` | `src/certificado_operadores/facade.py` | `(engine: Engine \| None = None) -> None` | Inicializa la fachada inyectando el motor. | — |
| `OperadoresFacade.motor` | `src/certificado_operadores/facade.py` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `OperadoresFacade.verificar_conexion` | `src/certificado_operadores/facade.py` | `() -> bool` | Verifica el estado de la conexión a SQLite. | `bool` |
| `OperadoresFacade.obtener_operador_por_cedula` | `src/certificado_operadores/facade.py` | `(cedula: int) -> OperadorInfo \| None` | Consulta un operador por número de cédula. | `OperadorInfo` o `None` |
| `OperadoresFacade.obtener_operador_por_codigo` | `src/certificado_operadores/facade.py` | `(codigo: int) -> OperadorInfo \| None` | Consulta un operador por código de operación. | `OperadorInfo` o `None` |
| `OperadoresFacade.validar_certificado` | `src/certificado_operadores/facade.py` | `(codigo: int) -> EstadoCertificado` | Valida la vigencia del certificado de idoneidad. | `EstadoCertificado` |
| `OperadoresFacade.estadisticas_basicas` | `src/certificado_operadores/facade.py` | `() -> EstadisticasBasicas` | Conteos generales del sistema. | `EstadisticasBasicas` |
| `OperadorInfo.nombre_completo` | `src/certificado_operadores/facade.py` | `() -> str` | Une nombres y apellidos del operador. | `str` |
| `_parsear_fecha` | `src/certificado_operadores/facade.py` | `(valor: object) -> date \| None` | Convierte una fecha de SQLite a `date`. | `date` o `None` |
| `_sumar_anios` | `src/certificado_operadores/facade.py` | `(fecha: date, anios: int) -> date` | Suma años ajustando el 29 de febrero. | `date` |
| `_clasificar_estado` | `src/certificado_operadores/facade.py` | `(dias_restantes: int) -> str` | Clasifica el certificado (VIGENTE/POR_VENCER/VENCIDO). | `str` |
| `_contar` | `src/certificado_operadores/facade.py` | `(conexion: Connection, sentencia: str, parametros: dict[str, int] \| None = None) -> int` | Ejecuta un `COUNT(*)` de forma segura. | `int` |

### DTOs (dataclasses) del módulo `facade`

| Clase | Campos | Descripción |
|-------|--------|-------------|
| `OperadorInfo` | `codigo, cedula, nombres, primer_apellido, segundo_apellido, genero, id_empresa, nombre_empresa, id_perfil_tipologia, id_vigencia` | Datos consolidados de un operador. |
| `EstadoCertificado` | `codigo, fecha_certificado, fecha_vencimiento, dias_restantes, estado, cancelado` | Resultado de validar el certificado. |
| `EstadisticasBasicas` | `total_operadores, operadores_vigentes, operadores_anulados, total_empresas, total_licencias` | Conteos para tableros. |

## Detalle

### `OperadoresFacade.verificar_conexion`

- **Ubicación:** `src/certificado_operadores/facade.py`
- **Responsabilidad única:** comprobar que la base SQLite responde.
- **Parámetros:** ninguno.
- **Devuelve:** `True` si la conexión es válida; `False` ante `SQLAlchemyError`.
- **Errores:** no propaga; los captura y los traduce a `False`.

### `OperadoresFacade.obtener_operador_por_cedula`

- **Ubicación:** `src/certificado_operadores/facade.py`
- **Responsabilidad única:** buscar el operador asociado a una cédula.
- **Parámetros:** `cedula` — documento (`dim_persona.id_persona`).
- **Devuelve:** `OperadorInfo` del registro vigente de menor código, o `None`.
- **Errores:** ninguno (consulta parametrizada con `LEFT JOIN`).

### `OperadoresFacade.obtener_operador_por_codigo`

- **Ubicación:** `src/certificado_operadores/facade.py`
- **Responsabilidad única:** buscar el operador asociado a un código de operación.
- **Parámetros:** `codigo` — `dim_codigo.id_codigo`.
- **Devuelve:** `OperadorInfo` o `None`.
- **Errores:** ninguno.

### `OperadoresFacade.validar_certificado`

- **Ubicación:** `src/certificado_operadores/facade.py`
- **Responsabilidad única:** calcular la vigencia del certificado de un operador.
- **Parámetros:** `codigo` — `dim_codigo.id_codigo`.
- **Devuelve:** `EstadoCertificado` con estado `VIGENTE`, `POR_VENCER`, `VENCIDO`, `SIN_CERTIFICADO` o `CANCELADO`.
- **Errores:** ninguno de negocio; aplica `ANIOS_VIGENCIA_CERTIFICADO` (3 años) y `DIAS_ALERTA_VENCIMIENTO` (90 días).

### `OperadoresFacade.estadisticas_basicas`

- **Ubicación:** `src/certificado_operadores/facade.py`
- **Responsabilidad única:** contar operadores, vigencias, empresas y licencias.
- **Parámetros:** ninguno.
- **Devuelve:** `EstadisticasBasicas`. Si el esquema no está cargado, devuelve ceros.
- **Errores:** no propaga `SQLAlchemyError`; devuelve conteos en cero.

### Pruebas

- **Ubicación:** `tests/test_facade.py`
- **Cobertura:** conexión (éxito y fallo), consulta por cédula/código (con y sin resultados), validación de certificado (por vencer, vigente, sin certificado, cancelado) y estadísticas básicas. Patrón AAA con SQLite temporal.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
