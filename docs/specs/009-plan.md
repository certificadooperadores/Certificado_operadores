# Plan 009 — Refactorización UI: Reportes Bitacora

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`009-spec.md`](./009-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el módulo de reporte de comportamientos extrayendo la lógica visual a `src/certificado_operadores/modulos/reporte_comportamientos/ui.py` con una función `render_reporte_comportamientos()`, y encapsulando las consultas y carga en `infra/comportamientos_repository.py`. Esto elimina el último `exec` en `pages/2_Administracion_Operadores.py`.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/2_Administracion_Operadores.py`)  →  Pestaña (`modulos/reporte_comportamientos/ui.py`)  →  Repositorio Comportamientos  →  SQLite
```

La página `2_Administracion_Operadores.py` importa `render_reporte_comportamientos` y la ejecuta en la pestaña 3, culminando la modernización total de la segunda página maestra.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/reporte_comportamientos/ui.py` | crear | Lógica de interfaz de reporte de comportamientos |
| `src/certificado_operadores/modulos/reporte_comportamientos/__init__.py` | crear | Exporta `render_reporte_comportamientos` |
| `src/certificado_operadores/infra/comportamientos_repository.py` | crear | Repositorio para comportamientos y reincidencia |
| `src/certificado_operadores/pages/2_Administracion_Operadores.py` | modificar | Reemplaza el último `exec` por `render_reporte_comportamientos()` |
| `tests/test_reporte_comportamientos.py` | crear | Pruebas unitarias para reporte de comportamientos |

## 4. Orden de implementación

1. Crear repositorio en `src/certificado_operadores/infra/comportamientos_repository.py` para registro individual, validación de carga masiva y reincidencia.
2. Implementar `src/certificado_operadores/modulos/reporte_comportamientos/ui.py` delegando en el repositorio.
3. Actualizar `src/certificado_operadores/pages/2_Administracion_Operadores.py` para invocar `render_reporte_comportamientos()`.
4. Implementar pruebas unitarias en `tests/test_reporte_comportamientos.py`.
5. Ejecutar `make test` y certificar la finalización de la Fase 2.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
