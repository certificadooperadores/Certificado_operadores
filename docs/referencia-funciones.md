# Referencia de funciones — Certificado_operadores

Catálogo de **todas las funciones** del proyecto: su ubicación y su descripción.
Mantener actualizado en el mismo commit que cualquier cambio de código.

> Regla: cada archivo/módulo y cada función tiene **una única responsabilidad** y
> está súper-comentada (docstring en español).

## Índice por módulo

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| `db` | `src/certificado_operadores/db.py` | Motor y utilidades de conexión a SQLite. |
| `domain` | `src/certificado_operadores/domain/models.py` | DTOs, constantes de negocio y funciones puras; sin dependencias externas. |
| `infra` | `src/certificado_operadores/infra/repository.py` | Repositorio de acceso a datos (SQLAlchemy) que devuelve modelos de dominio. |
| `facade` | `src/certificado_operadores/facade.py` | Fachada de casos de uso; orquesta y delega en el repositorio sin ejecutar SQL. |
| `admin_operadores` | `src/certificado_operadores/modulos/admin_operadores/ui.py` | Interfaz Streamlit de administración de operadores; consume el Facade y no contiene SQL. |
| `domain.usuarios` | `src/certificado_operadores/domain/usuarios.py` | DTO de usuario, constantes y reglas puras de autorización. |
| `infra.seguridad` | `src/certificado_operadores/infra/seguridad.py` | Hashing y verificación de contraseñas con `bcrypt`. |
| `infra.usuarios_repository` | `src/certificado_operadores/infra/usuarios_repository.py` | Acceso a datos de `dim_usuarios` y auditoría (SQLAlchemy). |
| `facade_usuarios` | `src/certificado_operadores/facade_usuarios.py` | Fachada de casos de uso de usuarios; orquesta y delega sin ejecutar SQL. |
| `gestion_usuarios` | `src/certificado_operadores/modulos/gestion_usuarios/ui.py` | Interfaz Streamlit de gestión de usuarios; consume el Facade y no contiene SQL. |
| `infra.backup_service` | `src/certificado_operadores/infra/backup_service.py` | Servicio de copias de seguridad de SQLite; encapsula el sistema de archivos. |
| `administrar_backups` | `src/certificado_operadores/modulos/administrar_backups/ui.py` | Interfaz Streamlit de backups; consume `BackupService` y no contiene SO ni SQL. |
| `infra.eventos_repository` | `src/certificado_operadores/infra/eventos_repository.py` | Acceso a datos de `fact_eventos_operador`: filtros, lotes y mutaciones con auditoría (SQLAlchemy). |
| `correccion_registros` | `src/certificado_operadores/modulos/correccion_registros/ui.py` | Interfaz Streamlit de corrección de registros; consume `EventosRepository` y no contiene SQL. |
| `infra.catalogos_repository` | `src/certificado_operadores/infra/catalogos_repository.py` | Acceso a datos de los cinco catálogos (empresas, vehículos, impactos, comportamientos y detalles) con auditoría (SQLAlchemy). |
| `catalogos` | `src/certificado_operadores/modulos/catalogos/ui.py` | Interfaz Streamlit de catálogos; consume `CatalogosRepository` y no contiene SQL. |

## Funciones

### Módulo `domain` — `src/certificado_operadores/domain/models.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `OperadorInfo.nombre_completo` | `() -> str` | Une nombres y apellidos del operador. | `str` |
| `_parsear_fecha` | `(valor: object) -> date \| None` | Convierte una fecha textual a `date`. | `date` o `None` |
| `_sumar_anios` | `(fecha: date, anios: int) -> date` | Suma años ajustando el 29 de febrero. | `date` |
| `_clasificar_estado` | `(dias_restantes: int) -> str` | Clasifica el certificado (VIGENTE/POR_VENCER/VENCIDO). | `str` |
| `calcular_estado_certificado` | `(codigo: int, ultima_certificacion: object, cancelado: bool) -> EstadoCertificado` | Aplica la regla de negocio y construye el estado del certificado. | `EstadoCertificado` |

#### DTOs (dataclasses) del módulo `domain`

| Clase | Campos | Descripción |
|-------|--------|-------------|
| `OperadorInfo` | `codigo, cedula, nombres, primer_apellido, segundo_apellido, genero, id_empresa, nombre_empresa, id_perfil_tipologia, id_vigencia` | Datos consolidados de un operador. |
| `EstadoCertificado` | `codigo, fecha_certificado, fecha_vencimiento, dias_restantes, estado, cancelado` | Resultado de validar el certificado. |
| `EstadisticasBasicas` | `total_operadores, operadores_vigentes, operadores_anulados, total_empresas, total_licencias` | Conteos para tableros. |

#### Constantes de negocio

