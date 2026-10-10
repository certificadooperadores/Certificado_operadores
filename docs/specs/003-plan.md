# Plan 003 — Refactorización UI: Administración de Operadores

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`003-spec.md`](./003-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Vamos a tomar el módulo de administración de operadores (el monstruo heredado de 30 KB) y vamos a integrarlo con nuestro nuevo Facade. De esta manera, probaremos que la separación de capas funciona de punta a punta.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/`)  →  Módulo (`modulos/admin_operadores/ui.py`)  →  OperadoresFacade  →  Infraestructura
```

La página principal en `pages/` solo invocará una función de renderizado `render_page()` desde la carpeta exclusiva del módulo.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/admin_operadores/ui.py` | crear | Funciones únicas de interfaz para este módulo específico |
| `src/certificado_operadores/modulos/admin_operadores/__init__.py` | crear | Definición de módulo de Python |
| `src/certificado_operadores/pages/2_Administracion_Operadores.py` | crear/modificar | Punto de entrada de Streamlit que importa desde `admin_operadores` |
| `src/certificado_operadores/modulos/5_Administracion_Operadores.py` | eliminar | Se reemplaza por la versión estructurada en su propia carpeta |

## 4. Orden de implementación

1. Analizar los requerimientos de datos de `5_Administracion_Operadores.py`.
2. Extender `OperadoresFacade` y `OperadoresRepository` si la UI necesita guardar/actualizar (actualmente solo leen).
3. Reescribir `pages/2_Administracion_Operadores.py` eliminando llamadas directas SQL y conectándolo al Facade.
4. Eliminar el archivo heredado de la carpeta `modulos/`.

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Funcionalidad rota | Probar exhaustivamente el flujo en Streamlit y añadir pruebas al Facade para los métodos de escritura si se crean. |

## 6. Pruebas previstas

- `make test` debe pasar después de añadir cualquier método nuevo al Facade.
- Prueba manual abriendo `streamlit run Inicio.py` y buscando un operador.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
