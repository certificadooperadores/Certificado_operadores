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
| `infra.seguridad` | `src/certificado_operadores/infra/seguridad.py` | Hashing de contraseñas (`bcrypt`) y firma/validación de tokens de sesión (`HMAC-SHA256`). |
| `infra.usuarios_repository` | `src/certificado_operadores/infra/usuarios_repository.py` | Acceso a datos de `dim_usuarios` y auditoría (SQLAlchemy). |
| `facade_usuarios` | `src/certificado_operadores/facade_usuarios.py` | Fachada de casos de uso de usuarios; orquesta y delega sin ejecutar SQL. |
| `ui_sesion` | `src/certificado_operadores/ui_sesion.py` | Soporte de sesión persistente y refresco de datos para Streamlit; consume el Facade. |
| `gestion_usuarios` | `src/certificado_operadores/modulos/gestion_usuarios/ui.py` | Interfaz Streamlit de gestión de usuarios; consume el Facade y no contiene SQL. |
| `infra.backup_service` | `src/certificado_operadores/infra/backup_service.py` | Servicio de copias de seguridad de SQLite; encapsula el sistema de archivos, la comparación y la restauración. |
| `administrar_backups` | `src/certificado_operadores/modulos/administrar_backups/ui.py` | Interfaz Streamlit de backups; consume `BackupService` y no contiene SO ni SQL. |
| `infra.eventos_repository` | `src/certificado_operadores/infra/eventos_repository.py` | Acceso a datos de `fact_eventos_operador`: filtros, lotes, mutaciones con auditoría, integridad referencial, catálogos oficiales, columnas completas de negocio y bloqueo de campos por categoría de evento (specs 006, 015, 017, 018, 019 y 020). |
| `correccion_registros` | `src/certificado_operadores/modulos/correccion_registros/ui.py` | Interfaz Streamlit de corrección de registros con editor tipo Excel, búsqueda rápida, acciones en bloque y proyección de columnas por categoría de evento; consume `EventosRepository` y no contiene SQL. |
| `infra.catalogos_repository` | `src/certificado_operadores/infra/catalogos_repository.py` | Acceso a datos de los cinco catálogos (empresas, vehículos, impactos, comportamientos y detalles) con auditoría (SQLAlchemy). |
| `catalogos` | `src/certificado_operadores/modulos/catalogos/ui.py` | Interfaz Streamlit de catálogos; consume `CatalogosRepository` y no contiene SQL. |
| `infra.certificados_repository` | `src/certificado_operadores/infra/certificados_repository.py` | Acceso a datos del registro de eventos y certificados: catálogos auxiliares, operador activo y registro con auditoría (SQLAlchemy). |
| `gestion_certificados` | `src/certificado_operadores/modulos/gestion_certificados/ui.py` | Interfaz Streamlit de gestión de certificados; consume `CertificadosRepository` y no contiene SQL. |
| `infra.comportamientos_repository` | `src/certificado_operadores/infra/comportamientos_repository.py` | Acceso a datos del reporte de comportamientos: búsqueda de operador, registro individual/masivo y reincidencia con auditoría (SQLAlchemy). |
| `reporte_comportamientos` | `src/certificado_operadores/modulos/reporte_comportamientos/ui.py` | Interfaz Streamlit del reporte de comportamientos; consume `ComportamientosRepository` y no contiene SQL. |
| `infra.reportes_repository` | `src/certificado_operadores/infra/reportes_repository.py` | Acceso a datos de la vista de reportes: catálogos de filtros, consultas consolidadas y auditoría de exportaciones (SQLAlchemy). |
| `reportes` | `src/certificado_operadores/modulos/reportes/ui.py` | Interfaz Streamlit de reportes y exportaciones; consume `ReportesRepository`, no contiene SQL ni `exec`. |
| `estilos` | `src/certificado_operadores/estilos.py` | Estilos visuales institucionales de Metrocali, paleta oficial y logo de la barra lateral (spec 023). |

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
| `RegistroOperador` | `cedula, nombres, primer_apellido, segundo_apellido, genero, id_empresa, id_perfil_tipologia, codigo=None, id_vigencia=VIGENCIA_ACTIVA` | Datos del formulario para crear/actualizar un operador (spec 023). |
| `ResultadoOperador` | `exito, mensaje, codigo=None` | Resultado del guardado de un operador (spec 023). |
| `EstadoCertificado` | `codigo, fecha_certificado, fecha_vencimiento, dias_restantes, estado, cancelado` | Resultado de validar el certificado. |
| `EstadisticasBasicas` | `total_operadores, operadores_vigentes, operadores_anulados, total_empresas, total_licencias` | Conteos para tableros. |

#### Constantes de negocio

`VIGENCIA_ACTIVA`, `VIGENCIA_ANULADA`, `ANIOS_VIGENCIA_CERTIFICADO`,
`DIAS_ALERTA_VENCIMIENTO`, `TIPOS_EVENTO_CERTIFICADO`, `TIPO_EVENTO_CANCELACION`
y los estados `ESTADO_VIGENTE`, `ESTADO_POR_VENCER`, `ESTADO_VENCIDO`,
`ESTADO_SIN_CERTIFICADO`, `ESTADO_CANCELADO`. La spec 023 añade los mensajes del
guardado de operadores: `MENSAJE_OPERADOR_CREADO`, `MENSAJE_OPERADOR_DUPLICADO`,
`MENSAJE_OPERADOR_CAMPOS_OBLIGATORIOS` y `MENSAJE_OPERADOR_ERROR`.

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
| `OperadoresRepository.listar_empresas` | `() -> list[EmpresaInfo]` | Spec 023: empresas concesionarias oficiales para el desplegable. | `list[EmpresaInfo]` |
| `OperadoresRepository.listar_tipologias` | `() -> list[TipologiaInfo]` | Spec 023: tipologías de bus oficiales con su descripción. | `list[TipologiaInfo]` |
| `OperadoresRepository.existe_operador_vigente` | `(cedula: int) -> bool` | Spec 023: indica si la cédula ya tiene un código vigente. | `bool` |
| `OperadoresRepository.crear_operador` | `(registro: RegistroOperador, usuario: str = "") -> int` | Spec 023: persiste persona y código, y audita en una sola transacción. | `int` |
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
| `OperadoresFacade.listar_empresas` | `() -> list[EmpresaInfo]` | Spec 023: empresas concesionarias oficiales. | `list[EmpresaInfo]` |
| `OperadoresFacade.listar_tipologias` | `() -> list[TipologiaInfo]` | Spec 023: tipologías de bus oficiales. | `list[TipologiaInfo]` |
| `OperadoresFacade.guardar_operador` | `(registro: RegistroOperador, usuario: str = "") -> ResultadoOperador` | Spec 023: valida duplicados y campos obligatorios y persiste el operador. | `ResultadoOperador` |
| `OperadoresFacade._campos_obligatorios` | `(registro: RegistroOperador) -> bool` | Indica si el registro trae los datos obligatorios. | `bool` |

### Módulo `admin_operadores` — `src/certificado_operadores/modulos/admin_operadores/ui.py`

Interfaz de Streamlit del módulo de administración de operadores (specs 003 y
023). Página delgada: busca la cédula en `OperadoresFacade` y presenta un
formulario horizontal con los datos personales y los desplegables oficiales de
empresa y tipología; el botón **Guardar Operador** delega en
`OperadoresFacade.guardar_operador`. No contiene sentencias de base de datos
(RNF-01) ni conoce el esquema (RNF-02).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `parsear_cedula` | `(texto: str) -> int \| None` | Convierte el texto del campo en una cédula positiva. | `int` o `None` |
| `construir_valores_formulario` | `(operador: OperadorInfo \| None, cedula: int \| None = None) -> dict[str, Any]` | Mapea el DTO del Facade a los valores por defecto del formulario (estado Creación/Actualización). | `dict` |
| `construir_registro` | `(datos: dict[str, Any]) -> RegistroOperador` | Spec 023: traduce los valores del formulario al DTO de guardado. | `RegistroOperador` |
| `_a_entero` | `(valor: Any) -> int` | Convierte un identificador opcional a entero (o cero). | `int` |
| `_a_entero_opcional` | `(valor: Any) -> int \| None` | Convierte un identificador opcional a entero o `None`. | `int` o `None` |
| `_indice_genero` | `(genero: str) -> int` | Índice de la etiqueta de género dentro de `GENEROS`. | `int` |
| `_indice_opcion` | `(catalogo: dict[str, int], valor: Any) -> int` | Índice de la opción cuyo identificador coincide. | `int` |
| `_texto_opcional` | `(valor: Any) -> str` | Convierte un identificador opcional a texto. | `str` |
| `_render_encabezado` | `() -> None` | Título y subtítulo descriptivo del módulo. | — |
| `_render_formulario` | `(valores: dict[str, Any], fachada: OperadoresFacade) -> None` | Spec 023: formulario horizontal con desplegables oficiales y botón Guardar. | — |
| `_render_consulta` | `(fachada: OperadoresFacade) -> None` | Captura la cédula, consulta el Facade y autocompleta. | — |
| `render_page` | `(fachada: OperadoresFacade \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `GENEROS` (Masculino/Femenino/Otro), `CODIGO_GENERO`,
`ETIQUETA_GENERO_POR_CODIGO`, `ESTADO_CREACION`, `ESTADO_ACTUALIZACION` y los
textos de la vista (`ENCABEZADO_*`, `ETIQUETA_*`, `MENSAJE_*`).

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
- **Ubicación (spec 023):** `tests/test_admin_operadores_guardado.py`
- **Cobertura (spec 023):** catálogos `listar_empresas`/`listar_tipologias`,
  detección de duplicados, `OperadoresFacade.guardar_operador` (creación con
  auditoría, duplicado, campos obligatorios y error de persistencia), funciones
  puras `construir_registro`/`_indice_genero` y criterios estáticos (botón
  Guardar y `guardar_operador` CA-05, formulario en columnas y desplegables
  CA-04, UI sin SQL). Patrón AAA contra SQLite temporal.

### Módulo `estilos` — `src/certificado_operadores/estilos.py`

Estilos visuales institucionales de Metrocali (spec 023). Capa de presentación
pura que centraliza la paleta clara oficial (azul `#046BD2`, fondo `#FFFFFF`,
fondo suave `#F8FAFC`, texto `#111827` y borde `#E5E7EB`), inyecta el CSS de
márgenes, tarjetas y pestañas, y publica el logo oficial en la barra lateral. No
accede a la base de datos.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `ruta_logo` | `() -> Path` | Resuelve la ruta del logo oficial (con variable de entorno opcional). | `Path` |
| `inyectar_estilos_metrocali` | `() -> None` | Inyecta el CSS institucional y muestra el logo lateral con `st.logo`. | — |