`VIGENCIA_ACTIVA`, `VIGENCIA_ANULADA`, `ANIOS_VIGENCIA_CERTIFICADO`,
`DIAS_ALERTA_VENCIMIENTO`, `TIPOS_EVENTO_CERTIFICADO`, `TIPO_EVENTO_CANCELACION`
y los estados `ESTADO_VIGENTE`, `ESTADO_POR_VENCER`, `ESTADO_VENCIDO`,
`ESTADO_SIN_CERTIFICADO`, `ESTADO_CANCELADO`.

### Módulo `infra` — `src/certificado_operadores/infra/repository.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `OperadoresRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `OperadoresRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `OperadoresRepository.verificar_conexion` | `() -> bool` | Verifica el estado de la conexión a SQLite. | `bool` |
| `OperadoresRepository.obtener_operador_por_cedula` | `(cedula: int) -> OperadorInfo \| None` | Consulta un operador por número de cédula. | `OperadorInfo` o `None` |
| `OperadoresRepository.obtener_operador_por_codigo` | `(codigo: int) -> OperadorInfo \| None` | Consulta un operador por código de operación. | `OperadorInfo` o `None` |
| `OperadoresRepository.validar_certificado` | `(codigo: int) -> EstadoCertificado` | Consulta certificación y cancelaciones; calcula el estado con el dominio. | `EstadoCertificado` |
| `OperadoresRepository.estadisticas_basicas` | `() -> EstadisticasBasicas` | Conteos generales del sistema. | `EstadisticasBasicas` |
| `OperadoresRepository._consultar_operador` | `(sentencia: TextClause, parametros: dict[str, int]) -> OperadorInfo \| None` | Ejecuta la consulta de operador y mapea la fila al DTO. | `OperadorInfo` o `None` |
| `_contar` | `(conexion: Connection, sentencia: TextClause, parametros: dict[str, int] \| None = None) -> int` | Ejecuta un `COUNT(*)` de forma segura. | `int` |

### Módulo `facade` — `src/certificado_operadores/facade.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `OperadoresFacade.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa la fachada y su repositorio. | — |
| `OperadoresFacade.motor` | `propiedad -> Engine` | Motor SQLAlchemy delegado al repositorio. | `Engine` |
| `OperadoresFacade.verificar_conexion` | `() -> bool` | Verifica el estado de la conexión a SQLite. | `bool` |
| `OperadoresFacade.obtener_operador_por_cedula` | `(cedula: int) -> OperadorInfo \| None` | Consulta un operador por número de cédula. | `OperadorInfo` o `None` |
| `OperadoresFacade.obtener_operador_por_codigo` | `(codigo: int) -> OperadorInfo \| None` | Consulta un operador por código de operación. | `OperadorInfo` o `None` |
| `OperadoresFacade.validar_certificado` | `(codigo: int) -> EstadoCertificado` | Valida la vigencia del certificado de idoneidad. | `EstadoCertificado` |
| `OperadoresFacade.estadisticas_basicas` | `() -> EstadisticasBasicas` | Conteos generales del sistema. | `EstadisticasBasicas` |

### Módulo `admin_operadores` — `src/certificado_operadores/modulos/admin_operadores/ui.py`

Interfaz de Streamlit del módulo de administración de operadores (spec 003).
Página delgada: busca la cédula en `OperadoresFacade` y autocompleta el
formulario con el DTO `OperadorInfo`. No contiene sentencias de base de datos
(RNF-01) ni conoce el esquema (RNF-02).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `parsear_cedula` | `(texto: str) -> int \| None` | Convierte el texto del campo en una cédula positiva. | `int` o `None` |
| `construir_valores_formulario` | `(operador: OperadorInfo \| None) -> dict[str, Any]` | Mapea el DTO del Facade a los valores por defecto del formulario (estado Creación/Actualización). | `dict` |
| `_indice_genero` | `(genero: str) -> int` | Índice del género dentro de `GENEROS`. | `int` |
| `_texto_opcional` | `(valor: Any) -> str` | Convierte un identificador opcional a texto. | `str` |
| `_render_encabezado` | `() -> None` | Título, estilos y ayuda del módulo. | — |
| `_render_formulario` | `(valores: dict[str, Any]) -> None` | Pinta el formulario autocompletado. | — |
| `_render_consulta` | `(fachada: OperadoresFacade) -> None` | Captura la cédula, consulta el Facade y autocompleta. | — |
| `render_page` | `(fachada: OperadoresFacade \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `GENEROS`, `ESTADO_CREACION`, `ESTADO_ACTUALIZACION`.

Punto de entrada: `src/certificado_operadores/pages/2_Administracion_Operadores.py`
(importa `OperadoresFacade` y delega en `render_page`).

### Módulo `admin_operadores` — pruebas

- **Ubicación:** `tests/test_admin_operadores_ui.py`
- **Cobertura:** `parsear_cedula`, `construir_valores_formulario` (creación y
  actualización), ausencia de SQL/conexión directa en la UI (RNF-01), uso del
  `OperadoresFacade` (CA-01), compilación de la página (CA-03), delegación real
  de la búsqueda por cédula en el Facade (RF-01), autocompletado del formulario
  con el `OperadorInfo` (RF-02) y el caso de borde de operador no encontrado
  (estado "Creación"). Patrón AAA con un doble de Facade y un doble de Streamlit.

### Módulo `domain.usuarios` — `src/certificado_operadores/domain/usuarios.py`

Reglas puras de autorización y DTO de cuenta (spec 004).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `roles_asignables` | `(rol_solicitante: str) -> tuple[str, ...]` | Roles que puede asignar un solicitante (solo Super Admin asigna Super Admin). | `tuple[str, ...]` |
| `puede_modificar_usuario` | `(rol_solicitante: str, rol_objetivo: str) -> bool` | Indica si puede modificar una cuenta con ese rol. | `bool` |
| `puede_inactivar_usuario` | `(usuario_solicitante: str, usuario_objetivo: str, estado_nuevo: str) -> bool` | Impide inactivar la propia cuenta. | `bool` |

DTOs: `UsuarioInfo`, `ResultadoOperacion`. Constantes: `ROL_SUPER_ADMINISTRADOR`,
`ROL_ADMINISTRADOR`, `ROL_GESTOR`, `ROLES_ASIGNABLES_BASE`, `ESTADO_ACTIVO`,
`ESTADO_INACTIVO`, `ESTADOS_USUARIO` y los mensajes `MENSAJE_*`.

### Módulo `infra.seguridad` — `src/certificado_operadores/infra/seguridad.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `hashear_contrasena` | `(contrasena: str) -> str` | Genera el hash bcrypt de una contraseña. | `str` |
| `verificar_contrasena` | `(contrasena: str, hash_almacenado: str) -> bool` | Comprueba una contraseña contra su hash. | `bool` |

