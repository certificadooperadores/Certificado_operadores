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

<!-- Una o dos frases: qué problema resuelve el proyecto y para quién. -->

### No-propósito

<!-- Qué NO es este proyecto. Evita expectativas equivocadas y desvíos de alcance. -->

## 2. Alcance

### Dentro del alcance

- ...

### Fuera del alcance (por ahora)

- ...

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
│   │   │   └── ui.py              # interfaz de Streamlit; consume CatalogosRepository, sin SQL
│   │   ├── correccion_registros/
│   │   │   └── ui.py              # interfaz de Streamlit; consume EventosRepository, sin SQL
│   │   ├── gestion_certificados/
│   │   │   └── ui.py              # interfaz de Streamlit; consume CertificadosRepository, sin SQL
│   │   ├── reporte_comportamientos/
│   │   │   └── ui.py              # interfaz de Streamlit; consume ComportamientosRepository, sin SQL
│   │   ├── reportes/
│   │   │   └── ui.py              # interfaz de Streamlit; consume ReportesRepository, sin SQL
│   │   └── gestion_usuarios/
│   │       └── ui.py              # interfaz de Streamlit; consume el Facade, sin SQL
│   ├── pages/                     # puntos de entrada de Streamlit (páginas delgadas)
│   ├── facade.py                  # Fachada de operadores (UI → Facade → Dominio → Infraestructura)
│   ├── facade_usuarios.py         # Fachada de usuarios (UI → Facade → Dominio → Infraestructura)
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

## 10. Notas y tareas pendientes

- [ ] Completar las secciones marcadas de este documento.
- [ ] Configurar el remoto y proteger `main`.
- [ ] Definir la primera funcionalidad y sus pruebas.
- [ ] <!-- Agregar el roadmap del proyecto. -->

## 11. Configuración local (no trackear)

> Configuración específica de la máquina local. **NO incluir en commits.**

<!-- p. ej. identidad Git vía includeIf, remotos, credenciales.
     Ver references/agent-context.md. -->
