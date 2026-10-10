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
