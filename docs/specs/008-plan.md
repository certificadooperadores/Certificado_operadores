# Plan 008 — Refactorización UI: Gestion Certificados

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`008-spec.md`](./008-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el módulo de gestión de certificados e historial de eventos extrayendo la lógica visual a `src/certificado_operadores/modulos/gestion_certificados/ui.py` con una función `render_gestion_certificados()`, y encapsulando el acceso a base de datos en la capa de repositorios de infraestructura. Esto elimina el `exec` de la pestaña 2 en `pages/2_Administracion_Operadores.py`.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/2_Administracion_Operadores.py`)  →  Pestaña (`modulos/gestion_certificados/ui.py`)  →  Repositorio / Facade  →  SQLite
```

La página `2_Administracion_Operadores.py` importa `render_gestion_certificados` y la ejecuta en la pestaña 2 de forma limpia y directa.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/gestion_certificados/ui.py` | crear | Lógica de interfaz de certificados y eventos |
| `src/certificado_operadores/modulos/gestion_certificados/__init__.py` | crear | Exporta `render_gestion_certificados` |
| `src/certificado_operadores/infra/certificados_repository.py` | crear | Repositorio para consultas y mutaciones de eventos/certificados |
| `src/certificado_operadores/pages/2_Administracion_Operadores.py` | modificar | Reemplaza `exec` de pestaña 2 por `render_gestion_certificados()` |
| `tests/test_gestion_certificados.py` | crear | Pruebas unitarias de gestión de certificados |

## 4. Orden de implementación

1. Crear repositorio en `src/certificado_operadores/infra/certificados_repository.py` (o extender existentes) para registro y búsqueda de eventos.
2. Implementar `src/certificado_operadores/modulos/gestion_certificados/ui.py` delegando en el repositorio.
3. Actualizar `src/certificado_operadores/pages/2_Administracion_Operadores.py` para invocar `render_gestion_certificados()`.
4. Implementar pruebas unitarias en `tests/test_gestion_certificados.py`.
5. Ejecutar `make test` y verificar cobertura en verde.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
