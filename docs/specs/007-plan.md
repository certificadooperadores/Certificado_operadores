# Plan 007 — Refactorización UI: Catalogos

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`007-spec.md`](./007-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar la gestión de catálogos extrayendo la lógica visual a `src/certificado_operadores/modulos/catalogos/ui.py` con una función `render_catalogos()`, y encapsulando el acceso a datos en un repositorio desacoplado. Esto erradica el último `exec(open(...))` en `pages/1_Configuracion.py`.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/1_Configuracion.py`)  →  Pestaña (`modulos/catalogos/ui.py`)  →  Repositorio de Catálogos  →  SQLite
```

La página `1_Configuracion.py` solo importa `render_catalogos` y la ejecuta en su pestaña correspondiente, culminando la modernización total de la página de configuración.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/catalogos/ui.py` | crear | Lógica de interfaz de catálogos |
| `src/certificado_operadores/modulos/catalogos/__init__.py` | crear | Exporta `render_catalogos` |
| `src/certificado_operadores/infra/catalogos_repository.py` | crear | Repositorio para operaciones CRUD de catálogos |
| `src/certificado_operadores/pages/1_Configuracion.py` | modificar | Reemplaza el último `exec(...)` por `render_catalogos()` |
| `tests/test_catalogos.py` | crear | Pruebas unitarias para catálogos |

## 4. Orden de implementación

1. Crear repositorio en `src/certificado_operadores/infra/catalogos_repository.py` con métodos para los 5 catálogos.
2. Implementar `src/certificado_operadores/modulos/catalogos/ui.py` delegando en el repositorio.
3. Actualizar `src/certificado_operadores/pages/1_Configuracion.py` para invocar `render_catalogos()`.
4. Implementar pruebas unitarias en `tests/test_catalogos.py`.
5. Ejecutar `make test` y certificar la finalización de la Fase 1.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
