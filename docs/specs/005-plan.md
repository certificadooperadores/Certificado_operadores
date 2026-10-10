# Plan 005 — Refactorización UI: Administrar Backups

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`005-spec.md`](./005-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar la gestión de copias de seguridad extrayendo la lógica visual a `src/certificado_operadores/modulos/administrar_backups/ui.py` y el manejo de archivos/BD a un servicio desacoplado, eliminando `exec(open(...))` en `pages/1_Configuracion.py`.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/1_Configuracion.py`)  →  Pestaña (`modulos/administrar_backups/ui.py`)  →  Servicio / Facade de Backups  →  Sistema de Archivos y SQLite
```

La página de configuración solo importa `render_administrar_backups` y la ejecuta en la pestaña correspondiente.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/administrar_backups/ui.py` | crear | Lógica de interfaz de backups |
| `src/certificado_operadores/modulos/administrar_backups/__init__.py` | crear | Exporta `render_administrar_backups` |
| `src/certificado_operadores/infra/backup_service.py` | crear | Servicio de copias de seguridad y metadatos |
| `src/certificado_operadores/pages/1_Configuracion.py` | modificar | Reemplaza `exec(...)` de pestaña 2 por importación limpia |
| `tests/test_backups.py` | crear | Pruebas unitarias de gestión de copias de seguridad |

## 4. Orden de implementación

1. Implementar `src/certificado_operadores/infra/backup_service.py` con operaciones de listar, crear, proteger y eliminar copias usando ruta configurable.
2. Crear `src/certificado_operadores/modulos/administrar_backups/ui.py` consumiendo el servicio de backups.
3. Actualizar `src/certificado_operadores/pages/1_Configuracion.py` para reemplazar `exec` por `render_administrar_backups()`.
4. Añadir pruebas unitarias en `tests/test_backups.py`.
5. Ejecutar `make test` y verificar que las pruebas pasen en verde.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
