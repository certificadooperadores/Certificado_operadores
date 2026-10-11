# CONSTITUTION — Certificado_operadores

> **Verdad central del proyecto.** Este documento define el propósito, el stack, la
> estructura, las convenciones y el flujo de trabajo de `Certificado_operadores`. Si algo
> aquí contradice al código, el código manda **y este archivo se actualiza**.

> ⚠️ **Directiva de mantenimiento:** cada vez que se realicen cambios significativos
> (nuevas funcionalidades, cambios arquitectónicos, adición de módulos o ajustes de
> tecnologías), **se debe actualizar este archivo en el mismo commit** para mantener
> la verdad central del proyecto bien documentada.

---

## 0. Identidad del proyecto

| Campo            | Valor                          |
|------------------|--------------------------------|
| **Nombre**       | Certificado_operadores               |
| **Descripción**  | Aplicación para la gestión del certificado de ideoneida de los operadores del sistema masivo mio, desde su vinculación, formación, supensión, retiro. el objetivo es poder gestionar la información de una manera ordenada y versionada de facil acceso y manipulación                |
| **Repositorio**  | certificadooperadores                   |
| **Autoría**      | Ing. Miguel Angel Ortiz Roldan — certificado.operadores@gmail.com  |
| **Licencia**     | Privado                    |
| **Rama principal** | `main`                       |
| **Estado**       | En construcción 🚧             |

## 1. Propósito y no-propósito

### Propósito

Centralizar, versionar y custodiar la información de idoneidad, eventos normativos, control de novedades disciplinarias (accidentalidad, quejas e infracciones) y trazabilidad del ciclo de vida de los operadores del sistema integrado de transporte masivo MIO para Metrocali S.A. (Dirección de Operación - Evaluación de la Operación), sustituyendo hojas de cálculo aisladas por una plataforma con reglas de negocio auditables, evaluación automatizada de reincidencias y analítica interactiva confiable.

### No-propósito

- **No es un sistema de nómina ni gestión de recursos humanos:** no gestiona salarios, prestaciones ni contratos laborales individuales.
- **No es un sistema de despacho o telemetría en tiempo real:** no monitorea la ubicación GPS de los buses en vivo ni sustituye a los sistemas de ayuda a la explotación (SAE/TMS).
- **No es un sistema transaccional bancario ni de recaudo:** no gestiona ventas de pasajes ni tarifas del usuario final.
- **No almacena datos personales sensibles en repositorios públicos:** la base de datos física, respaldos y libros Excel institucionales con cédulas o datos de personas jamás se suben a Git ni se comparten fuera de la red autorizada.

## 2. Alcance

### Dentro del alcance

- **Administración del Ciclo de Vida del Operador:** Registro, actualización, asignación de rangos numéricos por concesionario (patrón COT: 10000 Git, 20000 ByN, 30000 ETM, 40000 Unimetro), control de tipologías y verificación de no duplicidad de cédula activa.
- **Gestión Normativa de Certificados de Idoneidad:** Control de vigencia de 3 años, cálculo automático de estados (Vigente, Próximo a Vencer a 90 días, Vencido, Cancelado) y registro de eventos oficiales (Certificación, Reactivación, Renovación, Suspensión, Retiro).
- **Novedades y Comportamientos Operacionales:** Ingreso individual y carga masiva de eventos de bitácora, consolidación de fuentes (accidentalidad, quejas, infracciones), evaluación matemática de reincidencias y trazabilidad de determinaciones institucionales.
- **Analítica Visual y Reportes:** Dashboard interactivo con Altair (cross-filtering coordinado tridireccional entre operadores, causales y rutas), cronograma de vencimientos por quincenas y exportación oficial a Excel/CSV.
- **Seguridad y Control de Acceso (RBAC):** Cuentas con roles jerárquicos (Super Administrador, Administrador, Gestor), contraseñas con hash irreversible `bcrypt`, tokens firmados (`HMAC-SHA256`) y auditoría transaccional estricta en `log_auditoria`.
- **Gobernanza de Datos:** Copias de seguridad versionadas (`.db`), protección contra sobrescritura (`.protegido.db`), comparación preventiva de registros y optimización SQLite en modo WAL con índices estratégicos.

### Fuera del alcance (por ahora)