Constantes: `COLOR_PRIMARIO`, `COLOR_FONDO`, `COLOR_FONDO_SUAVE`,
`COLOR_TEXTO`, `COLOR_TEXTO_SECUNDARIO`, `COLOR_BORDE`, `NOMBRE_ARCHIVO_LOGO` y
`VARIABLE_ENTORNO_LOGO`. Se invoca desde `Inicio.py` y las tres páginas de
`pages/`.

### Módulo `estilos` — pruebas

- **Ubicación:** `tests/test_estilos.py`
- **Cobertura (spec 023):** paleta del tema global en `.streamlit/config.toml`
  (CA-01), ruta del logo por defecto y por variable de entorno (CA-02), e
  inyección del CSS y del logo (con y sin archivo) mediante un doble de
  Streamlit. Patrón AAA.

### Módulo `domain.usuarios` — `src/certificado_operadores/domain/usuarios.py`

Reglas puras de autorización y DTO de cuenta (spec 004); incluye los DTO y los
mensajes del inicio de sesión (spec 011).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `roles_asignables` | `(rol_solicitante: str) -> tuple[str, ...]` | Roles que puede asignar un solicitante (solo Super Admin asigna Super Admin). | `tuple[str, ...]` |
| `puede_modificar_usuario` | `(rol_solicitante: str, rol_objetivo: str) -> bool` | Indica si puede modificar una cuenta con ese rol. | `bool` |
| `puede_inactivar_usuario` | `(usuario_solicitante: str, usuario_objetivo: str, estado_nuevo: str) -> bool` | Impide inactivar la propia cuenta. | `bool` |

DTOs: `UsuarioInfo`, `ResultadoOperacion`, `CredencialesUsuario` (hash, rol y
estado para autenticar) y `ResultadoAutenticacion` (`exito`, `mensaje`, `rol`).
Constantes: `ROL_SUPER_ADMINISTRADOR`, `ROL_ADMINISTRADOR`, `ROL_GESTOR`,
`ROLES_ASIGNABLES_BASE`, `ESTADO_ACTIVO`, `ESTADO_INACTIVO`, `ESTADOS_USUARIO` y
los mensajes `MENSAJE_*` (incluidos `MENSAJE_LOGIN_EXITOSO`,
`MENSAJE_USUARIO_INACTIVO` y `MENSAJE_CONTRASENA_INCORRECTA`).

### Módulo `infra.seguridad` — `src/certificado_operadores/infra/seguridad.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `hashear_contrasena` | `(contrasena: str) -> str` | Genera el hash bcrypt de una contraseña. | `str` |
| `verificar_contrasena` | `(contrasena: str, hash_almacenado: str) -> bool` | Comprueba una contraseña contra su hash. | `bool` |
| `_clave_sesion` | `() -> bytes` | Devuelve la clave HMAC de ``SECRET_KEY_SESION`` o el valor por defecto. | `bytes` |
| `_firmar` | `(payload_codificado: str) -> str` | Calcula la firma HMAC-SHA256 de un payload en Base64. | `str` |
| `generar_token_sesion` | `(usuario: str, rol: str, timestamp: float \| None = None) -> str` | RF-01/RNF-01: firma un token autocontenido `<payload_b64>.<firma_hex>`. | `str` |
| `validar_token_sesion` | `(token: str, tiempo_max: int = 1200, ahora: float \| None = None) -> tuple[bool, str \| None, str \| None, str]` | Verifica firma y caducidad (20 min); devuelve `(válido, usuario, rol, motivo)`. | `tuple` |

Constantes (spec 013): `SEGUNDOS_INACTIVIDAD_SESION` (1200),
`VARIABLE_ENTORNO_CLAVE_SESION`, `CLAVE_SESION_POR_DEFECTO`, las claves del
payload `CLAVE_PAYLOAD_*`, los motivos `MOTIVO_VALIDO`, `MOTIVO_EXPIRADO`,
`MOTIVO_INVALIDO` y `SEPARADOR_TOKEN`.

