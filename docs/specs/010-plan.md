# Plan 010 — Refactorización UI: Pqr

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`010-spec.md`](./010-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el módulo de reportes y exportaciones extrayendo la lógica visual a `src/certificado_operadores/modulos/reportes/ui.py` con una función `render_reportes()`, y encapsulando las consultas y generación de exportables en `infra/reportes_repository.py`. Esto elimina el último `exec` en `pages/3_Reportes.py`.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/3_Reportes.py`)  →  Página (`modulos/reportes/ui.py`)  →  Repositorio Reportes  →  SQLite
```

La página `3_Reportes.py` solo importa `render_reportes` y la ejecuta, culminando la modernización total de las páginas principales del sistema.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/reportes/ui.py` | crear | Lógica de interfaz de reportes y exportación |
| `src/certificado_operadores/modulos/reportes/__init__.py` | crear | Exporta `render_reportes` |
| `src/certificado_operadores/infra/reportes_repository.py` | crear | Repositorio para consultas y filtros de reportes |
| `src/certificado_operadores/pages/3_Reportes.py` | modificar | Reemplaza `exec` por `render_reportes()` |
| `tests/test_reportes.py` | crear | Pruebas unitarias para generación de reportes |

## 4. Orden de implementación

1. Crear repositorio en `src/certificado_operadores/infra/reportes_repository.py` para catálogos de filtros y consultas de reportes (UTRYT, etc.).
2. Implementar `src/certificado_operadores/modulos/reportes/ui.py` delegando en el repositorio.
3. Actualizar `src/certificado_operadores/pages/3_Reportes.py` para invocar `render_reportes()`.
4. Implementar pruebas unitarias en `tests/test_reportes.py`.
5. Ejecutar `make test` y certificar la finalización de la Fase 3.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
