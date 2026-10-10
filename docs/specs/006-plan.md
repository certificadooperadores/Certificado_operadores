# Plan 006 — Refactorización UI: Modificacion Tablas

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`006-spec.md`](./006-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar la funcionalidad de corrección de registros extrayéndola de `src/certificado_operadores/pages/1_Configuracion.py` hacia `src/certificado_operadores/modulos/correccion_registros/ui.py` con una función `render_correccion_registros()`, y delegando el acceso a base de datos a un repositorio dedicado.

## 2. Arquitectura y capas

```text
UI (Streamlit `pages/1_Configuracion.py`)  →  Pestaña (`modulos/correccion_registros/ui.py`)  →  Repositorio / Facade Eventos  →  SQLite
```

La página de configuración se limpia eliminando todas las funciones inlined de corrección y consultas SQL, importando únicamente `render_correccion_registros`.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/modulos/correccion_registros/ui.py` | crear | Interfaz visual de corrección de registros |
| `src/certificado_operadores/modulos/correccion_registros/__init__.py` | crear | Exporta `render_correccion_registros` |
| `src/certificado_operadores/infra/eventos_repository.py` | crear | Repositorio para consultas y mutaciones de eventos |
| `src/certificado_operadores/pages/1_Configuracion.py` | modificar | Remueve funciones inlined de corrección y llama a `render_correccion_registros()` |
| `tests/test_correccion_registros.py` | crear | Pruebas unitarias de repositorio y lógica |

## 4. Orden de implementación

1. Implementar repositorio con soporte para listar tipos de evento, filtrar eventos y mutar estado de lotes o registros.
2. Extraer la lógica visual a `src/certificado_operadores/modulos/correccion_registros/ui.py`.
3. Limpiar `src/certificado_operadores/pages/1_Configuracion.py` eliminando el código SQL inlined.
4. Crear pruebas unitarias en `tests/test_correccion_registros.py`.
5. Ejecutar `make test` y validar cobertura en verde.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