### Módulo `infra.usuarios_repository` — `src/certificado_operadores/infra/usuarios_repository.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `UsuariosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor y asegura las tablas. | — |
| `UsuariosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `UsuariosRepository.asegurar_tablas` | `() -> None` | RF-01..RF-03: crea `dim_usuarios` y `log_auditoria` y siembra `admin` si la tabla está vacía. | — |
| `UsuariosRepository.listar_usuarios` | `() -> list[UsuarioInfo]` | Lista las cuentas ordenadas por id. | `list[UsuarioInfo]` |
| `UsuariosRepository.obtener_usuario` | `(usuario: str) -> UsuarioInfo \| None` | Consulta una cuenta por su nombre. | `UsuarioInfo` o `None` |
| `UsuariosRepository.obtener_para_autenticacion` | `(usuario: str) -> CredencialesUsuario \| None` | RF-01: consulta las credenciales seguras (hash, rol y estado) para el login. | `CredencialesUsuario` o `None` |
| `UsuariosRepository.existe_usuario` | `(usuario: str) -> bool` | Indica si la cuenta ya existe. | `bool` |
| `UsuariosRepository.crear_usuario` | `(usuario, password_hash, rol, estado) -> None` | Inserta una cuenta nueva. | — |
| `UsuariosRepository.actualizar_usuario` | `(usuario, rol, estado, password_hash=None) -> None` | Actualiza rol, estado y contraseña opcional. | — |
| `UsuariosRepository.registrar_auditoria` | `(usuario, accion, detalles) -> None` | Registra una acción en `log_auditoria`. | — |
| `_mapear_usuario` | `(fila: RowMapping) -> UsuarioInfo` | Mapea una fila de `dim_usuarios` al DTO. | `UsuarioInfo` |
| `_mapear_credenciales` | `(fila: RowMapping) -> CredencialesUsuario` | Mapea una fila de credenciales al DTO. | `CredencialesUsuario` |

Constantes de auto-aprovisionamiento (spec 012): `USUARIO_ADMIN_POR_DEFECTO`,
`CONTRASENA_ADMIN_POR_DEFECTO` y las sentencias DDL `_SQL_CREAR_TABLA_USUARIOS`,
`_SQL_CREAR_TABLA_LOGS` y `_SQL_CONTEO_USUARIOS`.

### Módulo `facade_usuarios` — `src/certificado_operadores/facade_usuarios.py`

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `UsuariosFacade.__init__` | `(engine=None, hasheador=hashear_contrasena, verificador=verificar_contrasena) -> None` | Inicializa la fachada con motor, hasheador y verificador inyectables. | — |
| `UsuariosFacade.motor` | `propiedad -> Engine` | Motor SQLAlchemy delegado al repositorio. | `Engine` |
| `UsuariosFacade.listar_usuarios` | `() -> list[UsuarioInfo]` | RF-01: lista las cuentas del sistema. | `list[UsuarioInfo]` |
| `UsuariosFacade.obtener_usuario` | `(usuario: str) -> UsuarioInfo \| None` | Consulta una cuenta por su nombre. | `UsuarioInfo` o `None` |
| `UsuariosFacade.autenticar` | `(usuario: str, contrasena: str) -> ResultadoAutenticacion` | RF-01..RF-04: valida credenciales, estado activo y contraseña contra el hash. | `ResultadoAutenticacion` |
| `UsuariosFacade.crear_usuario` | `(usuario, contrasena, rol, *, usuario_solicitante="") -> ResultadoOperacion` | RF-02: valida existencia, hashea con bcrypt y crea. | `ResultadoOperacion` |
| `UsuariosFacade.modificar_usuario` | `(usuario, rol, estado, contrasena=None, *, rol_solicitante="", usuario_solicitante="") -> ResultadoOperacion` | RF-03: aplica permisos y actualiza la cuenta. | `ResultadoOperacion` |
| `UsuariosFacade.generar_token_sesion` | `(usuario: str, rol: str) -> str` | CA-02: firma un token de sesión delegando en `infra.seguridad`. | `str` |
| `UsuariosFacade.validar_y_renovar_sesion` | `(token: str) -> tuple[bool, str \| None, str \| None, str \| None]` | CA-02: valida el token y, si es válido, devuelve uno renovado. | `tuple` |

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

### Punto de entrada `Inicio.py` — `src/certificado_operadores/Inicio.py`

Punto de entrada de Streamlit (specs 011 y 013). Captura las credenciales del
formulario de login y delega la autenticación en
`UsuariosFacade.autenticar(usuario, contrasena)`; no contiene sentencias SQL ni
importa controladores de base de datos o librerías criptográficas (RNF-01).
Solo tras un resultado exitoso persiste `logged_in`, `usuario` y `rol` en
`st.session_state` y publica el token firmado en `st.query_params["session"]`
(spec 013). Antes de mostrar el login intenta restaurar la sesión con
`ui_sesion.gestionar_sesion_activa()` y, ya autenticado, pinta los controles
laterales con `ui_sesion.render_controles_sesion_lateral(pagina_inicio=True)`. No
define funciones propias; el ajuste de `sys.path` permite importar el paquete
`certificado_operadores` desde la app.

### Módulo `Inicio.py` — pruebas

- **Ubicación:** `tests/test_autenticacion.py`
- **Cobertura:** `UsuariosFacade.autenticar` contra SQLite temporal (éxito RF-01
  con rol, contraseña incorrecta RF-04, usuario inexistente RF-02 e inactivo
  RF-03, campos obligatorios, verificador inyectado); método
  `UsuariosRepository.obtener_para_autenticacion` (DTO y `None`); inicialización
  resiliente (spec 012: creación automática de `dim_usuarios` y `log_auditoria`
  con siembra de `admin` en un motor en blanco, autenticación del `admin`
  sembrado, idempotencia de `asegurar_tablas` y escritura en `log_auditoria`);
  y criterios estáticos de `Inicio.py` (sin SQL ni acceso directo a la BD ni
  criptografía CA-02/RNF-01, delegación en `UsuariosFacade` CA-01/CA-02,
  persistencia de la sesión solo tras el éxito y compilación sin errores de
  sintaxis). Patrón AAA.

### Módulo `ui_sesion` — `src/certificado_operadores/ui_sesion.py`

Soporte de sesión persistente y refresco de datos para Streamlit (spec 013).
Capa de presentación pura: restaura la sesión desde el token firmado que viaja en
`st.query_params["session"]`, la renueva con la actividad reciente y pinta los
controles laterales de **Refrescar Datos** y **Cerrar Sesión**. No contiene SQL,
criptografía ni lógica de negocio: la firma y validación de tokens pasan por
`UsuariosFacade`.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `_restaurar_estado_sesion` | `(usuario: str, rol: str) -> None` | Registra la sesión restaurada en `st.session_state`. | — |
| `_actualizar_token_url` | `(fachada, usuario, rol) -> None` | Renueva el token de la URL con la actividad actual. | — |
| `_limpiar_sesion` | `() -> None` | Borra el estado de sesión y el token de la URL. | — |
| `gestionar_sesion_activa` | `(fachada: UsuariosFacade \| None = None) -> bool` | CA-03/CA-04: restaura la sesión desde la URL o la cierra si expiró. | `bool` |
| `_refrescar_datos` | `(fachada, usuario, rol) -> None` | CA-05: limpia las cachés de Streamlit y recarga sin cerrar sesión. | — |
| `render_controles_sesion_lateral` | `(fachada=None, *, pagina_inicio: bool = False) -> None` | Pinta los controles laterales (Refrescar Datos y Cerrar Sesión). | — |

Constantes: `CLAVE_QUERY_SESION`, `CLAVE_ESTADO_LOGGED_IN`, `CLAVE_ESTADO_USUARIO`,
`CLAVE_ESTADO_ROL`, `PAGINA_INICIO`, `ETIQUETA_REFRESCAR_DATOS`,
`ETIQUETA_CERRAR_SESION` y `MENSAJE_SESION_EXPIRADA`. Punto de entrada:
importado por `Inicio.py` y por `pages/1_Configuracion.py`,
`pages/2_Administracion_Operadores.py` y `pages/3_Reportes.py`.

### Módulo `ui_sesion` — pruebas

- **Ubicación:** `tests/test_seguridad_sesion.py`
- **Cobertura:** tokens HMAC-SHA256 (válidos dentro de 20 minutos, límite exacto
  de 1200 s, expiración a los 1201 s, firma manipulada, payload alterado, tokens
  mal formados y clave de entorno); `UsuariosFacade.generar_token_sesion` y
  `validar_y_renovar_sesion` (renovación, expirado e inválido); y la capa de UI
  con dobles de prueba (restauración desde la URL, expiración con limpieza y
  aviso, renovación por actividad, refresco con limpieza de caché y cierre de
  sesión). Incluye criterios estáticos (sin SQL en `ui_sesion`, controles de
  refrescar/cerrar, gestión de sesión en `Inicio.py` y en las tres páginas).
  Patrón AAA.

### Módulo `infra.backup_service` — `src/certificado_operadores/infra/backup_service.py`

Servicio de copias de seguridad de la base SQLite (spec 005 y 014). Encapsula la
gestión física de los respaldos con ruta de directorio y base de origen
**configurables** (variables de entorno `BACKUPS_DIR` y `BACKUP_DB_PATH`) y
valores por defecto relativos; no contiene rutas absolutas quemadas. La spec 014
añade la comparación preventiva de registros (`comparar_backup`) y la
restauración atómica con respaldo de rescate (`restaurar_backup`).

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
| `BackupService.comparar_backup` | `(nombre_backup: str) -> list[dict[str, object]]` | CA-01: compara los registros de las tablas maestras entre la base activa y el respaldo. | `list[dict]` |
| `BackupService.restaurar_backup` | `(nombre_backup: str, crear_respaldo_seguridad: bool = True) -> tuple[bool, str]` | CA-02: crea el respaldo preventivo y sobrescribe la base activa con la API atómica de SQLite. | `(bool, str)` |
| `BackupService._crear_respaldo_preventivo` | `() -> BackupInfo` | Crea el respaldo automático de rescate con los datos actuales. | `BackupInfo` |
| `BackupService._registrar_restauracion` | `(nombre_backup: str) -> None` | Inserta la versión restaurada en `dim_version_bd`. | — |
| `BackupService._ruta` | `(nombre: str) -> Path` | Resuelve la ruta de un respaldo existente. | `Path` |
| `BackupService._describir` | `(archivo: Path) -> BackupInfo` | Construye los metadatos de un archivo. | `BackupInfo` |
| `BackupService._copiar` | `(origen: Path, destino: Path) -> None` | Copia con SQLite y degrada a copia de archivo. | — |
| `BackupService._siguiente_nombre` | `() -> str` | Nombre versionado `DD-MM-AAAA_Vn.db`. | `str` |
| `BackupService._nombre_preventivo` | `() -> str` | Nombre único del respaldo preventivo `pre_restauracion_...`. | `str` |
| `BackupService._version_de` | `(nombre: str) -> int \| None` | Extrae el número de versión del nombre. | `int` o `None` |
| `BackupService._nombre_protegido` | `(nombre: str) -> str` | Nombre con el sufijo `.protegido`. | `str` |
| `BackupService._nombre_desprotegido` | `(nombre: str) -> str` | Nombre sin el sufijo `.protegido`. | `str` |

Función de módulo: `_contar_filas(ruta: Path, tabla: str) -> int` — cuenta las filas
de una tabla tolerando bases o tablas ausentes (devuelve 0).

DTO: `BackupInfo`. Excepciones: `BackupError`, `BackupProtegidoError`.
Constantes: `DIRECTORIO_POR_DEFECTO`, `VARIABLE_ENTORNO_DIRECTORIO`,
`VARIABLE_ENTORNO_ORIGEN`, `EXTENSION_BACKUP`, `SUFIJO_PROTEGIDO`,
`FORMATO_FECHA`, `FORMATO_FECHA_HORA`, `SEPARADOR_VERSION`,
`PREFIJO_RESPALDO_PREVENTIVO`, `TABLAS_COMPARACION`, `TABLA_VERSION_BD`,
`USUARIO_RESTAURACION_POR_DEFECTO`.

### Módulo `administrar_backups` — `src/certificado_operadores/modulos/administrar_backups/ui.py`

Interfaz de Streamlit de administración de backups (spec 005 y 014). Página
delgada: lista los respaldos y delega crear, proteger, desproteger, eliminar,
comparar y restaurar en `BackupService`. No contiene operaciones de sistema de
archivos ni sentencias SQL (RNF-01).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `filas_backups` | `(backups: list[BackupInfo]) -> list[dict[str, object]]` | Mapea los respaldos a filas legibles para `st.dataframe`. | `list[dict]` |
| `_impacto` | `(diferencia: int) -> str` | Traduce la diferencia de registros al semáforo (recupera, pierde o iguala). | `str` |
| `filas_comparacion` | `(comparacion: list[dict[str, object]]) -> list[dict[str, object]]` | CA-03: traduce la comparación a filas legibles con columna `Impacto`. | `list[dict]` |
| `_render_encabezado` | `() -> None` | Título y ayuda del módulo. | — |
| `_render_creacion` | `(fachada: BackupService) -> None` | Formulario de creación de respaldos. | — |
| `_render_proteccion` | `(fachada, respaldos) -> None` | Proteger / desproteger un respaldo. | — |
| `_render_eliminacion` | `(fachada, respaldos) -> None` | Eliminar un respaldo desprotegido. | — |
| `_render_restauracion` | `(fachada: BackupService, respaldos: list[BackupInfo]) -> None` | CA-03: análisis de diferencias y confirmación de la restauración. | — |
| `render_administrar_backups` | `(fachada: BackupService \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `FORMATO_FECHA_HORA`, `ETIQUETA_PROTEGIDO`, `ETIQUETA_DESPROTEGIDO`,
`IMPACTO_SIN_CAMBIOS`, `IMPACTO_RECUPERADOS`, `IMPACTO_PERDIDOS`.
Punto de entrada: `src/certificado_operadores/pages/1_Configuracion.py` (importa
`render_administrar_backups` y lo invoca en la pestaña de backups).

### Módulo `administrar_backups` — pruebas

- **Ubicación:** `tests/test_backups.py`
- **Cobertura:** servicio contra directorio y base SQLite temporales (creación
  versionada RF-02 y copia consistente, listado RF-01, protección/
  desprotección RF-03, eliminación y bloqueo de protegidos RF-04, resolución
  por variable de entorno, comparación de registros con diferencia por tabla y
  tolerancia a tablas ausentes CA-01, restauración atómica con respaldo
  preventivo y registro en `dim_version_bd` CA-02); funciones puras de la UI
  (`filas_backups` y `filas_comparacion` con semáforo); y criterios estáticos
  (paquete CA-01, UI sin SO ni SQL CA-03/RNF-01, sección de restauración con
  confirmación, página con `render_administrar_backups` y sin `exec`
  CA-02/RNF-02). Patrón AAA.

### Módulo `infra.eventos_repository` — `src/certificado_operadores/infra/eventos_repository.py`

Repositorio de eventos de operadores (specs 006, 015, 017, 018 y 019). Encapsula
todo el acceso a `fact_eventos_operador` y sus dimensiones: búsqueda con filtros,
listado de tipos de evento, agrupamiento por lote (minuto de cargue) y mutaciones
de reactivación, anulación y eliminación de registros o lotes. La spec 015 añade
el **catálogo declarativo `TABLAS_CORRECCION`** (Eventos, Licencias,
Comportamientos, Operadores y Códigos) y un listado y mutación **genéricos por
tabla**. La spec 017 añade la **integridad referencial** (conteo de dependencias y
bloqueo de borrado), la **validación de códigos** y la **edición segura de celdas**
tipo Excel con transacciones atómicas. La spec 018 añade los **catálogos oficiales
de listas desplegables** (licencias `C1`/`C2`/`C3` y fuentes/descripciones de
`dim_detalle_comportamiento`). La spec 019 amplía la definición de la tabla
**Eventos** con las **columnas completas de negocio** de Metrocali: las cinco
fechas (certificado, retiro, notificación de retiro, suspensión y prueba),
evaluador, vehículo evaluado y observación, todas editables, dejando `Cédula`,
`Nombre` y `Registro` como columnas protegidas. La spec 020 añade la **matriz de
compatibilidad `CAMPOS_PERMITIDOS_POR_EVENTO`** por categoría de evento, la
excepción `CampoIncompatibleError`, el **rechazo atómico** de campos prohibidos
(S-02), la **limpieza a `NULL`** de los campos huérfanos al cambiar el tipo de
evento (S-03) y la **validación de plausibilidad de fechas** (S-04). Cada mutación
registra su acción en `log_auditoria` dentro de la misma transacción.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `EventosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `EventosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `EventosRepository.listar_tipos_evento` | `() -> list[TipoEventoInfo]` | Lista los tipos de evento ordenados por id. | `list[TipoEventoInfo]` |
| `EventosRepository.listar_fuentes_comportamiento` | `() -> list[str]` | Spec 018: fuentes distintas de `dim_detalle_comportamiento` para el desplegable `Fuente`. | `list[str]` |
| `EventosRepository.listar_descripciones_comportamiento` | `() -> list[str]` | Spec 018: descripciones distintas del catálogo para el desplegable `Descripción`. | `list[str]` |
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
| `EventosRepository.listar_registros` | `(clave: str, limite: int = LIMITE_POR_DEFECTO) -> list[RegistroInfo]` | Spec 015: lista de forma compacta los registros de una tabla del catálogo. | `list[RegistroInfo]` |
| `EventosRepository.mutar_vigencia` | `(clave: str, ids: list[int], vigencia: int, usuario: str) -> int` | Spec 015: cambia la vigencia de los IDs de una tabla y audita. | `int` |
| `EventosRepository.eliminar_registros_tabla` | `(clave: str, ids: list[int], usuario: str) -> int` | Spec 015/017: elimina los IDs de una tabla; S-01 bloquea si tienen hijos dependientes. | `int` |
| `EventosRepository.contar_dependencias_operador` | `(id_persona: int, id_codigo: int \| None = None) -> dict[str, int]` | Spec 017/S-01: cuenta eventos, comportamientos y licencias del operador. | `dict` |
| `EventosRepository.validar_codigo_existe` | `(id_codigo: int) -> bool` | Spec 017/S-02: indica si el código existe en `dim_codigo`. | `bool` |
| `EventosRepository.actualizar_registros_seguros` | `(clave: str, cambios: list[CambioRegistro], usuario: str) -> int` | Specs 017/020: aplica ediciones validadas en una transacción atómica con auditoría; en Eventos aplica la matriz por categoría. | `int` |
| `EventosRepository._aplicar_cambios_simples` | `(conexion, definicion, cambios) -> int` | Spec 017: aplica los cambios genéricos de una tabla sin reglas por categoría. | `int` |
| `EventosRepository._aplicar_cambios_evento` | `(conexion, definicion, cambios) -> int` | Spec 020: agrupa los cambios de Eventos por fila y delega su validación/ejecución. | `int` |
| `EventosRepository._aplicar_cambios_evento_fila` | `(conexion, definicion, id_registro, cambios_fila) -> int` | Spec 020: valida compatibilidad y fechas, ejecuta los cambios y limpia campos huérfanos. | `int` |
| `EventosRepository._tipo_evento_efectivo` | `(conexion, id_registro, columnas, cambios_fila) -> tuple[int \| None, str]` | Spec 020: resuelve el tipo de evento efectivo (nuevo o actual) de una fila. | `tuple` |
| `EventosRepository._nombre_tipo_evento` | `(conexion, id_tipo_evento) -> str` | Spec 020: nombre legible de un tipo de evento (o su id). | `str` |
| `EventosRepository._validar_compatibilidad_evento` | `(cambios_fila, columnas, permitidos, nombre_evento) -> None` | Spec 020/S-02/S-04: rechaza campos prohibidos y fechas inválidas. | — |
| `EventosRepository._limpiar_campos_huerfanos` | `(conexion, definicion, id_registro, permitidos) -> None` | Spec 020/S-03: resetea a `NULL` los campos incompatibles con el nuevo tipo. | — |
| `EventosRepository._verificar_dependencias` | `(definicion: DefinicionTabla, ids: list[int]) -> None` | Spec 017/S-01: aborta el borrado si hay hijos dependientes. | — |
| `EventosRepository._resolver_valor` | `(conexion: Connection, columna: ColumnaEditable, valor: object) -> object` | Spec 017: valida y normaliza el valor de una celda editable. | `object` |
| `campos_permitidos_evento` | `(id_tipo_evento: int) -> frozenset[str]` | Spec 020/S-01: columnas permitidas de una categoría (restrictivas si no está listada). | `frozenset` |
| `_valor_vacio` | `(valor: object) -> bool` | Spec 020: indica si una celda está vacía (`None`, cadena en blanco o `NaN`). | `bool` |
| `_validar_fecha_evento` | `(valor: object, etiqueta: str) -> None` | Spec 020/S-04: valida formato `AAAA-MM-DD` y rechaza fechas futuras inverosímiles. | — |
| `_definicion` | `(clave: str) -> DefinicionTabla` | Busca la tabla en el catálogo; lanza `ValueError` si no existe. | `DefinicionTabla` |
| `_sql_listar` | `(definicion: DefinicionTabla) -> TextClause` | Construye el `SELECT` compacto aliasando columnas por posición. | `TextClause` |
| `_sql_cambiar_vigencia` | `(definicion: DefinicionTabla) -> TextClause` | Construye el `UPDATE ... IN :ids` de la tabla. | `TextClause` |
| `_sql_eliminar_tabla` | `(definicion: DefinicionTabla) -> TextClause` | Construye el `DELETE ... IN :ids` de la tabla. | `TextClause` |
| `_sql_actualizar_columna` | `(definicion: DefinicionTabla, columna: str) -> TextClause` | Spec 017: construye el `UPDATE` de una columna con valor enlazado. | `TextClause` |
| `_columna_editable` | `(definicion: DefinicionTabla, etiqueta: str) -> ColumnaEditable \| None` | Spec 017: busca la columna editable por su etiqueta. | `ColumnaEditable` o `None` |
| `_vigencia_desde_opcion` | `(valor: object) -> int` | Spec 017: traduce `vigente`/`anulado` a la vigencia numérica. | `int` |
| `_a_entero` | `(valor: object) -> int` | Spec 017: convierte una celda a entero tolerando cadenas/decimales. | `int` |
| `_mapear_registro` | `(definicion: DefinicionTabla, fila: RowMapping) -> RegistroInfo` | Mapea una fila genérica al DTO con etiquetas y vigencia. | `RegistroInfo` |
| `_mapear_evento` | `(fila: RowMapping) -> EventoInfo` | Mapea una fila de eventos al DTO. | `EventoInfo` |
| `_condiciones_y_parametros` | `(filtro: FiltroEventos) -> tuple[list[str], dict[str, object]]` | Traduce el filtro a condiciones y parámetros enlazados. | `tuple` |

DTOs: `TipoEventoInfo`, `EventoInfo`, `LoteInfo`, `FiltroEventos`, y los de la
spec 015 `ColumnaTabla`, `DefinicionTabla` y `RegistroInfo`; la spec 017 añade
`ColumnaEditable` (columna editable: etiqueta, columna física y tipo) y
`CambioRegistro` (cambio de celda: id, etiqueta y valor). Excepciones:
`DependenciaRegistroError` (S-01), `CodigoInexistenteError` (S-02),
`ColumnaProtegidaError` (S-03), `ValorInvalidoError` (S-04) y, de la spec 020,
`CampoIncompatibleError` (S-02). Constantes:
`LIMITE_POR_DEFECTO`, `FORMATO_LOTE`, `ESTADO_VIGENTE_TEXTO`,
`ESTADO_ANULADO_TEXTO`, `TABLA_PERSONA`, `ETIQUETA_ESTADO`, `OPCION_VIGENTE`,
`OPCION_ANULADO`, `OPCIONES_ESTADO`, `GENEROS_VALIDOS`, `OPCIONES_LICENCIA`
(`C1`/`C2`/`C3`, spec 018), los tipos de edición
`TIPO_EDICION_*`, los mensajes `MENSAJE_*` (dependencias, código inexistente,
columna protegida, valor inválido, campo incompatible y fechas, spec 020),
`TABLAS_CORRECCION` y las acciones de auditoría `ACCION_*` (incluidas
`ACCION_REACTIVAR_TABLA`, `ACCION_ANULAR_TABLA`, `ACCION_ELIMINAR_TABLA` y
`ACCION_EDITAR_TABLA`). La spec 020 añade además `CAMPOS_PERMITIDOS_POR_EVENTO`
(matriz `id_tipo_evento -> columnas`), `CAMPOS_EVENTO_EDITABLES`,
`CAMPOS_EVENTO_POR_DEFECTO`, `CAMPOS_FECHA_EVENTO`, `CLAVE_TABLA_EVENTOS`,
`ETIQUETA_EVENTO` y los identificadores `TIPO_EVENTO_*`.

### Módulo `correccion_registros` — `src/certificado_operadores/modulos/correccion_registros/ui.py`

Interfaz de Streamlit de corrección de registros (specs 015, 017, 018 y 019).
Página delgada: organiza la corrección en **sub-pestañas por tabla** (Eventos,
Licencias, Comportamientos, Operadores y Códigos), muestra en cada una un
**editor tipo hoja de cálculo** (``st.data_editor``) con listas desplegables en
las columnas permitidas, columnas protegidas de solo lectura y un botón explícito
**Guardar Cambios**; delega toda lectura, validación y mutación en
`EventosRepository`, que aplica integridad referencial y transacciones atómicas
con auditoría. La spec 018 añade la **barra de búsqueda rápida** (``🔍 Filtrar
tabla``), las listas oficiales de licencias y comportamientos, la tabla de
**Códigos** y los **botones de acción en bloque** (``Marcar Vigente``, ``Marcar
Anulado`` y ``Eliminar`` sobre las filas marcadas con la casilla ``Seleccionar``).
La spec 019 expone en la sub-pestaña Eventos las **columnas completas de negocio**
(fechas de certificado, retiro, notificación, suspensión y prueba, evaluador,
vehículo evaluado y observación) como celdas editables, manteniendo `Cédula`,
`Nombre` y `Registro` de solo lectura. La spec 020 añade un **selector de tipo de
evento** en la cabecera que proyecta las columnas visibles y editables a las
aplicables a la categoría elegida (o muestra todas con un aviso orientativo en
«Todos») y captura `CampoIncompatibleError` al guardar.
No contiene sentencias SQL (RNF-01) ni conoce el esquema (RNF-02).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `filas_editor` | `(definicion: DefinicionTabla, registros: list[RegistroInfo]) -> list[dict[str, object]]` | Spec 017: mapea los DTOs a filas del editor con `Estado` restringido. | `list[dict]` |
| `opciones_evento` | `(nombres_evento: list[str]) -> list[str]` | Spec 017: opciones de la lista de tipos de evento, sin duplicados. | `list[str]` |
| `id_tipo_evento_por_nombre` | `(tipos_evento: list[TipoEventoInfo], nombre: str) -> int \| None` | Spec 020/S-05: traduce el nombre del tipo de evento a su identificador. | `int` o `None` |
| `columnas_por_tipo_evento` | `(definicion: DefinicionTabla, id_tipo_evento: int \| None) -> DefinicionTabla` | Spec 020/S-05: proyecta Eventos a las columnas aplicables a la categoría. | `DefinicionTabla` |
| `filas_por_tipo_evento` | `(filas: list[dict[str, object]], nombre_evento: str) -> list[dict[str, object]]` | Spec 020/S-05: deja solo las filas del tipo de evento indicado. | `list[dict]` |
| `columnas_protegidas` | `(definicion: DefinicionTabla) -> list[str]` | Spec 017/S-03: encabezados de solo lectura (ID y columnas no editables). | `list[str]` |
| `configuracion_columnas` | `(definicion: DefinicionTabla, opciones_evento: list[str], opciones_fuente: list[str] \| None = None, opciones_descripcion: list[str] \| None = None) -> dict[str, Any]` | Specs 017/018: `column_config` del editor (SelectboxColumn, CheckboxColumn y columnas numéricas). | `dict` |
| `filtrar_filas` | `(filas: list[dict[str, object]], termino: str) -> list[dict[str, object]]` | Spec 018: busca el término en cualquier celda (sin distinguir mayúsculas). | `list[dict]` |
| `filas_con_seleccion` | `(filas: list[dict[str, object]]) -> list[dict[str, object]]` | Spec 018: añade la casilla `Seleccionar` (falsa) a cada fila. | `list[dict]` |
| `ids_seleccionados` | `(filas: list[dict[str, object]]) -> list[int]` | Spec 018: extrae los IDs de las filas con la casilla marcada. | `list[int]` |
| `detectar_cambios` | `(definicion, original, editado) -> list[CambioRegistro]` | Spec 017: compara filas y extrae las celdas editadas. | `list[CambioRegistro]` |
| `ids_eliminados` | `(original, editado) -> list[int]` | Spec 017: detecta las filas removidas por el usuario. | `list[int]` |
| `puede_eliminar` | `(rol: str) -> bool` | Indica si el rol puede eliminar (solo Super Admin). | `bool` |
| `_como_entero` | `(valor: object) -> int` | Convierte la columna ID del editor a entero. | `int` |
| `_editable_por_etiqueta` | `(definicion: DefinicionTabla) -> dict[str, ColumnaEditable]` | Indexa las columnas editables por etiqueta. | `dict` |
| `_config_editable` | `(columna: ColumnaEditable, opciones_evento: list[str], opciones_fuente: list[str], opciones_descripcion: list[str]) -> Any` | Configura una columna editable del editor (licencias, comportamientos, fechas ISO y columnas numéricas). | config |
| `_columnas_editables` | `(definicion: DefinicionTabla) -> list[str]` | Etiquetas editables, incluida la de estado. | `list[str]` |
| `_como_filas` | `(editor: object) -> list[dict[str, object]]` | Normaliza la salida de `st.data_editor` a filas. | `list[dict]` |
| `_render_mensaje` | `(definicion: DefinicionTabla) -> None` | Muestra y descarta el mensaje pendiente de la tabla. | — |
| `_guardar_mensaje` | `(definicion, tipo, mensaje) -> None` | Registra el mensaje de resultado para el `rerun`. | — |
| `_procesar_guardado` | `(repositorio, definicion, original, editor, rol, usuario) -> None` | Aplica ediciones y eliminaciones con manejo de errores. | — |
| `_procesar_bloque` | `(repositorio, definicion, ids, vigencia, rol, usuario) -> None` | Spec 018: aplica la acción en bloque (vigencia o eliminación) con auditoría. | — |
| `_render_encabezado` | `() -> None` | Ayuda del módulo. | — |
| `_render_tabla` | `(repositorio, definicion, rol, usuario, tipos_evento, opciones_fuente, opciones_descripcion) -> None` | Renderiza filtros (incluido el de categoría), editor Excel y acciones en bloque de una sub-pestaña. | — |
| `render_correccion_registros` | `(repositorio: EventosRepository \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `ETIQUETA_GUARDAR`, `MENSAJE_DISPONIBLE`, `ERROR_ELIMINAR_SIN_PERMISO`,
`MENSAJE_SIN_CAMBIOS` y, de la spec 018, `ETIQUETA_FILTRO`, `PLACEHOLDER_FILTRO`,
`ETIQUETA_SELECCION`, `ETIQUETA_VIGENTE_BLOQUE`, `ETIQUETA_ANULADO_BLOQUE`,
`ETIQUETA_ELIMINAR_BLOQUE`, `MENSAJE_SIN_SELECCION`, `MENSAJE_SIN_COINCIDENCIAS`;
de la spec 020, `ETIQUETA_TIPO_EVENTO`, `OPCION_TODOS_EVENTOS` y
`MENSAJE_RESTRICCIONES_EVENTO`; más los prefijos de claves de sesión
`PREFIJO_CLAVE_*` (incluidos
`PREFIJO_CLAVE_FILTRO` y `PREFIJO_CLAVE_BLOQUE`) y `CLAVE_TIPO_MENSAJE`. Punto de
entrada:
`src/certificado_operadores/pages/1_Configuracion.py` (importa
`render_correccion_registros` y lo invoca en la pestaña de corrección). El
módulo heredado `modulos/3_Modificacion_Tablas.py` quedó **deprecado** como
redirección a esta interfaz.

### Módulo `correccion_registros` — pruebas

- **Ubicación:** `tests/test_correccion_registros.py`
- **Cobertura:** repositorio contra SQLite temporal (tipos de evento, búsqueda
  por código/vigencia/rango de fechas y límite, lotes, reactivar/anular/eliminar
  individual y por lote con auditoría) y de la spec 015 (catálogo de las cinco
  tablas, listado genérico por tabla —incluida `Códigos` con operador, empresa y
  `Desde`—, `mutar_vigencia` y `eliminar_registros_tabla` con auditoría, selección
  vacía, clave desconocida); de la spec 017 (conteo de dependencias del operador,
  validación de códigos, bloqueo de borrado de operadores con hijos S-01,
  reasignación validada S-02, edición de estado/evento/género con listas S-03/S-04,
  rechazo de columnas protegidas y rollback atómico con auditoría S-05); de la
  spec 018 (catálogos de fuentes y descripciones, listas de licencias
  `C1`/`C2`/`C3`, fuentes y descripciones oficiales con rechazo de valores fuera
  del catálogo); de la spec 019 (presencia de las columnas completas de negocio en
  la definición de `Eventos` y su tipo de edición, listado de fechas/evaluador/
  vehículo/observación, y persistencia al editar fechas de certificado, retiro,
  notificación, prueba, evaluador, vehículo y observación); de la spec 020 (matriz
  `CAMPOS_PERMITIDOS_POR_EVENTO` por categoría, rechazo atómico de campos
  incompatibles con `CampoIncompatibleError`, limpieza a `NULL` de campos huérfanos
  al cambiar el tipo de evento, validación de fechas con formato o valor inválidos,
  y proyección de columnas y filas por tipo de evento en la UI); funciones
  puras de la UI (`filas_editor`,
  `columnas_protegidas`, `configuracion_columnas`, `detectar_cambios`,
  `ids_eliminados`, `opciones_evento`, `puede_eliminar`, `filtrar_filas`,
  `filas_con_seleccion`, `ids_seleccionados`); y criterios estáticos (paquete
  CA-01, sub-pestañas por tabla CA-01, editor `st.data_editor` con
  `SelectboxColumn`/`CheckboxColumn` y columnas protegidas CA-01, buscador rápido
  CA-01, botones de acción en bloque CA-05, botón Guardar Cambios CA-04, métodos
  de seguridad del repositorio CA-02/CA-03, UI sin SQL CA-02/RNF-01, página sin
  funciones inlined con `render_correccion_registros` CA-02, módulo heredado
  deprecado sin SQL). Patrón AAA.

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

### Módulo `infra.certificados_repository` — `src/certificado_operadores/infra/certificados_repository.py`

Repositorio de la capa de infraestructura que encapsula **todo** el acceso a
datos del registro de eventos y certificados: catálogos auxiliares (tipos de
evento, vehículos y evaluadores), búsqueda del operador activo por cédula o
código y la inserción de eventos en `fact_eventos_operador` con su auditoría en
la misma transacción. Reutiliza `TipoEventoInfo` y `VehiculoInfo` de los otros
repositorios.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `CertificadosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `CertificadosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `CertificadosRepository.listar_tipos_evento` | `() -> list[TipoEventoInfo]` | Lista los tipos de evento ordenados por id. | `list[TipoEventoInfo]` |
| `CertificadosRepository.listar_vehiculos` | `() -> list[VehiculoInfo]` | Lista los vehículos evaluables ordenados por id. | `list[VehiculoInfo]` |
| `CertificadosRepository.listar_evaluadores` | `() -> list[str]` | Lista los evaluadores históricos distintos. | `list[str]` |
| `CertificadosRepository.buscar_operador_activo_por_codigo` | `(codigo: int) -> OperadorActivoInfo \| None` | RF-01: operador vigente y no cancelado por código. | `OperadorActivoInfo` o `None` |
| `CertificadosRepository.buscar_operador_activo_por_cedula` | `(cedula: int) -> OperadorActivoInfo \| None` | RF-01: código activo no cancelado más reciente del operador. | `OperadorActivoInfo` o `None` |
| `CertificadosRepository.registrar_evento` | `(datos: DatosEvento, usuario: str) -> int` | RF-02: inserta un evento y audita; devuelve su id. | `int` |
| `CertificadosRepository.registrar_eventos` | `(eventos: list[DatosEvento], usuario, accion, detalles) -> int` | RF-03: inserta varios eventos y una auditoría. | `int` |
| `CertificadosRepository._siguiente_id` | `() -> int` | Calcula `MAX(id_hecho_evento)+1`. | `int` |
| `CertificadosRepository._parametros_evento` | `(datos, id_hecho_evento, usuario) -> dict[str, object]` | Traduce el evento a parámetros enlazados. | `dict` |
| `CertificadosRepository._auditar` | `(conexion, usuario, accion, detalles) -> None` | Inserta la auditoría en la transacción. | — |
| `_formatear_fecha` | `(valor: date \| None) -> str \| None` | Convierte una fecha a texto ISO. | `str` o `None` |
| `_mapear_operador` | `(fila: RowMapping) -> OperadorActivoInfo` | Mapea una fila al DTO de operador activo. | `OperadorActivoInfo` |

DTOs: `OperadorActivoInfo` (con `nombre_completo()`) y `DatosEvento` (entrada).
Constantes: `TIPO_EVENTO_*` (certificación, reactivación, renovación,
observación, restricción médica, suspensión, cancelación, advertencia,
condicionamiento) y `ACCION_REGISTRO_EVENTO`, `ACCION_CARGA_MASIVA`.

### Módulo `gestion_certificados` — `src/certificado_operadores/modulos/gestion_certificados/ui.py`

Interfaz Streamlit de registro de eventos e historial (spec 008). Ofrece el
ingreso individual y la carga masiva desde Excel; busca al operador activo y
delega todo el acceso a datos en `CertificadosRepository`. No contiene sentencias
SQL (RNF-01) ni conoce el esquema. El paquete expone `render_gestion_certificados`
en `src/certificado_operadores/modulos/gestion_certificados/__init__.py`.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `limpiar_texto` | `(valor: object) -> str \| None` | Normaliza un texto vacío/`NaN` a `None`. | `str` o `None` |
| `limpiar_entero` | `(valor: object) -> int \| None` | Normaliza un entero (admite decimales de Excel). | `int` o `None` |
| `parsear_entero` | `(texto: str) -> int \| None` | Convierte el campo de búsqueda en entero. | `int` o `None` |
| `es_codigo_operacion` | `(texto: str) -> bool` | Indica si el texto es un código (cinco dígitos o menos). | `bool` |
| `opciones_evento` | `(tipos: list[TipoEventoInfo]) -> list[str]` | Construye las opciones "id - nombre". | `list[str]` |
| `id_desde_opcion` | `(opcion: str) -> int` | Extrae el id de tipo de evento de la opción. | `int` |
| `nombre_hoja` | `(id_tipo_evento: int) -> str` | Hoja de Excel del tipo de evento. | `str` |
| `_como_fecha` | `(valor: object) -> date \| None` | Normaliza una fecha del formulario o del Excel. | `date` o `None` |
| `validar_evento_individual` | `(id_tipo_evento: int, campos: Mapping[str, object]) -> list[str]` | RF-02: valida los campos del evento individual. | `list[str]` |
| `validar_fila_masiva` | `(id_tipo_evento: int, fila: Mapping[str, object]) -> str` | RF-03: valida una fila de la carga masiva. | `str` |
| `construir_datos_evento` | `(id_codigo: int, id_tipo_evento: int, campos) -> DatosEvento` | Traduce los campos a un `DatosEvento`. | `DatosEvento` |
| `construir_datos_desde_fila` | `(id_tipo_evento: int, id_codigo: int, fila) -> DatosEvento` | Traduce una fila del Excel a `DatosEvento`. | `DatosEvento` |
| `construir_plantilla_eventos` | `(evaluadores: list[str]) -> bytes` | Genera el Excel de la plantilla maestra. | `bytes` |
| `render_gestion_certificados` | `(repositorio: CertificadosRepository \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `TITULO`, `EVALUADOR_OTRO`, `SEPARADOR_OPCION`,
`NOMBRE_ARCHIVO_PLANTILLA`, `TIPO_MIME_EXCEL`, `HOJA_INSTRUCCIONES`,
`HOJAS_POR_EVENTO`, `COLUMNAS_POR_EVENTO`, `INSTRUCCIONES_PLANTILLA`,
`ESTADO_LISTO`, `VALIDACION_OK` y los mensajes `ERROR_*`. Punto de entrada:
`src/certificado_operadores/pages/2_Administracion_Operadores.py` (importa
`render_gestion_certificados` y lo invoca en la pestaña 2; ya **no** usa `exec`).
El módulo heredado `modulos/6_Gestion_Certificados.py` quedó **deprecado** como
redirección a esta interfaz.

### Módulo `gestion_certificados` — pruebas

- **Ubicación:** `tests/test_gestion_certificados.py`
- **Cobertura:** repositorio contra SQLite temporal (tipos de evento, vehículos,
  evaluadores, operador activo por cédula y código incluyendo cancelados e
  inactivos, registro individual y masivo con auditoría, lista vacía); funciones
  puras de la UI (`parsear_entero`, `es_codigo_operacion`, `limpiar_texto`,
  `limpiar_entero`, `opciones_evento`/`id_desde_opcion`, `nombre_hoja`,
  `validar_evento_individual`, `validar_fila_masiva`,
  `construir_datos_desde_fila`, `construir_plantilla_eventos`); y criterios
  estáticos (paquete CA-01, UI sin SQL RNF-01, repositorio que encapsula la SQL
  CA-03, página sin `exec` con `render_gestion_certificados` CA-02/RNF-02,
  módulo heredado deprecado sin SQL). Patrón AAA.

### Módulo `infra.comportamientos_repository` — `src/certificado_operadores/infra/comportamientos_repository.py`

Repositorio de la capa de infraestructura que encapsula **todo** el acceso a
datos del reporte de comportamientos (spec 009): búsqueda del operador por cédula
o código, jerarquías de comportamiento, registro individual y masivo en
`fact_comportamiento` con auditoría y el cálculo/consulta de la reincidencia
(`fact_reincidencia`, `reincidencia_detalle` y las acciones en
`fact_eventos_operador`). Conserva la ventana heredada de reincidencia
(`MESES_VENTANA_REINCIDENCIA`).

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `ComportamientosRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `ComportamientosRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `ComportamientosRepository.buscar_operador_por_codigo` | `(codigo: int) -> OperadorComportamientoInfo \| None` | RF-01: operador por código vigente. | `OperadorComportamientoInfo` o `None` |
| `ComportamientosRepository.buscar_operador_por_cedula` | `(cedula: int) -> OperadorComportamientoInfo \| None` | RF-01: código activo más reciente del operador. | `OperadorComportamientoInfo` o `None` |
| `ComportamientosRepository.listar_detalles_comportamiento` | `() -> list[DetalleComportamientoInfo]` | RF-01: jerarquías ordenadas por descripción. | `list[DetalleComportamientoInfo]` |
| `ComportamientosRepository.registrar_comportamiento` | `(datos: DatosComportamiento, usuario: str) -> int` | RF-01: inserta un comportamiento y audita. | `int` |
| `ComportamientosRepository.resolver_codigo_activo` | `(codigo: int) -> int \| None` | RF-02: valida que el código esté vigente. | `int` o `None` |
| `ComportamientosRepository.resolver_jerarquia_por_descripcion` | `(descripcion: str) -> int \| None` | RF-02: traduce la descripción a su jerarquía. | `int` o `None` |
| `ComportamientosRepository.buscar_comportamiento_por_caso` | `(caso: str) -> int \| None` | RF-02: comportamiento existente por caso. | `int` o `None` |
| `ComportamientosRepository.guardar_comportamientos` | `(filas: Sequence[DatosComportamiento], usuario: str) -> tuple[int, int]` | RF-02: inserta/actualiza en lote y audita. | `(nuevos, actualizados)` |
| `ComportamientosRepository.listar_impactos` | `() -> list[ImpactoInfo]` | RF-03: impactos con máximo mayor que cero. | `list[ImpactoInfo]` |
| `ComportamientosRepository.listar_comportamientos_por_impacto` | `(id_impacto: int) -> list[ComportamientoReincidenciaInfo]` | RF-03: comportamientos del impacto. | `list[ComportamientoReincidenciaInfo]` |
| `ComportamientosRepository.listar_codigos_pendientes` | `(id_comportamiento: int) -> list[int]` | RF-03: códigos con hechos pendientes. | `list[int]` |
| `ComportamientosRepository.listar_hechos_pendientes` | `(id_comportamiento: int, id_codigo: int) -> list[HechoComportamientoInfo]` | RF-03: hechos pendientes ordenados por fecha. | `list[HechoComportamientoInfo]` |
| `ComportamientosRepository.listar_pares_reincidencia` | `() -> set[tuple[int, int]]` | RF-03: pares de hechos ya registrados. | `set[tuple[int, int]]` |
| `ComportamientosRepository.generar_reincidencias` | `() -> int` | RF-03: analiza y crea los casos nuevos. | `int` |
| `ComportamientosRepository.listar_empresas` | `() -> list[EmpresaInfo]` | RF-03: empresas ordenadas por nombre. | `list[EmpresaInfo]` |
| `ComportamientosRepository.listar_reincidencias` | `() -> list[ReincidenciaInfo]` | RF-03: casos del más reciente al más antiguo. | `list[ReincidenciaInfo]` |
| `ComportamientosRepository.listar_detalle_reincidencias` | `() -> list[DetalleReincidenciaInfo]` | RF-03: detalle de hechos de los casos. | `list[DetalleReincidenciaInfo]` |
| `ComportamientosRepository.obtener_reincidencia_accion` | `(id_reincidencia: int) -> ReincidenciaAccionInfo \| None` | RF-03: código y evento de un caso. | `ReincidenciaAccionInfo` o `None` |
| `ComportamientosRepository.actualizar_determinacion` | `(id_reincidencia: int, determinacion: str, usuario: str) -> None` | RF-03: fija la determinación y audita. | — |
| `ComportamientosRepository.registrar_accion_reincidencia` | `(accion: AccionReincidencia, usuario: str) -> int` | RF-03: registra/actualiza la acción en el historial. | `int` |
| `ComportamientosRepository.importar_acciones_reincidencia` | `(acciones: Sequence[AccionReincidencia], usuario: str) -> tuple[int, int]` | RF-03: importa acciones en lote y audita. | `(insertados, actualizados)` |
| `ComportamientosRepository.registrar_reincidencia` | `(id_impacto, id_comportamiento, id_codigo, fecha_inicio, fecha_fin, cantidad, resumen, usuario, hechos) -> int` | RF-03: guarda un caso y sus hechos. | `int` |

DTOs: `OperadorComportamientoInfo` (con `nombre_completo()`),
`DetalleComportamientoInfo`, `DatosComportamiento` (entrada), `ImpactoInfo`,
`ComportamientoReincidenciaInfo`, `HechoComportamientoInfo`, `EmpresaInfo`,
`ReincidenciaInfo`, `DetalleReincidenciaInfo`, `ReincidenciaAccionInfo` y
`AccionReincidencia` (entrada). Constantes: `MESES_VENTANA_REINCIDENCIA`,
`VENTANA_REINCIDENCIA_SQL`, `NOMBRE_IMPACTO_GRAVE`, `TIPO_EVENTO_CANCELACION` y
las acciones `ACCION_*`.

### Módulo `reporte_comportamientos` — `src/certificado_operadores/modulos/reporte_comportamientos/ui.py`

Interfaz Streamlit del reporte de comportamientos (spec 009): ingreso individual,
carga masiva desde Excel y reincidencia. Delega todo el acceso a datos en
`ComportamientosRepository`; no contiene sentencias SQL (RNF-01) ni conoce el
esquema. El paquete expone `render_reporte_comportamientos` en
`src/certificado_operadores/modulos/reporte_comportamientos/__init__.py`.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `parsear_entero` | `(texto: str) -> int \| None` | Convierte el campo de búsqueda en entero. | `int` o `None` |
| `es_codigo_operacion` | `(texto: str) -> bool` | Indica si el texto es un código (cinco dígitos o menos). | `bool` |
| `opciones_detalle` | `(detalles: list[DetalleComportamientoInfo]) -> dict[str, str]` | Mapa `{str(id_jerarquia): descripción}`. | `dict` |
| `texto_celda` | `(valor: object) -> str \| None` | Normaliza una celda de Excel a texto. | `str` o `None` |
| `entero_celda` | `(valor: object) -> int \| None` | Normaliza una celda de Excel a entero. | `int` o `None` |
| `fecha_celda` | `(valor: object) -> date \| None` | Normaliza una celda de Excel a fecha. | `date` o `None` |
| `fecha_texto` | `(valor: object) -> str \| None` | Formatea una celda de fecha como `YYYY-MM-DD`. | `str` o `None` |
| `construir_plantilla_comportamiento` | `() -> bytes` | Genera el Excel de la plantilla de comportamientos. | `bytes` |
| `construir_plantilla_acciones` | `() -> bytes` | Genera el Excel de la plantilla de acciones. | `bytes` |
| `filas_reincidencias` | `(casos: list[ReincidenciaInfo]) -> list[dict[str, object]]` | Mapea los casos a filas legibles. | `list[dict]` |
| `filas_detalle_reincidencias` | `(detalles: list[DetalleReincidenciaInfo]) -> list[dict[str, object]]` | Mapea el detalle a filas legibles. | `list[dict]` |
| `render_reporte_comportamientos` | `(repositorio: ComportamientosRepository \| None = None) -> None` | Renderiza la pestaña completa (punto de entrada de `pages/`). | — |

Constantes: `TITULO`, `USUARIO_POR_DEFECTO`, `NOMBRE_ARCHIVO_PLANTILLA`,
`NOMBRE_ARCHIVO_PLANTILLA_ACCIONES`, `TIPO_MIME_EXCEL`, `HOJA_INSTRUCCIONES`,
`HOJA_DATOS`, `OPCIONES_DETERMINACION`, `TIPO_EVENTO_POR_DETERMINACION`,
`TIPO_EVENTO_POR_ACCION`, `COLUMNAS_PLANTILLA_COMPORTAMIENTO`,
`INSTRUCCIONES_COMPORTAMIENTO`, `COLUMNAS_PLANTILLA_ACCIONES` e
`INSTRUCCIONES_ACCIONES`. Punto de entrada:
`src/certificado_operadores/pages/2_Administracion_Operadores.py` (importa
`render_reporte_comportamientos` y lo invoca en la pestaña 3; la página queda
100% libre de `exec`, cerrando la Fase 2).

### Módulo `reporte_comportamientos` — pruebas

- **Ubicación:** `tests/test_reporte_comportamientos.py`
- **Cobertura:** repositorio contra SQLite temporal (búsqueda de operador por
  código/cédula incluyendo inactivos, detalles, registro individual y masivo con
  auditoría, resolución de código/jerarquía/caso, evaluación de reincidencia
  grave y por pares, ventana temporal, listados y detalle, determinación, acción
  e importación de acciones); funciones puras de la UI (`parsear_entero`,
  `es_codigo_operacion`, `opciones_detalle`, `texto_celda`, `entero_celda`,
  `fecha_celda`, `fecha_texto`, plantillas Excel y `filas_reincidencias`); y
  criterios estáticos (paquete CA-01, UI sin SQL RNF-01, repositorio que
  encapsula la SQL CA-03, página sin `exec` con `render_reporte_comportamientos`
  CA-02/RNF-02). Patrón AAA.

### Módulo `infra.reportes_repository` — `src/certificado_operadores/infra/reportes_repository.py`

Repositorio de la capa de infraestructura que encapsula **todo** el acceso a
datos de la vista de reportes (spec 010): los catálogos de filtros (empresas,
tipologías, tipos de evento e impactos), las consultas consolidadas con sus
filtros dinámicos (UTRYT, operadores por empresa, licencias/certificados por
vencer, eventos, reincidencias y comportamientos), la auditoría de exportaciones
y la construcción de Excel/CSV en memoria. Las columnas de los filtros viven
aquí, nunca en la UI.

La spec 022 hace **todas** las consultas 100 % compatibles con SQLite: usa
`DATE(columna)` y modificadores de fecha (`DATE(fecha, '+3 years')`) en lugar de
la sintaxis PostgreSQL, calcula diferencias de días con `JULIANDAY`, expresa el
filtro de vencimiento como `DATE('now', '+' || :dias || ' days')` y sustituye la
selección distinta de certificados por `ROW_NUMBER() OVER (PARTITION BY id_codigo
ORDER BY fecha_certificado DESC)` filtrando `rn = 1`.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `ReportesRepository.__init__` | `(engine: Engine \| None = None) -> None` | Inicializa el repositorio inyectando el motor. | — |
| `ReportesRepository.motor` | `propiedad -> Engine` | Motor SQLAlchemy (inyectado o resuelto de `db.get_engine`). | `Engine` |
| `ReportesRepository.listar_reportes` | `() -> tuple[DefinicionReporte, ...]` | RF-01: reportes disponibles con metadatos (sin SQL). | `tuple[DefinicionReporte, ...]` |
| `ReportesRepository.listar_empresas` | `() -> list[EmpresaInfo]` | RF-01: empresas ordenadas por identificador. | `list[EmpresaInfo]` |
| `ReportesRepository.listar_tipologias` | `() -> list[TipologiaInfo]` | RF-01: tipologías con su descripción legible. | `list[TipologiaInfo]` |
| `ReportesRepository.listar_estados` | `() -> list[str]` | RF-01: etiquetas del filtro de estado. | `list[str]` |
| `ReportesRepository.listar_tipos_evento` | `() -> list[TipoEventoInfo]` | RF-01: tipos de evento ordenados. | `list[TipoEventoInfo]` |
| `ReportesRepository.listar_impactos` | `() -> list[ImpactoInfo]` | RF-01: impactos ordenados. | `list[ImpactoInfo]` |
| `ReportesRepository.construir_condiciones` | `(id_reporte: str, seleccion: SeleccionFiltros) -> tuple[list[str], dict[str, object]]` | RF-02: traduce la selección a condiciones y parámetros SQL. | `(condiciones, parametros)` |
| `ReportesRepository.ejecutar_reporte` | `(id_reporte: str, seleccion: SeleccionFiltros) -> pd.DataFrame` | RF-02: ejecuta el reporte con sus filtros. | `pd.DataFrame` |
| `ReportesRepository.registrar_exportacion` | `(usuario: str, nombre_reporte: str, total: int) -> None` | RF-03: audita la exportación del reporte. | — |
| `construir_descripcion_tipologia` | `(id_perfil_tipologia, articulado, padron, complementario, auxiliar) -> str` | Construye la descripción legible de una tipología. | `str` |
| `construir_consulta` | `(consulta_base: str, condiciones: list[str]) -> str` | Inyecta las condiciones con `AND` sobre `WHERE 1=1`. | `str` |
| `generar_excel` | `(df: pd.DataFrame, nombre: str) -> bytes` | Genera un libro Excel en memoria con hoja de resumen. | `bytes` |
| `generar_csv` | `(df: pd.DataFrame) -> bytes` | Genera un CSV UTF-8 con BOM en memoria. | `bytes` |

DTOs: `EmpresaInfo`, `TipologiaInfo`, `TipoEventoInfo`, `ImpactoInfo`,
`DefinicionFiltro`, `DefinicionReporte` y `SeleccionFiltros` (entrada).
Constantes: `TIPO_MIME_EXCEL`, `TIPO_MIME_CSV`, `ACCION_EXPORTAR_REPORTE`,
`OPCIONES_ESTADO`, `OPCIONES_ESTADO_ACTIVO`, `ESTADO_A_VIGENCIA` y los límites de
`dias_vencer`. La spec 022 añade las expresiones de fecha portables
`_MODIFICADOR_VIGENCIA`, `_COL_VENCIMIENTO_LICENCIA`, `_COL_FECHA_EVENTOS`,
`_COL_VENCIMIENTO_CERTIFICADO` y `_SUBCONSULTA_ULTIMO_CERTIFICADO`.

### Módulo `reportes` — `src/certificado_operadores/modulos/reportes/ui.py`

Interfaz Streamlit de reportes y exportaciones (specs 010 y 023): selección del
reporte, **toolbar de filtros en una sola fila**, resultados con KPIs, gráfico de
barras nativo y descargas. Delega todo el acceso a datos en
`ReportesRepository`; no contiene sentencias SQL (RNF-01) ni conoce el esquema.
El paquete expone `render_reportes` en
`src/certificado_operadores/modulos/reportes/__init__.py`.

| Función | Firma | Descripción | Devuelve |
|---------|-------|-------------|----------|
| `parsear_entero` | `(texto: str) -> int \| None` | Convierte el campo de búsqueda en entero. | `int` o `None` |
| `pesos_toolbar` | `(numero_filtros: int) -> list[float]` | Spec 023: anchos del toolbar horizontal (`[2, 2, 1.5, 2, 1]` de referencia). | `list[float]` |
| `construir_agregacion` | `(df: pd.DataFrame, limite: int = LIMITE_GRAFICO) -> pd.DataFrame` | Spec 023: agrega el resultado para el gráfico de barras nativo. | `pd.DataFrame` |
| `_render_filtro` | `(filtro_tipo, filtro_etiqueta, defecto, repositorio, definicion) -> Any` | Spec 023: pinta un filtro y devuelve su valor tipado. | `Any` |
| `_construir_seleccion` | `(definicion: DefinicionReporte, repositorio: ReportesRepository) -> tuple[SeleccionFiltros, bool]` | Spec 023: barra horizontal de filtros y botón. | `tuple` |
| `_render_kpis` | `(df: pd.DataFrame) -> None` | Spec 023: tarjetas métricas ejecutivas (`st.metric`). | — |
| `_render_grafico` | `(df: pd.DataFrame) -> None` | Spec 023: gráfico de barras horizontal nativo (`st.bar_chart`). | — |
| `_render_resultado` | `(df: pd.DataFrame \| None, definicion, repositorio, usuario: str) -> None` | Muestra KPIs, tabla, gráfico, exportaciones y auditoría. | — |
| `render_reportes` | `(repositorio: ReportesRepository \| None = None) -> None` | Renderiza la vista completa (punto de entrada de `pages/`). | — |

Constantes: `TITULO`, `SUBTITULO`, `USUARIO_POR_DEFECTO`, `ETIQUETA_EJECUTAR`
(`Filtrar`), `OPCION_TODAS`, `OPCION_TODOS`, `MENSAJE_SIN_RESULTADOS`,
`PROPORCIONES_TOOLBAR`, `PESO_FILTRO`, `PESO_BOTON`, `LIMITE_GRAFICO`,
`COLUMNA_CATEGORIA`, `COLUMNA_VALOR`, `COLUMNAS_TOTAL` y los rótulos `KPI_*` y
`TITULO_GRAFICO`. Punto de entrada:
`src/certificado_operadores/pages/3_Reportes.py` (importa `render_reportes` y lo
invoca; la página queda 100% libre de `exec`, cerrando la Fase 3).

### Módulo `reportes` — pruebas

- **Ubicación:** `tests/test_reportes.py`
- **Cobertura:** repositorio contra SQLite temporal (catálogos de filtros,
  ejecución de reportes con filtro de empresa y actividad, y de la spec 022 la
  ejecución de **los ocho reportes** —incluidos licencias por vencer y
  certificados por vencer/vencidos con fechas relativas al día— verificando que
  ninguno arroje errores de sintaxis SQLite), funciones puras (condiciones por
  tipo de filtro, construcción de consulta, descripción de tipologías y
  generación de Excel/CSV), de la spec 023 la agregación para el gráfico
  (`construir_agregacion` con totales, ocurrencias, vacío y límite) y el reparto
  del toolbar (`pesos_toolbar`), auditoría de exportación y criterios estáticos
  (paquete CA-01, UI sin SQL RNF-01, toolbar/KPIs/gráfico CA-06, repositorio que
  encapsula la SQL CA-03 y sin sintaxis PostgreSQL CA-01, página sin `exec` con
  `render_reportes` CA-02/RNF-02). Patrón AAA.

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