### Módulo `infra.usuarios_repository` — `src/certificado_operadores/infra/usuarios_repository.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `UsuariosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `UsuariosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `UsuariosRepository.listar_usuarios` | `() -> list[UsuarioInfo]` | Lista las cuentas ordenadas por id. | `list[UsuarioInfo]` |
| `UsuariosRepository.obtener_usuario` | `(usuario: str) -> UsuarioInfo \| None` | Consulta una cuenta por su nombre. | `UsuarioInfo` o `None` |
| `UsuariosRepository.existe_usuario` | `(usuario: str) -> bool` | Indica si la cuenta ya existe. | `bool` |
| `UsuariosRepository.crear_usuario` | `(usuario, password_hash, rol, estado) -> None` | Inserta una cuenta nueva. | — |
| `UsuariosRepository.actualizar_usuario` | `(usuario, rol, estado, password_hash=None) -> None` | Actualiza rol, estado y contraseña opcional. | — |
| `UsuariosRepository.registrar_auditoria` | `(usuario, accion, detalles) -> None` | Registra una acción en `log_auditoria`. | — |
| `_mapear_usuario` | `(fila: RowMapping) -> UsuarioInfo` | Mapea una fila de `dim_usuarios` al DTO. | `UsuarioInfo` |

### Módulo `facade_usuarios` — `src/certificado_operadores/facade_usuarios.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `UsuariosFacade.__init__` | `(engine=None, hasheador=hashear_contrasena) -> None` | Inicializa la fachada con motor y hasheador inyectables. | — |
| `UsuariosFacade.motor` | `propiedad -> Engine` | Motor SQLAlchemy delegado al repositorio. | `Engine` |
| `UsuariosFacade.listar_usuarios` | `() -> list[UsuarioInfo]` | RF-01: lista las cuentas del sistema. | `list[UsuarioInfo]` |
| `UsuariosFacade.obtener_usuario` | `(usuario: str) -> UsuarioInfo \| None` | Consulta una cuenta por su nombre. | `UsuarioInfo` o `None` |
| `UsuariosFacade.crear_usuario` | `(usuario, contrasena, rol, *, usuario_solicitante="") -> ResultadoOperacion` | RF-02: valida existencia, hashea con bcrypt y crea. | `ResultadoOperacion` |
| `UsuariosFacade.modificar_usuario` | `(usuario, rol, estado, contrasena=None, *, rol_solicitante="", usuario_solicitante="") -> ResultadoOperacion` | RF-03: aplica permisos y actualiza la cuenta. | `ResultadoOperacion` |

### Módulo `gestion_usuarios` — `src/certificado_operadores/modulos/gestion_usuarios/ui.py`

