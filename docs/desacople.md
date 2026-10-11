# Arquitectura y desacoplamiento — Certificado_operadores

Describe cómo está organizado el sistema y cómo se mantienen separadas sus
partes, para poder cambiarlas sin romper el resto.

## 1. Visión general

```text
[ Entrada / UI ] → [ Fachadas / Casos de uso ] → [ Dominio ] → [ Infraestructura ]
```

## 2. Capas y responsabilidades

| Capa / módulo | Responsabilidad única | Puede depender de |
|---------------|-----------------------|-------------------|
| Presentación / UI (`modulos/*/ui.py`, `pages/`, `Inicio.py`) | Mostrar y capturar datos. | Fachadas |
| Casos de uso / aplicación (`facade*.py`) | Orquestar flujos. | Dominio e Infraestructura |
| Dominio (`domain/`) | Reglas de negocio. | Nada externo |
| Infraestructura (`infra/`) | Persistencia, APIs, IO. | Dominio (implementa sus puertos) |

## 3. Dirección de dependencias (reglas duras)

- El **dominio no depende** de frameworks, base de datos ni UI.
- La **UI no accede** directamente a la base de datos ni importa repositorios.
- Las dependencias se **inyectan**, no se instancian dentro de la lógica.
- Los contratos entre capas son **interfaces / DTOs**, no tipos concretos de una
  tecnología.
- **Prohibido hardcodear ("quemar código"):** sin valores, rutas, credenciales,
  URLs, puertos ni parámetros incrustados. Todo sale de configuración, constantes
  con nombre, variables de entorno o se inyecta.

## 3bis. La UI no ejecuta tareas — patrón Facade

- La interfaz (incluida **Streamlit**) **no** contiene lógica de negocio ni ejecuta
  tareas; solo captura entrada, llama a la **fachada** y muestra el resultado.
- Cada **fachada** expone los casos de uso de su dominio y orquesta dominio +
  infraestructura; es la **única** puerta que la UI conoce.

```text
UI / Streamlit  →  Fachada (casos de uso)  →  Dominio  →  Infraestructura
```

### Mapa de fachadas especializadas (spec 025)

| Fachada | Archivo | Encapsula | Casos de uso que expone |
|---------|---------|-----------|-------------------------|
| `OperadoresFacade` | `facade.py` | `OperadoresRepository` | Consulta de operadores, guardado, validación de certificado y estadísticas. |
| `UsuariosFacade` | `facade_usuarios.py` | `UsuariosRepository` | Autenticación, RBAC, alta/modificación de usuarios y tokens de sesión. |
| `CertificadosFacade` | `facade_certificados.py` | `CertificadosRepository` + `OperadoresRepository` | Catálogos de eventos, operador activo, registro individual/masivo y alertas del certificado. |
| `ComportamientosFacade` | `facade_comportamientos.py` | `ComportamientosRepository` | Registro individual/masivo, evaluación de reincidencia y acciones de Metrocali. |
| `ReportesFacade` | `facade_reportes.py` | `ReportesRepository` | Métricas analíticas, filtros tridireccionales, vencimientos y exportaciones. |
| `ConfiguracionFacade` | `facade_configuracion.py` | `CatalogosRepository` + `EventosRepository` | Catálogos maestros y corrección segura de registros. |
| `BackupService` | `infra/backup_service.py` | Sistema de archivos / SQLite | Copias, protección, comparación, restauración y **estado de versión** de la base. |

> Regla verificable: **ningún** `modulos/*/ui.py` importa una clase `*Repository`.

## 4. Contratos entre módulos

| Contrato | Define | Implementa |
|----------|--------|------------|
| DTOs y modelos | `domain/models.py`, `domain/usuarios.py` | N/A (dataclasses inmutables) |
| Repositorios | Infraestructura (`infra/`) | `OperadoresRepository`, `UsuariosRepository`, `CertificadosRepository`, `ComportamientosRepository`, `ReportesRepository`, `CatalogosRepository`, `EventosRepository` (SQLAlchemy) |
| Casos de uso | `facade*.py` | `OperadoresFacade`, `UsuariosFacade`, `CertificadosFacade`, `ComportamientosFacade`, `ReportesFacade`, `ConfiguracionFacade` |
| Servicio de respaldos | `infra/backup_service.py` | `BackupService` |

## 5. Puntos de acoplamiento y su mitigación

| Acoplamiento | Riesgo | Mitigación |
|--------------|--------|------------|
| UI → Base de datos | Consultas SQL rotas por cambios de UI | **Mitigado:** la UI solo invoca las fachadas especializadas (specs 003–010 y 025). |
| UI → Repositorios | Conocer clases concretas de infraestructura | **Mitigado:** `CertificadosFacade`, `ComportamientosFacade`, `ReportesFacade` y `ConfiguracionFacade` encapsulan los repositorios; cero importaciones de `*Repository` en `modulos/*/ui.py`. |
| UI (backups) → Sistema de archivos/BD | Operaciones de SO y SQL dispersas | **Mitigado:** `modulos/administrar_backups/ui.py` y `utils.py` solo invocan `BackupService` (spec 005 y 025). |
| UI (sesión) → Criptografía | Tokens y hashing en la vista | **Mitigado:** `ui_sesion.py` delega en `UsuariosFacade`; el hashing/token viven en `infra/seguridad.py`. |
| Fachada → Infra | Fachada atada a SQLAlchemy | **Mitigado:** cada fachada delega todo acceso a datos en su repositorio. |
| Motor SQLite | Bloqueos y consultas lentas | **Mitigado (spec 025):** pragmas `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL` e índices estratégicos explícitos. |
| Tipado dinámico | Errores de acceso a diccionarios en UI | **Mitigado:** uso estricto de dataclasses en el dominio y en cada repositorio. |

## 6. Decisiones de arquitectura

1. **Clean Architecture ligera:** separación en dominio, infraestructura, fachadas
   y presentación.
2. **Inyección de dependencias:** el motor se inyecta (o se resuelve perezosamente)
   para facilitar las pruebas unitarias con SQLite temporal.
3. **Patrón Facade:** las vistas de Streamlit ignoran la existencia de tablas,
   columnas y consultas; todo pasa por la fachada de su dominio.
4. **Fachadas especializadas (spec 025):** se introdujeron
   `CertificadosFacade`, `ComportamientosFacade`, `ReportesFacade` y
   `ConfiguracionFacade` y se adaptaron sus `ui.py` para no importar repositorios.
5. **Servicio de respaldos (spec 005):** `BackupService` encapsula el sistema de
   archivos, la comparación, la restauración y el estado de versión de la base.
6. **Optimización del motor (spec 025):** pragmas de SQLite e índices explícitos
   declarados en `db.py` y aplicados por los scripts de carga.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
