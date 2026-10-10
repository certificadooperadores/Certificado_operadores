# Arquitectura y desacoplamiento — Certificado_operadores

Describe cómo está organizado el sistema y cómo se mantienen separadas sus
partes, para poder cambiarlas sin romper el resto.

## 1. Visión general

<!-- Diagrama de contexto. Puede ser ASCII, Mermaid o un enlace a un diagrama
     generado con la skill `archify` (HTML interactivo). -->

```text
[ Entrada / UI ] → [ Casos de uso ] → [ Dominio ] → [ Infraestructura ]
```

## 2. Capas y responsabilidades

| Capa / módulo | Responsabilidad única | Puede depender de |
|---------------|-----------------------|-------------------|
| Presentación / UI | Mostrar y capturar datos. | Casos de uso |
| Casos de uso / aplicación | Orquestar flujos. | Dominio |
| Dominio | Reglas de negocio. | Nada externo |
| Infraestructura | Persistencia, APIs, IO. | Dominio (implementa sus puertos) |

## 3. Dirección de dependencias (reglas duras)

- El **dominio no depende** de frameworks, base de datos ni UI.
- La **UI no accede** directamente a la base de datos.
- Las dependencias se **inyectan**, no se instancian dentro de la lógica.
- Los contratos entre capas son **interfaces / DTOs**, no tipos concretos de una
  tecnología.
- **Prohibido hardcodear ("quemar código"):** sin valores, rutas, credenciales,
  URLs, puertos ni parámetros incrustados. Todo sale de configuración, constantes
  con nombre, variables de entorno o se inyecta.

## 3bis. La UI no ejecuta tareas — patrón Facade

- La interfaz (incluida **Streamlit**) **no** contiene lógica de negocio ni ejecuta
  tareas; solo captura entrada, llama a la **fachada** y muestra el resultado.
- El **Facade** expone los casos de uso y orquesta dominio + infraestructura.

```text
UI / Streamlit  →  Facade (casos de uso)  →  Dominio  →  Infraestructura
```

## 4. Contratos entre módulos

| Contrato | Define | Implementa |
|----------|--------|------------|
| DTOs y Modelos | `domain/models.py`, `domain/usuarios.py` | N/A (Dataclasses inmutables) |
| Repositorio Base | `domain/` (Implícitamente) | `infra/repository.py`, `infra/usuarios_repository.py` (SQLAlchemy) |
| Casos de Uso | `facade.py`, `facade_usuarios.py` | `OperadoresFacade`, `UsuariosFacade` |

## 5. Puntos de acoplamiento y su mitigación

| Acoplamiento | Riesgo | Mitigación |
|--------------|--------|------------|
| UI -> Base de Datos | Consultas SQL rotas por cambios en UI | **Mitigado**: La UI (Streamlit) solo invoca métodos de `OperadoresFacade`. |
| UI (usuarios) -> Base de Datos | Consultas SQL rotas por cambios en UI | **Mitigado**: `modulos/gestion_usuarios/ui.py` solo invoca `UsuariosFacade` (spec 004). |
| UI (backups) -> Sistema de archivos/BD | Operaciones de SO y SQL dispersas en la vista | **Mitigado**: `modulos/administrar_backups/ui.py` solo invoca `BackupService`; el manejo de archivos y la copia SQLite viven en `infra/backup_service.py` (spec 005). |
| UI (corrección) -> Base de Datos | Consultas SQL y mutaciones crudas inlined en la vista | **Mitigado**: `modulos/correccion_registros/ui.py` solo invoca `EventosRepository`; la lógica inlined y duplicada de `3_Modificacion_Tablas.py` fue erradicada (spec 006). |
| UI (catálogos) -> Base de Datos | Más de 20 consultas SQL crudas mezcladas con la vista de catálogos | **Mitigado**: `modulos/catalogos/ui.py` solo invoca `CatalogosRepository`; se eliminó el último `exec` de `pages/1_Configuracion.py` (spec 007). |
| UI (certificados) -> Base de Datos | Más de 15 consultas SQL y transacciones crudas en la vista de eventos | **Mitigado**: `modulos/gestion_certificados/ui.py` solo invoca `CertificadosRepository`; se eliminó el `exec` de la pestaña 2 de `pages/2_Administracion_Operadores.py` y el módulo heredado `6_Gestion_Certificados.py` quedó deprecado (spec 008). |
| Facade -> Infra | Facade atado a SQLAlchemy | **Mitigado**: Facade delega todo acceso a datos a `OperadoresRepository`. |
| Tipado Dinámico | Errores de acceso a diccionarios en UI | **Mitigado**: Uso estricto de `dataclasses` (`OperadorInfo`) en la capa de Dominio. |

## 6. Decisiones de arquitectura

1. **Clean Architecture Ligera:** Se separó la lógica en capas de Dominio (`domain/models.py`), Infraestructura (`infra/repository.py`) y Aplicación (`facade.py`).
2. **Inyección de Dependencias:** El motor de base de datos se inyecta desde arriba (o perezosamente) para facilitar las pruebas unitarias con SQLite en memoria.
3. **Patrón Facade:** Las vistas de Streamlit (`views/`) ignoran completamente la existencia de tablas, columnas o consultas SQL; todo pasa por `OperadoresFacade`.
4. **Facade de usuarios (spec 004):** La gestión de usuarios se extrajo a `modulos/gestion_usuarios/ui.py` y consume `UsuariosFacade`; la página `pages/1_Configuracion.py` dejó de usar `exec` en esa pestaña. El hashing de contraseñas se aísla en `infra/seguridad.py` (bcrypt).
5. **Servicio de backups (spec 005):** La administración de respaldos se extrajo a `modulos/administrar_backups/ui.py`, que consume `infra/backup_service.py`; la página `pages/1_Configuracion.py` dejó de usar `exec` en la pestaña de backups. La copia se hace con la API de respaldo de `sqlite3` (consistente), con directorio configurable (`BACKUPS_DIR`, por defecto `backups/`) y sin rutas absolutas como el heredado `/Backups`.
6. **Repositorio de eventos y corrección (spec 006):** La corrección de registros individuales y lotes se extrajo a `modulos/correccion_registros/ui.py`, delegando en `infra/eventos_repository.py`. Se eliminaron más de 140 líneas inlined de SQL en `pages/1_Configuracion.py` y se reemplazó el archivo heredado duplicado `3_Modificacion_Tablas.py`.
7. **Repositorio de catálogos (spec 007):** La gestión de los cinco catálogos se extrajo a `modulos/catalogos/ui.py`, delegando en `infra/catalogos_repository.py`. Se eliminó el último `exec(open(...))` de `pages/1_Configuracion.py`, que quedó 100% libre de `exec` y desacoplada de la base de datos.
8. **Repositorio de certificados (spec 008):** El registro de eventos e historial de certificaciones se extrajo a `modulos/gestion_certificados/ui.py`, delegando en `infra/certificados_repository.py`. Se eliminó el `exec` de la pestaña 2 de `pages/2_Administracion_Operadores.py` y el módulo heredado `6_Gestion_Certificados.py` quedó deprecado como redirección.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
