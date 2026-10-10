# Plan 011 — Refactorización UI: Reporte Comportamientos

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`011-spec.md`](./011-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el módulo reporte_comportamientos para integrarlo al patrón Facade. De esta manera, aseguramos la separación de capas funciona de punta a punta.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/`)  →  Módulo (`modulos/reporte_comportamientos/ui.py`)  →  Facade Correspondiente  →  Infraestructura
```

La página principal en `pages/` solo invocará una función de renderizado `render_page()` desde la carpeta exclusiva del módulo.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/reporte_comportamientos/ui.py` | crear | Funciones únicas de interfaz |
| `src/certificado_operadores/modulos/reporte_comportamientos/__init__.py` | crear | Definición de módulo de Python |
| `src/certificado_operadores/pages/9_Reporte_Comportamientos_Refactor.py` | crear/modificar | Punto de entrada de Streamlit |
| `src/certificado_operadores/modulos/9_Reporte_Comportamientos.py` | eliminar | Archivo obsoleto |

## 4. Orden de implementación

1. Analizar los requerimientos de datos de `9_Reporte_Comportamientos.py`.
2. Extender las capas inferiores (Facade/Repositorio) si se requieren nuevos métodos de acceso a datos.
3. Extraer la vista a `modulos/reporte_comportamientos/ui.py` conectada al Facade.
4. Crear el punto de entrada en `pages/` y eliminar el archivo heredado.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
