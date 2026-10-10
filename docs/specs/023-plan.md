# Plan de Implementación — Spec 023

## Objetivo
Implementar la estandarización visual y rediseño UI/UX institucional con la paleta de metrocali.gov.co, eliminar emojis innecesarios, compactar toolbars en filas únicas y completar el formulario de operadores con guardado real en base de datos.

## Fases

### Fase 1: Tema y Estilos Globales
- Configurar `[theme]` en `.streamlit/config.toml` con `#046BD2`, `#FFFFFF`, `#F8FAFC`, `#111827`.
- Crear `src/certificado_operadores/estilos.py` e integrar `inyectar_estilos_metrocali()` y visualización del logo en la barra lateral.
- Llamar a la inyección de estilos en `Inicio.py` y en todas las páginas de `pages/`.

### Fase 2: Depuración de Emojis y Jerarquía Visual
- Revisar `Inicio.py`, `1_Configuracion.py`, `2_Administracion_Operadores.py` y `3_Reportes.py`.
- Reemplazar `st.title` con nombres limpios sin emojis infantiles.
- Renombrar `st.tabs` con nombres profesionales en texto plano.

### Fase 3: Rediseño del Módulo de Operadores y Botón Guardar
- Ajustar `src/certificado_operadores/modulos/admin_operadores/ui.py` para organizar los datos personales en una sola fila compacta con `st.columns`.
- Desplegables oficiales para Empresa y Tipología.
- Incorporar método `guardar_operador` en `OperadoresFacade` e implementar el botón `Guardar Operador` en la interfaz.

### Fase 4: Toolbar Horizontal y Gráficos en Reportes
- Rediseñar filtros en `3_Reportes.py` en una sola fila horizontal.
- Agregar tarjetas de KPIs (`st.metric`) y visualización de barras nativa (`st.bar_chart`).

### Fase 5: Pruebas y Cero Advertencias
- Agregar tests en `tests/test_admin_operadores.py` o correspondientes para verificar creación/guardado y estilos.
- Correr `pytest -q -W error` garantizando 100% verde y 0 warnings.
