# Plan 005 — Refactorización UI: Administrar Backups

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`005-spec.md`](./005-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el módulo administrar_backups para integrarlo al patrón Facade. De esta manera, aseguramos la separación de capas funciona de punta a punta.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/`)  →  Módulo (`modulos/administrar_backups/ui.py`)  →  Facade Correspondiente  →  Infraestructura
```

La página principal en `pages/` solo invocará una función de renderizado `render_page()` desde la carpeta exclusiva del módulo.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/administrar_backups/ui.py` | crear | Funciones únicas de interfaz |
| `src/certificado_operadores/modulos/administrar_backups/__init__.py` | crear | Definición de módulo de Python |
| `src/certificado_operadores/pages/2_Administrar_Backups_Refactor.py` | crear/modificar | Punto de entrada de Streamlit |
| `src/certificado_operadores/modulos/2_Administrar_Backups.py` | eliminar | Archivo obsoleto |

## 4. Orden de implementación

1. Analizar los requerimientos de datos de `2_Administrar_Backups.py`.
2. Extender las capas inferiores (Facade/Repositorio) si se requieren nuevos métodos de acceso a datos.
3. Extraer la vista a `modulos/administrar_backups/ui.py` conectada al Facade.
4. Crear el punto de entrada en `pages/` y eliminar el archivo heredado.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
