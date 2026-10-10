# Plan 004 — Refactorización UI: Gestion Usuarios

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`004-spec.md`](./004-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el módulo de gestión de usuarios extrayéndolo a `src/certificado_operadores/modulos/gestion_usuarios/ui.py` y conectándolo directamente a través de una función limpia invocada por la página `src/certificado_operadores/pages/1_Configuracion.py`, eliminando la ejecución dinámica por `exec`.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/1_Configuracion.py`)  →  Pestaña (`modulos/gestion_usuarios/ui.py`)  →  Facade / Repositorio  →  BD
```

La página de configuración solo importa `render_gestion_usuarios` y la renderiza dentro de su correspondiente pestaña.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/gestion_usuarios/ui.py` | crear | Lógica de interfaz de gestión de usuarios |
| `src/certificado_operadores/modulos/gestion_usuarios/__init__.py` | crear | Exporta `render_gestion_usuarios` |
| `src/certificado_operadores/pages/1_Configuracion.py` | modificar | Reemplaza `exec(...)` de pestaña 1 por importación limpia |
| `tests/test_gestion_usuarios.py` | crear | Pruebas unitarias para gestión de usuarios |

## 4. Orden de implementación

1. Crear el paquete `src/certificado_operadores/modulos/gestion_usuarios/` con `ui.py` y `__init__.py`.
2. Encapsular las operaciones de lectura y mutación de usuarios fuera de la vista.
3. Actualizar `src/certificado_operadores/pages/1_Configuracion.py` para llamar `render_gestion_usuarios()`.
4. Implementar pruebas unitarias en `tests/test_gestion_usuarios.py`.
5. Validar con `uv run pytest` y `make check`.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