Interfaz de Streamlit de gestión de usuarios (spec 004). Página delgada: lista
las cuentas y delega el alta y la modificación en `UsuariosFacade`. No contiene
sentencias de base de datos (RNF-01).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `filas_usuarios` | `(usuarios: list[UsuarioInfo]) -> list[dict[str, object]]` | Mapea los DTOs a filas legibles para `st.dataframe`. | `list[dict]` |
| `nombres_usuarios` | `(usuarios: list[UsuarioInfo]) -> list[str]` | Extrae los nombres para el selector de edición. | `list[str]` |
| `_render_encabezado` | `() -> None` | Título y ayuda del módulo. | — |
| `_render_listado` | `(usuarios: list[UsuarioInfo]) -> None` | Muestra el listado de usuarios. | — |
| `_render_alta` | `(fachada, roles_disponibles, usuario_solicitante) -> None` | Formulario de creación de usuarios. | — |
| `_render_modificacion` | `(fachada, usuarios, roles_disponibles, rol_solicitante, usuario_solicitante) -> None` | Formulario de modificación de usuarios. | — |
| `render_gestion_usuarios` | `(fachada: UsuariosFacade \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constante: `AYUDA_CONTRASENA_OPCIONAL`. Punto de entrada:
`src/certificado_operadores/pages/1_Configuracion.py` (importa
`render_gestion_usuarios` y lo invoca en la pestaña de usuarios).

### Módulo `gestion_usuarios` — pruebas

- **Ubicación:** `tests/test_gestion_usuarios.py`
- **Cobertura:** reglas puras (`roles_asignables`, `puede_modificar_usuario`,
  `puede_inactivar_usuario`); fachada contra SQLite temporal (listado RF-01,
  creación con hash bcrypt y auditoría RF-02, duplicado y campos vacíos,
  modificación RF-03 con y sin contraseña, permiso de Super Admin,
  autoinactivación e inexistente); ayuda de UI (`filas_usuarios`,
  `nombres_usuarios`); y criterios de aceptación estáticos (paquete CA-01, sin
  SQL en la UI CA-03/RNF-01, página con `render_gestion_usuarios` y sin `exec`
  CA-02/RNF-02). Patrón AAA.

### Módulo `infra.backup_service` — `src/certificado_operadores/infra/backup_service.py`

Servicio de copias de seguridad de la base SQLite (spec 005). Encapsula la
gestión física de los respaldos con ruta de directorio y base de origen
**configurables** (variables de entorno `BACKUPS_DIR` y `BACKUP_DB_PATH`) y
valores por defecto relativos; no contiene rutas absolutas quemadas.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `_copiar_con_sqlite` | `(origen: Path, destino: Path) -> None` | Copia consistente con la API de respaldo de `sqlite3`. | — |
| `BackupInfo.tamano_mb` | `propiedad -> float` | Tamaño del respaldo en megabytes. | `float` |
| `BackupService.__init__` | `(directorio=None, origen_db=None, reloj=datetime.now) -> None` | Inicializa el servicio con dependencias inyectables. | — |
| `BackupService.directorio` | `propiedad -> Path` | Directorio de respaldos (inyectado, por entorno o por defecto). | `Path` |
| `BackupService.origen_db` | `propiedad -> Path` | Ruta de la base de origen (inyectada o configurada). | `Path` |
| `BackupService.listar_backups` | `() -> list[BackupInfo]` | RF-01: lista los respaldos del más reciente al más antiguo. | `list[BackupInfo]` |
| `BackupService.crear_backup` | `() -> BackupInfo` | RF-02: crea una copia versionada de la base actual. | `BackupInfo` |
| `BackupService.proteger` | `(nombre: str) -> BackupInfo` | RF-03: marca el respaldo como no eliminable. | `BackupInfo` |
| `BackupService.desproteger` | `(nombre: str) -> BackupInfo` | RF-03: quita la protección del respaldo. | `BackupInfo` |
| `BackupService.eliminar` | `(nombre: str) -> None` | RF-04: elimina un respaldo desprotegido. | — |
| `BackupService._ruta` | `(nombre: str) -> Path` | Resuelve la ruta de un respaldo existente. | `Path` |
| `BackupService._describir` | `(archivo: Path) -> BackupInfo` | Construye los metadatos de un archivo. | `BackupInfo` |
| `BackupService._copiar` | `(origen: Path, destino: Path) -> None` | Copia con SQLite y degrada a copia de archivo. | — |
| `BackupService._siguiente_nombre` | `() -> str` | Nombre versionado `DD-MM-AAAA_Vn.db`. | `str` |
| `BackupService._version_de` | `(nombre: str) -> int \| None` | Extrae el número de versión del nombre. | `int` o `None` |
| `BackupService._nombre_protegido` | `(nombre: str) -> str` | Nombre con el sufijo `.protegido`. | `str` |
| `BackupService._nombre_desprotegido` | `(nombre: str) -> str` | Nombre sin el sufijo `.protegido`. | `str` |

DTO: `BackupInfo`. Excepciones: `BackupError`, `BackupProtegidoError`.
Constantes: `DIRECTORIO_POR_DEFECTO`, `VARIABLE_ENTORNO_DIRECTORIO`,
`VARIABLE_ENTORNO_ORIGEN`, `EXTENSION_BACKUP`, `SUFIJO_PROTEGIDO`,
`FORMATO_FECHA`, `SEPARADOR_VERSION`.

### Módulo `administrar_backups` — `src/certificado_operadores/modulos/administrar_backups/ui.py`

Interfaz de Streamlit de administración de backups (spec 005). Página delgada:
lista los respaldos y delega crear, proteger, desproteger y eliminar en
`BackupService`. No contiene operaciones de sistema de archivos ni sentencias
SQL (RNF-01).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `filas_backups` | `(backups: list[BackupInfo]) -> list[dict[str, object]]` | Mapea los respaldos a filas legibles para `st.dataframe`. | `list[dict]` |
| `_render_encabezado` | `() -> None` | Título y ayuda del módulo. | — |
| `_render_creacion` | `(fachada: BackupService) -> None` | Formulario de creación de respaldos. | — |
| `_render_proteccion` | `(fachada, respaldos) -> None` | Proteger / desproteger un respaldo. | — |
| `_render_eliminacion` | `(fachada, respaldos) -> None` | Eliminar un respaldo desprotegido. | — |
| `render_administrar_backups` | `(fachada: BackupService \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `FORMATO_FECHA_HORA`, `ETIQUETA_PROTEGIDO`, `ETIQUETA_DESPROTEGIDO`.
Punto de entrada: `src/certificado_operadores/pages/1_Configuracion.py` (importa
`render_administrar_backups` y lo invoca en la pestaña de backups).

### Módulo `administrar_backups` — pruebas

- **Ubicación:** `tests/test_backups.py`
- **Cobertura:** servicio contra directorio y base SQLite temporales (creación
  versionada RF-02 y copia consistente, listado RF-01, protección/
  desprotección RF-03, eliminación y bloqueo de protegidos RF-04, resolución
  por variable de entorno); funciones puras de la UI (`filas_backups`); y
  criterios estáticos (paquete CA-01, UI sin SO ni SQL CA-03/RNF-01, página con
  `render_administrar_backups` y sin `exec` CA-02/RNF-02). Patrón AAA.

### Módulo `infra.eventos_repository` — `src/certificado_operadores/infra/eventos_repository.py`

Repositorio de eventos de operadores (spec 006). Encapsula todo el acceso a
`fact_eventos_operador` y sus dimensiones: búsqueda con filtros, listado de
tipos de evento, agrupamiento por lote (minuto de cargue) y mutaciones de
reactivación, anulación y eliminación de registros o lotes. Cada mutación
registra su acción en `log_auditoria` dentro de la misma transacción.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `EventosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `EventosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `EventosRepository.listar_tipos_evento` | `() -> list[TipoEventoInfo]` | Lista los tipos de evento ordenados por id. | `list[TipoEventoInfo]` |
| `EventosRepository.buscar_eventos` | `(filtro: FiltroEventos \| None = None) -> list[EventoInfo]` | RF-01: filtra por código, cédula, tipo, vigencia y rango de fechas. | `list[EventoInfo]` |
| `EventosRepository.listar_lotes` | `() -> list[LoteInfo]` | RF-02: agrupa los eventos por minuto de cargue. | `list[LoteInfo]` |
| `EventosRepository.listar_eventos_de_lote` | `(lote: str) -> list[EventoInfo]` | RF-02: detalle de los eventos de un lote. | `list[EventoInfo]` |
| `EventosRepository.reactivar_registros` | `(ids: list[int], usuario: str) -> int` | CA-03: reactiva registros y audita. | `int` |
| `EventosRepository.anular_registros` | `(ids: list[int], usuario: str) -> int` | CA-03: anula registros y audita. | `int` |
| `EventosRepository.eliminar_registros` | `(ids: list[int], usuario: str) -> int` | CA-03: elimina registros y audita. | `int` |
| `EventosRepository.reactivar_lote` | `(lote: str, usuario: str) -> int` | RF-02: reactiva el lote completo y audita. | `int` |
| `EventosRepository.anular_lote` | `(lote: str, usuario: str) -> int` | RF-02: anula el lote completo y audita. | `int` |
| `EventosRepository.eliminar_lote` | `(lote: str, usuario: str) -> int` | RF-02: elimina el lote completo y audita. | `int` |
| `EventosRepository.registrar_auditoria` | `(usuario, accion, detalles) -> None` | Registra una acción en `log_auditoria`. | — |
| `_mapear_evento` | `(fila: RowMapping) -> EventoInfo` | Mapea una fila de eventos al DTO. | `EventoInfo` |
| `_condiciones_y_parametros` | `(filtro: FiltroEventos) -> tuple[list[str], dict[str, object]]` | Traduce el filtro a condiciones y parámetros enlazados. | `tuple` |

DTOs: `TipoEventoInfo`, `EventoInfo`, `LoteInfo`, `FiltroEventos`. Constantes:
`LIMITE_POR_DEFECTO`, `FORMATO_LOTE`, `ESTADO_VIGENTE_TEXTO`,
`ESTADO_ANULADO_TEXTO` y las acciones de auditoría `ACCION_*`.

### Módulo `correccion_registros` — `src/certificado_operadores/modulos/correccion_registros/ui.py`

Interfaz de Streamlit de corrección de registros (spec 006). Página delgada:
filtra eventos y delega reactivar, anular y eliminar (individuales o por lote)
en `EventosRepository`. No contiene sentencias SQL (RNF-01) ni conoce el esquema
(RNF-02).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `parsear_entero_positivo` | `(texto: str) -> int \| None` | Convierte el texto de un campo en un entero positivo. | `int` o `None` |
| `opciones_tipos_evento` | `(tipos: list[TipoEventoInfo]) -> list[str]` | Construye las opciones "id - nombre" del selector. | `list[str]` |
| `id_tipo_evento_desde_opcion` | `(opcion: str) -> int \| None` | Extrae el id del tipo de evento de la opción. | `int` o `None` |
| `vigencia_desde_estado` | `(estado: str) -> int \| None` | Traduce la opción de estado a la vigencia. | `int` o `None` |
| `construir_filtro` | `(codigo, cedula, tipo_evento, estado, fecha_desde, fecha_hasta) -> FiltroEventos` | Traduce los campos del formulario a un filtro. | `FiltroEventos` |
| `etiqueta_lote` | `(lote: LoteInfo) -> str` | Etiqueta "YYYY-MM-DD HH:MM (n reg.)" del selector. | `str` |
| `lote_desde_etiqueta` | `(etiqueta: str) -> str` | Recupera la marca temporal de la etiqueta. | `str` |
| `filas_eventos` | `(eventos: list[EventoInfo]) -> list[dict[str, object]]` | Mapea los DTOs a filas legibles para `st.dataframe`. | `list[dict]` |
| `filas_seleccionadas` | `(seleccion: object) -> list[int]` | Extrae los índices marcados en la tabla. | `list[int]` |
| `puede_eliminar` | `(rol: str) -> bool` | Indica si el rol puede eliminar (solo Super Admin). | `bool` |
| `_como_fecha` | `(valor: object) -> date \| None` | Normaliza el valor de `st.date_input` a fecha. | `date` o `None` |
| `render_correccion_registros` | `(repositorio: EventosRepository \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `ETIQUETA_TODOS`, `OPCION_VIGENTE`, `OPCION_ANULADO`,
`OPCIONES_ESTADO`, `SEPARADOR_OPCION`, `SEPARADOR_ETIQUETA_LOTE`. Punto de
entrada: `src/certificado_operadores/pages/1_Configuracion.py` (importa
`render_correccion_registros` y lo invoca en la pestaña de corrección). El
módulo heredado `modulos/3_Modificacion_Tablas.py` quedó **deprecado** como
redirección a esta interfaz.

### Módulo `correccion_registros` — pruebas

- **Ubicación:** `tests/test_correccion_registros.py`
- **Cobertura:** repositorio contra SQLite temporal (tipos de evento, búsqueda
  por código/cédula/tipo/vigencia/rango de fechas y límite, lotes y su detalle,
  reactivar/anular/eliminar individual y por lote con auditoría, selección
  vacía); funciones puras de la UI (`parsear_entero_positivo`,
  `opciones_tipos_evento`, `id_tipo_evento_desde_opcion`,
  `vigencia_desde_estado`, `construir_filtro`, `etiqueta_lote`/`lote_desde_etiqueta`,
  `filas_eventos`, `filas_seleccionadas`, `puede_eliminar`); y criterios
  estáticos (paquete CA-01, UI sin SQL CA-02/RNF-01, página sin funciones
  inlined con `render_correccion_registros` CA-02, módulo heredado deprecado sin
  SQL). Patrón AAA.

### Módulo `infra.catalogos_repository` — `src/certificado_operadores/infra/catalogos_repository.py`

Repositorio de la capa de infraestructura que encapsula **todo** el acceso a
datos de los cinco catálogos (`dim_empresa`, `dim_vehiculo`, `dim_impacto`,
`dim_comportamiento` y `dim_detalle_comportamiento`). Devuelve DTOs inmutables y
registra la auditoría de impacto, comportamiento y detalle dentro de la misma
transacción; empresa y vehículo preservan el comportamiento heredado (sin
auditoría).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `construir_descripcion_comportamiento` | `(tipo, servicios, jerarquia_1, jerarquia_2=None, jerarquia_3=None, jerarquia_4=None) -> str` | Compone la descripción `tipo::servicios::jerarquías` en minúsculas. | `str` |
| `CatalogosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `CatalogosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `CatalogosRepository.listar_empresas` | `() -> list[EmpresaInfo]` | RF-01: lista las empresas ordenadas. | `list[EmpresaInfo]` |
| `CatalogosRepository.crear_empresa` | `(nombre: str, usuario: str) -> int` | RF-01: crea una empresa activa con el siguiente id. | `int` |
| `CatalogosRepository.cambiar_vigencia_empresa` | `(id_empresa: int, vigencia: int) -> None` | RF-01: activa o inactiva una empresa. | — |
| `CatalogosRepository.renombrar_empresa` | `(id_empresa: int, nombre: str) -> None` | RF-01: renombra una empresa. | — |
| `CatalogosRepository.listar_vehiculos` | `() -> list[VehiculoInfo]` | RF-02: lista los vehículos ordenados. | `list[VehiculoInfo]` |
| `CatalogosRepository.crear_vehiculo` | `(nombre: str, usuario: str) -> int` | RF-02: crea un vehículo con el siguiente id. | `int` |
| `CatalogosRepository.renombrar_vehiculo` | `(id_vehiculo: int, nombre: str) -> None` | RF-02: renombra un vehículo. | — |
| `CatalogosRepository.listar_impactos` | `() -> list[ImpactoInfo]` | RF-03: lista los niveles de impacto. | `list[ImpactoInfo]` |
| `CatalogosRepository.crear_impacto` | `(nombre, maximo, dias_maximo, usuario) -> int` | RF-03: crea un impacto y audita. | `int` |
| `CatalogosRepository.actualizar_impacto` | `(id_impacto, nombre, maximo, dias_maximo, usuario) -> None` | RF-03: actualiza un impacto y audita. | — |
| `CatalogosRepository.listar_comportamientos` | `() -> list[ComportamientoInfo]` | RF-04: lista los comportamientos con su impacto. | `list[ComportamientoInfo]` |
| `CatalogosRepository.crear_comportamiento` | `(descripcion, id_impacto, usuario) -> int` | RF-04: crea un comportamiento y audita. | `int` |
| `CatalogosRepository.actualizar_comportamiento` | `(id_comportamiento, descripcion, id_impacto, usuario) -> None` | RF-04: actualiza un comportamiento y audita. | — |
| `CatalogosRepository.listar_detalles` | `(fuente: str \| None = None, limite: int = 500) -> list[DetalleComportamientoInfo]` | RF-05: lista los detalles, opcionalmente por fuente. | `list[DetalleComportamientoInfo]` |
| `CatalogosRepository.crear_detalle` | `(datos: DatosDetalleComportamiento, usuario: str) -> int` | RF-05: crea un detalle y audita. | `int` |
| `CatalogosRepository.actualizar_detalle` | `(id_jerarquia: int, datos, usuario: str) -> None` | RF-05: actualiza un detalle y audita. | — |
| `CatalogosRepository._siguiente_id` | `(tabla: str, columna: str) -> int` | Calcula `MAX(columna)+1` (tabla/columna internas). | `int` |
| `CatalogosRepository._parametros_detalle` | `(datos: DatosDetalleComportamiento) -> dict[str, object]` | Traduce el detalle a parámetros enlazados. | `dict` |
| `CatalogosRepository._auditar` | `(conexion, usuario, accion, detalles) -> None` | Inserta la auditoría en la transacción. | — |

DTOs: `EmpresaInfo` (con propiedad `estado`), `VehiculoInfo`, `ImpactoInfo`,
`ComportamientoInfo`, `DetalleComportamientoInfo` (salida) y
`DatosDetalleComportamiento` (entrada). Constantes: `LIMITE_DETALLES`,
`SEPARADOR_DESCRIPCION`, `ESTADO_EMPRESA_ACTIVA`, `ESTADO_EMPRESA_INACTIVA` y las
acciones `ACCION_CREAR_IMPACTO`, `ACCION_EDITAR_IMPACTO`,
`ACCION_CREAR_COMPORTAMIENTO`, `ACCION_EDITAR_COMPORTAMIENTO`,
`ACCION_CREAR_DETALLE`, `ACCION_EDITAR_DETALLE`.

### Módulo `catalogos` — `src/certificado_operadores/modulos/catalogos/ui.py`

Interfaz Streamlit de los cinco catálogos. Delega toda lectura y mutación en
`CatalogosRepository`; no contiene sentencias SQL (RNF-01) ni conoce el esquema.
El paquete expone `render_catalogos` en
`src/certificado_operadores/modulos/catalogos/__init__.py`.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `vigencia_desde_accion` | `(accion: str) -> int` | Traduce "Activar"/"Inactivar" a la vigencia. | `int` |
| `filas_empresas` | `(empresas: list[EmpresaInfo]) -> list[dict[str, object]]` | Mapea empresas a filas legibles. | `list[dict]` |
| `filas_vehiculos` | `(vehiculos: list[VehiculoInfo]) -> list[dict[str, object]]` | Mapea vehículos a filas legibles. | `list[dict]` |
| `filas_impactos` | `(impactos: list[ImpactoInfo]) -> list[dict[str, object]]` | Mapea impactos a filas legibles. | `list[dict]` |
| `filas_comportamientos` | `(comportamientos: list[ComportamientoInfo]) -> list[dict[str, object]]` | Mapea comportamientos a filas legibles. | `list[dict]` |
| `filas_detalles` | `(detalles: list[DetalleComportamientoInfo]) -> list[dict[str, object]]` | Mapea detalles a filas legibles. | `list[dict]` |
| `opciones_impacto` | `(impactos: list[ImpactoInfo]) -> dict[int, str]` | Mapa `{id_impacto: impacto}`. | `dict` |
| `id_impacto_desde_nombre` | `(opciones: dict[int, str], nombre: str) -> int \| None` | Recupera el id de un impacto por su nombre. | `int` o `None` |
| `opciones_comportamiento` | `(comportamientos: list[ComportamientoInfo]) -> dict[str, str]` | Mapa `{str(id): comportamiento}`. | `dict` |
| `render_catalogos` | `(repositorio: CatalogosRepository \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `USUARIO_POR_DEFECTO`, `ETIQUETA_TODAS_FUENTES`, `FUENTES_DETALLE`,
`ACCION_ACTIVAR`, `ACCION_INACTIVAR`, `ACCIONES_ESTADO`, `TITULO`. Punto de
entrada: `src/certificado_operadores/pages/1_Configuracion.py` (importa
`render_catalogos` y lo invoca en la pestaña de catálogos; ya **no** usa `exec`).

### Módulo `catalogos` — pruebas

- **Ubicación:** `tests/test_catalogos.py`
- **Cobertura:** repositorio contra SQLite temporal (listar/crear/activar/renombrar
  empresas; listar/crear/renombrar vehículos; listar/crear/actualizar impactos;
  listar/crear/actualizar comportamientos; listar por fuente/crear/actualizar
  detalles; auditoría y descripción compuesta); funciones puras de la UI
  (`vigencia_desde_accion`, `filas_*`, `opciones_impacto`,
  `id_impacto_desde_nombre`, `opciones_comportamiento`); y criterios estáticos
  (paquete CA-01, UI sin SQL RNF-01, repositorio que encapsula la SQL CA-03,
  página sin `exec` con `render_catalogos` CA-02/RNF-02). Patrón AAA.

## Detalle

### `OperadoresRepository.verificar_conexion`

- **Ubicación:** `src/certificado_operadores/infra/repository.py`
- **Responsabilidad única:** comprobar que la base SQLite responde.
- **Parámetros:** ninguno.
- **Devuelve:** `True` si la conexión es válida; `False` ante `SQLAlchemyError`.
- **Errores:** no propaga; los captura y los traduce a `False`.

### `OperadoresRepository.obtener_operador_por_cedula`

- **Ubicación:** `src/certificado_operadores/infra/repository.py`
- **Responsabilidad única:** buscar el operador asociado a una cédula.
- **Parámetros:** `cedula` — documento (`dim_persona.id_persona`).
- **Devuelve:** `OperadorInfo` del registro vigente de menor código, o `None`.
- **Errores:** ninguno (consulta parametrizada con `LEFT JOIN`).

### `OperadoresRepository.obtener_operador_por_codigo`

- **Ubicación:** `src/certificado_operadores/infra/repository.py`
- **Responsabilidad única:** buscar el operador asociado a un código de operación.
- **Parámetros:** `codigo` — `dim_codigo.id_codigo`.
- **Devuelve:** `OperadorInfo` o `None`.
- **Errores:** ninguno.

### `OperadoresRepository.validar_certificado`

- **Ubicación:** `src/certificado_operadores/infra/repository.py`
- **Responsabilidad única:** consultar los datos y obtener el estado del certificado.
- **Parámetros:** `codigo` — `dim_codigo.id_codigo`.
- **Devuelve:** `EstadoCertificado` con estado `VIGENTE`, `POR_VENCER`, `VENCIDO`, `SIN_CERTIFICADO` o `CANCELADO`.
- **Errores:** ninguno de negocio; el cálculo puro lo realiza `calcular_estado_certificado` en el dominio.

### `OperadoresRepository.estadisticas_basicas`

- **Ubicación:** `src/certificado_operadores/infra/repository.py`
- **Responsabilidad única:** contar operadores, vigencias, empresas y licencias.
- **Parámetros:** ninguno.
- **Devuelve:** `EstadisticasBasicas`. Si el esquema no está cargado, devuelve ceros.
- **Errores:** no propaga `SQLAlchemyError`; devuelve conteos en cero.

### `OperadoresFacade`

- **Ubicación:** `src/certificado_operadores/facade.py`
- **Responsabilidad única:** exponer los casos de uso y delegar en `OperadoresRepository`.
- **Contrato:** mantiene la firma pública previa; no contiene SQL ni reglas de negocio.

### Pruebas

- **Ubicación:** `tests/test_facade.py`
- **Cobertura:** conexión (éxito y fallo), consulta por cédula/código (con y sin resultados), validación de certificado (por vencer, vigente, vencido, sin certificado, cancelado) y estadísticas básicas. Patrón AAA con SQLite temporal e importación de los DTOs desde `domain.models`.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