- Integración directa por API con el RUNT o bases de datos externas del Ministerio de Transporte.
- Portal público de autogestión para consulta de certificados por parte de los conductores o ciudadanos.
- Notificaciones automáticas por correo electrónico o mensajería SMS a los concesionarios (se gestiona vía exportación de reportes).
- Motor de base de datos cliente-servidor distribuido (PostgreSQL en la nube): actualmente opera sobre SQLite optimizado con sincronización colaborativa vía OneDrive institucional.

## 3. Stack técnico

| Categoría         | Tecnología |
|-------------------|------------|
| **Lenguaje**      | Python 3.13+ |
| **Entorno/deps**  | [`uv`](https://docs.astral.sh/uv/) |
| **Testing**       | [`pytest`](https://docs.pytest.org/) |
| **Lint / formato**| [Ruff](https://docs.astral.sh/ruff/) |
| **Pre-commit**    | [pre-commit](https://pre-commit.com) |
| **CI/CD**         | [GitHub Actions](.github/workflows/ci.yml) |

> ⚠️ **Regla dura:** toda gestión de dependencias y entornos pasa por `uv`. Está
> **prohibido** `pip` y `requirements.txt`.

## 4. Estructura del repositorio

```text
certificado-operadores/
├── src/certificado_operadores/    # código del paquete (src-layout)
│   ├── domain/                    # capa de dominio (DTOs, constantes y lógica pura)
│   │   ├── models.py
│   │   └── usuarios.py            # DTO y reglas puras de usuarios
│   ├── infra/                     # capa de infraestructura (acceso a datos)
│   │   ├── repository.py
│   │   ├── usuarios_repository.py # repositorio de usuarios (dim_usuarios)
│   │   ├── eventos_repository.py  # repositorio de eventos (fact_eventos_operador)
│   │   ├── catalogos_repository.py # repositorio de los cinco catálogos (dim_*)
│   │   ├── certificados_repository.py # repositorio de eventos y certificados (fact_eventos_operador)
│   │   ├── comportamientos_repository.py # repositorio de comportamientos y reincidencia
│   │   ├── reportes_repository.py # repositorio de reportes y exportaciones
│   │   ├── backup_service.py      # copias de seguridad de SQLite (sistema de archivos)
│   │   └── seguridad.py           # hashing de contraseñas (bcrypt) y tokens de sesión (HMAC-SHA256)
│   ├── modulos/                   # un módulo de UI por carpeta (p. ej. admin_operadores/)
│   │   ├── admin_operadores/
│   │   │   └── ui.py              # interfaz de Streamlit; consume el Facade, sin SQL
│   │   ├── administrar_backups/
│   │   │   └── ui.py              # interfaz de Streamlit; consume BackupService
│   │   ├── catalogos/
│   │   │   └── ui.py              # interfaz de Streamlit; consume ConfiguracionFacade, sin SQL
│   │   ├── correccion_registros/
│   │   │   └── ui.py              # interfaz de Streamlit; consume ConfiguracionFacade, sin SQL
│   │   ├── gestion_certificados/
│   │   │   └── ui.py              # interfaz de Streamlit; consume CertificadosFacade, sin SQL
│   │   ├── reporte_comportamientos/
│   │   │   └── ui.py              # interfaz de Streamlit; consume ComportamientosFacade, sin SQL
│   │   ├── reportes/
│   │   │   └── ui.py              # interfaz de Streamlit; consume ReportesFacade, sin SQL
│   │   └── gestion_usuarios/
│   │       └── ui.py              # interfaz de Streamlit; consume el Facade, sin SQL
│   ├── pages/                     # puntos de entrada de Streamlit (páginas delgadas)
│   ├── facade.py                  # Fachada de operadores (UI → Facade → Dominio → Infraestructura)
│   ├── facade_usuarios.py         # Fachada de usuarios (UI → Facade → Dominio → Infraestructura)
│   ├── facade_certificados.py     # Fachada de certificados y alertas (spec 025)
│   ├── facade_comportamientos.py  # Fachada de comportamientos y reincidencias (spec 025)
│   ├── facade_reportes.py         # Fachada de reportes y exportaciones (spec 025)
│   ├── facade_configuracion.py    # Fachada de catálogos y corrección de registros (spec 025)
│   ├── db.py                      # Motor SQLite, pragmas (WAL/busy_timeout) e índices (spec 025)
│   ├── estilos.py                 # Estilos visuales institucionales Metrocali y logo (spec 023)
│   └── ui_sesion.py               # Sesión persistente y refresco de datos (Streamlit; consume el Facade)
├── tests/                   # pruebas (pytest)
├── docs/                    # documentación detallada (requerimientos, desacople, manual, funciones)
├── scripts/                 # código permanente y reutilizable
├── assets/                  # recursos (imágenes, datos de ejemplo)
├── temp_agent/              # código temporal del agente (ignorado en Git)
├── .github/                 # gobernanza (plantillas PR/issue, CI, Dependabot, labels)
├── AGENTS.md                # contexto para agentes LLM
├── CONSTITUTION.md          # este archivo — verdad central
├── README.md                # puerta de entrada pública
├── CONTRIBUTING.md          # guía de contribución
├── CODE_OF_CONDUCT.md       # código de conducta
├── Makefile                 # automatización de tareas
├── pyproject.toml           # metadatos y dependencias (uv)
├── uv.lock                  # lockfile determinista (versionado)
├── .python-version          # versión de Python fijada
└── .pre-commit-config.yaml  # hooks de calidad
```

## 5. Convenciones de código

- **Responsabilidad única:** cada archivo/módulo y cada función hacen una sola cosa.
- **Súper-comentado:** todo módulo, clase y función pública lleva docstring **en
  español** (PEP 257) y comentarios donde el *porqué* no sea obvio.
- **Estilo:** [PEP 8](https://peps.python.org/pep-0008/) y
  [PEP 257](https://peps.python.org/pep-0257/), impuesto por **Ruff**
  (`line-length = 100`, comillas dobles).
- **Tipado:** anotaciones en funciones y firmas públicas.
- **Nomenclatura:** `snake_case` (funciones/variables), `PascalCase` (clases),
  `UPPER_CASE` (constantes).
- **Pruebas:** `pytest` con el patrón **AAA** (*Arrange · Act · Assert*).
- **Idioma:** documentación, comentarios, docstrings y commits en español;
  identificadores de código en inglés.
- **Prohibido hardcodear ("quemar código"):** sin valores, rutas, credenciales,
  URLs, puertos ni parámetros incrustados; todo sale de configuración, constantes
  con nombre, variables de entorno o se inyecta.
- **La UI no ejecuta tareas (patrón Facade):** la interfaz (incluida Streamlit)
  solo captura entrada, llama al Facade y muestra el resultado; cero lógica de
  negocio y cero acceso directo a BD/APIs desde la UI.
  `UI → Facade → Dominio → Infraestructura`.
- **Inyección de dependencias:** las dependencias se inyectan, no se instancian en
  la lógica.
- **Orden de carpetas:** estructura predecible, una carpeta = una responsabilidad;
  nada suelto en la raíz.
- **Código temporal del agente:** los `fix`, `repair`, parches, workarounds,
  migraciones puntuales y diagnósticos que no forman parte del proyecto van en
  `temp_agent/` (ignorado en Git); nunca en la raíz, `src/`, `tests/`, `docs/` ni
  `scripts/`.
- **Reglas propias:**
  - <!-- Invariantes del dominio (p. ej. "montos como enteros"). -->

## 5bis. Seguridad, respaldos y autorización (obligatorio)

- **Repositorio obligatorio:** un proyecto nuevo no arranca sin repositorio Git;
  pide primero al usuario la URL del repositorio y la rama principal.
- **No borrar sin autorización expresa:** archivos, carpetas y bases de datos se
  borran solo con el consentimiento explícito del usuario (lista qué se borrará y
  pregunta antes). Nada de `rm -rf`, `DROP`, `TRUNCATE`, `git push --force`,
  `reset --hard` ni borrado de ramas sin permiso.
- **Modificar solo con respaldo previo:** commitea/stashea/rama el trabajo anterior
  y asegura el respaldo antes de editar. Los cambios grandes van en una rama, nunca
  sobre `main`.
- **Responsabilidad única + súper-comentado:** cada archivo y función hacen una
  sola cosa y están exhaustivamente documentados (docstring en español).

## 5ter. Documentación

La documentación detallada vive en `docs/` (en español), enlazada desde el
`README.md`:

| Documento | Contenido |
|-----------|-----------|
| `docs/README.md` | Índice de la documentación. |
| `docs/requerimientos.md` | Requisitos de software y hardware mínimo. |
| `docs/desacople.md` | Arquitectura, capas y desacoplamiento. |
| `docs/manual-usuario.md` | Guía de uso: qué hace cada botón/elemento. |
| `docs/referencia-funciones.md` | Todas las funciones, su ubicación y descripción. |

- **Docstrings en español** (PEP 257); identificadores en inglés.
- Todo documento de `docs/` y este `README.md` terminan con:
  **Autor:** Ing. Miguel Angel Ortiz Roldan

## 6. Calidad y automatización

| Herramienta   | Rol                       | Comando |
|---------------|---------------------------|---------|
| `uv`          | Entornos y dependencias   | `uv sync` |
| Ruff          | Lint + formato            | `make lint` / `make format` |
| pytest        | Pruebas                   | `make test` |
| pre-commit    | Hooks antes de cada commit| `make pre-commit` |
| GitHub Actions| CI (pre-commit + pruebas) | `.github/workflows/ci.yml` |

- Ningún commit se salta los hooks (`--no-verify` prohibido salvo causa justificada y documentada).
- La **CI debe estar en verde** antes de fusionar un Pull Request.
- Toda dependencia nueva entra con `uv add` / `uv add --dev`.
- **Pruebas tras cada función:** al terminar o aprobar cualquier función o
  desarrollo, se ejecutan las pruebas necesarias. Una tarea no termina hasta que
  las pruebas pasan (verde).
- **Cero advertencias en pruebas (spec 021):** la suite se ejecuta con el
  criterio duro `-W error` configurado en `[tool.pytest.ini_options]` de
  `pyproject.toml`; cualquier advertencia nueva falla la ejecución. Está
  **prohibido silenciarlas** (`filterwarnings = ["ignore"]`,
  `@pytest.mark.filterwarnings` o equivalentes). Las conexiones SQLite se cierran
  en su origen: las fixtures de motor usan `poolclass=NullPool` y ejecutan
  `motor.dispose()` en el teardown (`yield`), y los motores creados de forma
  inline se liberan con `motor.dispose()`.
- **Preguntar antes de empezar y avanzar por partes:** reúne primero toda la
  información y permisos, luego avanza una función por ciclo:
  **implementar → probar → corregir → documentar → commit**.

## 7. Repositorio y Git

- **Remoto (SSH):** `certificadooperadores.git`
- **Rama principal:** `main`
- **Estrategia de ramas:** `feat/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`, `chore/...`; integración vía Pull Request.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `test:`, `chore:`.

## 8. Flujo diario (commit + push)

```bash
# 1. Ver cambios
git status

# 2. Verificación completa (lint + formato + pruebas)
make check

# 3. Agregar y commitear (los hooks se ejecutan solos)
git add -A
git commit -m "tipo: mensaje descriptivo"

# 4. Subir
git push
```

## 9. Historial de decisiones técnicas

| Fecha    | Decisión | Motivo |
|----------|----------|--------|
| 2026-10-09 | Adoptar `CONSTITUTION.md` como fuente única de verdad | Claridad legal y operativa |
| 2026-10-09 | Crear `OperadoresFacade` en `src/certificado_operadores/facade.py` | Cumplir la regla Facade: la UI no accede directamente a la base de datos |
| 2026-10-09 | Modularizar `facade.py` en `domain/models.py` e `infra/repository.py` | Separar responsabilidades (Clean Architecture): el Facade solo orquesta; el dominio define DTOs, constantes y lógica pura; la infraestructura encapsula el SQL |
| 2026-10-09 | Mover la UI de administración de operadores a `modulos/admin_operadores/ui.py` consumiendo `OperadoresFacade` | Cumplir la spec 003: la UI no ejecuta SQL ni conoce el esquema; se elimina el heredado `modulos/5_Administracion_Operadores.py` |
| 2026-10-09 | Extraer la UI de gestión de usuarios a `modulos/gestion_usuarios/ui.py` con `UsuariosFacade` y eliminar el `exec` de la pestaña en `pages/1_Configuracion.py` | Cumplir la spec 004: cero SQL en la UI (Facade) y hashing aislado en `infra/seguridad.py` (bcrypt) |
| 2026-10-09 | Extraer la UI de backups a `modulos/administrar_backups/ui.py` con `BackupService` (API de respaldo de SQLite, directorio configurable) y eliminar el `exec` de la pestaña en `pages/1_Configuracion.py` | Cumplir la spec 005: cero operaciones de SO/SQL en la UI y fin de la ruta dura `/Backups` y del `pg_dump` de PostgreSQL |
| 2026-10-09 | Extraer la corrección de registros a `modulos/correccion_registros/ui.py` con `EventosRepository` (filtros, lotes y mutaciones con auditoría) y deprecar `modulos/3_Modificacion_Tablas.py` | Cumplir la spec 006: cero SQL en la página y en la vista; todo el acceso a `fact_eventos_operador` pasa por el repositorio |
| 2026-10-09 | Extraer los catálogos a `modulos/catalogos/ui.py` con `CatalogosRepository` y eliminar el último `exec` de `pages/1_Configuracion.py` | Cumplir la spec 007: la UI no ejecuta SQL (Facade/Repositorio) y la página de configuración queda 100% desacoplada |
| 2026-10-09 | Extraer la gestión de certificados a `modulos/gestion_certificados/ui.py` con `CertificadosRepository`, deprecar `modulos/6_Gestion_Certificados.py` y eliminar el `exec` de la pestaña 2 de `pages/2_Administracion_Operadores.py` | Cumplir la spec 008: cero SQL en la vista, registro individual y masivo desacoplados y encapsulados en el repositorio |
| 2026-10-09 | Extraer el reporte de comportamientos a `modulos/reporte_comportamientos/ui.py` con `ComportamientosRepository` y eliminar el último `exec` de `pages/2_Administracion_Operadores.py` | Cumplir la spec 009: cero SQL en la vista (registro individual, carga masiva y reincidencia) y cierre de la Fase 2, con la página 100% libre de `exec` |
| 2026-10-09 | Extraer reportes y exportaciones a `modulos/reportes/ui.py` con `ReportesRepository` y eliminar el último `exec` de `pages/3_Reportes.py` | Cumplir la spec 010: cero SQL en la vista, consultas y exportaciones encapsuladas en la infraestructura y cierre de la Fase 3 (todas las páginas maestras desacopladas) |
| 2026-10-09 | Extraer el login de `Inicio.py` a `UsuariosFacade.autenticar()` con el DTO `ResultadoAutenticacion`, las credenciales `CredencialesUsuario` y `UsuariosRepository.obtener_para_autenticacion()` | Cumplir la spec 011: el punto de entrada queda 100% libre de SQL y de dependencias criptográficas directas (`UI → Facade → Dominio → Infraestructura`) |
| 2026-10-10 | Añadir `UsuariosRepository.asegurar_tablas()` (DDL idempotente de `dim_usuarios` y `log_auditoria` + siembra del `admin` por defecto) invocado en el constructor, y corregir la ruta de CSVs en `scripts/cargar_excel_a_sqlite.py` a `data/Modelo_Estrella_Final_CSVs` | Cumplir la spec 012: la app arranca y autentica al `admin` sobre una base SQLite nueva sin `OperationalError`; la auto-inicialización queda confinada a la infraestructura (RNF-01) |
| 2026-10-10 | Firmar tokens de sesión con HMAC-SHA256 en `infra/seguridad.py` (`generar_token_sesion`/`validar_token_sesion`, caducidad de 1200 s), orquestarlos en `UsuariosFacade` y persistir la sesión vía `st.query_params["session"]` con el módulo de UI `ui_sesion.py` (restaurar/renovar, Refrescar Datos y Cerrar Sesión) | Cumplir la spec 013: sobrevivir a `F5` dentro de los 20 minutos, expirar por inactividad, permitir refrescar datos sin cerrar sesión y mantener la UI sin SQL ni criptografía (UI → Facade → Dominio → Infraestructura) |
| 2026-10-10 | Añadir a `BackupService` la comparación preventiva (`comparar_backup` sobre `TABLAS_COMPARACION`) y la restauración atómica (`restaurar_backup` con respaldo de rescate `pre_restauracion_*` y registro en `dim_version_bd`), e integrarlas en `modulos/administrar_backups/ui.py` | Cumplir la spec 014: advertir al usuario cuántos registros se pierden/recuperan antes de restaurar, proteger los datos actuales con una copia automática y reflejar la versión restaurada en el indicador lateral, sin SO ni SQL en la UI |
| 2026-10-10 | Rediseñar `modulos/correccion_registros/ui.py` con sub-pestañas por tabla (Eventos, Licencias, Comportamientos, Operadores) y acciones compactas sobre filas seleccionadas, y añadir a `EventosRepository` el catálogo `TABLAS_CORRECCION` con `listar_registros`, `mutar_vigencia` y `eliminar_registros_tabla` | Cumplir la spec 015: eliminar la división Individual/Lote y los filtros externos voluminosos, aprovechar la búsqueda y selección múltiple nativas de `st.dataframe` y permitir cambio de estado/eliminación por lote de IDs con auditoría, sin SQL en la UI |
| 2026-10-10 | Rediseñar `modulos/correccion_registros/ui.py` como **editor tipo Excel** (`st.data_editor` + `column_config.SelectboxColumn` y columnas protegidas con botón "💾 Guardar Cambios") y añadir a `EventosRepository` las columnas editables del catálogo, `contar_dependencias_operador`, `validar_codigo_existe` y `actualizar_registros_seguros`, con las excepciones `DependenciaRegistroError`, `CodigoInexistenteError`, `ColumnaProtegidaError` y `ValorInvalidoError` | Cumplir la spec 017: listas desplegables restringidas a los catálogos (S-04), llaves primarias y fechas de auditoría de solo lectura (S-03), bloqueo de borrado de operadores con hijos dependientes (S-01), validación de códigos reasignados (S-02) y transacciones atómicas con `log_auditoria` (S-05), sin SQL en la UI |
| 2026-10-10 | Perfeccionar `modulos/correccion_registros/ui.py` con barra de **búsqueda rápida** (`st.text_input` por sub-pestaña), casilla `Seleccionar` y **botones de acción en bloque** (`Marcar Vigente`/`Marcar Anulado`/`Eliminar`), listas oficiales de licencias y comportamientos mediante `columna_config.SelectboxColumn`, y añadir a `EventosRepository` el catálogo `codigos` (`dim_codigo`), `OPCIONES_LICENCIA`, los tipos de edición `licencia`/`fuente`/`descripcion`, `listar_fuentes_comportamiento` y `listar_descripciones_comportamiento` | Cumplir la spec 018: filtrar en memoria antes del editor (CA-01), restringir `Tipo` a `C1`/`C2`/`C3` (CA-02) y `Fuente`/`Descripción` al catálogo oficial (CA-03), exponer la sub-pestaña Códigos con operador, empresa y fecha de registro (CA-04) y permitir mutar en bloque las filas seleccionadas conviviendo con Guardar Cambios (CA-05), sin SQL en la UI |
| 2026-10-10 | Ampliar la definición de la tabla `eventos` de `TABLAS_CORRECCION` en `infra/eventos_repository.py` con las columnas completas de negocio (cinco fechas, evaluador, vehículo evaluado y observación) y sus tipos de edición `fecha`/`texto`/`entero`, protegiendo `Cédula`, `Nombre` y `Registro` | Cumplir la spec 019: exponer y editar en el editor tipo Excel la información oficial de Metrocali (CA-01), persistir los cambios en `fact_eventos_operador` (CA-02), cubrir presencia y edición con pruebas en `tests/test_correccion_registros.py` (CA-03) y mantener `uv run pytest` 100% en verde (CA-04), sin SQL en la UI |
| 2026-10-10 | Añadir a `infra/eventos_repository.py` la matriz `CAMPOS_PERMITIDOS_POR_EVENTO`, la excepción `CampoIncompatibleError`, el rechazo atómico de campos incompatibles por categoría (S-02), la limpieza a `NULL` de campos huérfanos al mutar el tipo de evento (S-03) y la validación de plausibilidad de fechas (S-04); adaptar `modulos/correccion_registros/ui.py` con un selector de tipo de evento que proyecta columnas y filas (S-05) | Cumplir la spec 020: blindar `fact_eventos_operador` contra fechas incongruentes con la naturaleza del evento, evitar datos residuales al cambiar de categoría y reducir el ruido visual del editor, sin SQL en la UI |
| 2026-10-10 | Estandarizar las fixtures de motor de `tests/` con `poolclass=NullPool` + `motor.dispose()` en el teardown (`Iterator[Engine]`), liberar con `dispose()` los motores creados inline y fijar `addopts = "-q -W error"` en `pyproject.toml` | Cumplir la spec 021: eliminar en su causa raíz los 161 `ResourceWarning` de SQLite bajo Python 3.13 (cierre limpio de conexiones), prohibir silenciar advertencias y dejar `uv run pytest` y `make check` en verde con 0 advertencias |
| 2026-10-10 | Migrar en `infra/reportes_repository.py` toda la sintaxis de fecha a SQLite: `DATE(columna)` y `DATE(fecha, '+3 years')`, diferencias de días con `JULIANDAY` y `CAST(ROUND(...) AS INTEGER)`, filtro de vencimiento `DATE('now', '+' || :dias || ' days')` y último certificado por código con `ROW_NUMBER() OVER (PARTITION BY id_codigo ORDER BY fecha_certificado DESC)` filtrando `rn = 1`; ampliar `tests/test_reportes.py` para ejecutar los ocho reportes sobre SQLite | Cumplir la spec 022: erradicar el `OperationalError: unrecognized token ":"` de PostgreSQL que rompía la página de Reportes y Exportaciones y garantizar la portabilidad de todas las consultas |
| 2026-10-10 | Declarar el bloque `[theme]` institucional (`#046BD2`, `#FFFFFF`, `#F8FAFC`, `#111827`) en `.streamlit/config.toml`; crear `estilos.py` con `inyectar_estilos_metrocali()` (CSS, bordes y pestañas en azul) y el logo `assets/logo_metrocali.png` vía `st.logo`; añadir a `OperadoresRepository` los catálogos `listar_empresas`/`listar_tipologias` y `crear_operador`/`existe_operador_vigente`, el caso de uso `OperadoresFacade.guardar_operador` (valida duplicados y campos obligatorios) y los DTO `RegistroOperador`/`ResultadoOperador`; rediseñar `modulos/admin_operadores/ui.py` con el formulario horizontal y el botón `Guardar Operador`, y `modulos/reportes/ui.py` con toolbar en una sola fila, KPIs (`st.metric`) y gráfico nativo (`st.bar_chart`); retirar los emojis de todos los `st.title` y `st.tabs` | Cumplir la spec 023: estandarizar la identidad visual institucional de Metrocali MIO, ordenar el formulario de operadores con guardado real en base de datos y compactar los reportes, con pruebas verdes y sin advertencias |
| 2026-10-10 | Refinar la UX de reportes en `modulos/reportes/ui.py`: ancho fluido en `estilos.py` (`max-width: none`), supresión total de `st.bar_chart` por código individual, KPIs de negocio por tipo de reporte (prohibido sumar IDs o contar columnas), botones de exportación en la cabecera y diagrama de Gantt de vencimientos por concesionario con `matplotlib`; en `reportes_repository.py` resolver la `Empresa` de reincidencias por prefijo COT con `COALESCE`, añadir filtro de fechas a reincidencias y filtro de concesionario a licencias/certificados por vencer, y proyectar el nombre legible de tipología (`_COLUMNA_TIPOLOGIA`); en `repository.py` calcular el siguiente código por rango de concesionario (`siguiente_codigo` con base `id_empresa * 10000`) | Cumplir la spec 024: eliminar el layout estrangulado, los gráficos inútiles y las métricas absurdas, y aplicar el patrón de códigos por COT, con pruebas verdes y sin advertencias |
| 2026-10-10 | Configurar pragmas de alto rendimiento (`journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`) y crear los índices estratégicos en `db.py` y `scripts/cargar_excel_a_sqlite.py`; introducir `CertificadosFacade`, `ComportamientosFacade`, `ReportesFacade` y `ConfiguracionFacade` y adaptar los `ui.py` para no importar `*Repository`; desacoplar `utils.py` mediante `BackupService.version_actual`/`estado_version`; mover `init_db.py` a `temp_agent/` y eliminar `INSTRUCCIONES_OPENCODE.md`; declarar `altair` y crear `LICENSE` y `CODE_OF_CONDUCT.md` | Cumplir la spec 025: optimizar el motor SQLite, completar el patrón Facade 100%, erradicar residuos legacy y robustecer la gobernanza, con la suite (373 funciones de prueba; 402 casos) en verde y sin advertencias |

## 10. Notas y tareas pendientes

- [ ] Completar las secciones marcadas de este documento.
- [ ] Configurar el remoto y proteger `main`.
- [ ] Definir la primera funcionalidad y sus pruebas.
- [ ] <!-- Agregar el roadmap del proyecto. -->

## 11. Configuración local (no trackear)

> Configuración específica de la máquina local. **NO incluir en commits.**

<!-- p. ej. identidad Git vía includeIf, remotos, credenciales.
     Ver references/agent-context.md. -->
