# Tareas — Spec 023

- [ ] **T01:** Configurar `[theme]` institucional en `.streamlit/config.toml` (colores `#046BD2`, `#FFFFFF`, `#F8FAFC`, `#111827`).
- [ ] **T02:** Crear `src/certificado_operadores/estilos.py` con `inyectar_estilos_metrocali()` y mostrar logo `assets/logo_metrocali.png`.
- [ ] **T03:** Limpiar emojis excesivos en títulos y pestañas de `Inicio.py`, `1_Configuracion.py`, `2_Administracion_Operadores.py` y `3_Reportes.py`.
- [ ] **T04:** Rediseñar `modulos/admin_operadores/ui.py` con datos personales en una sola fila horizontal, desplegables oficiales para Empresa y Tipología, y botón `Guardar Operador`.
- [ ] **T05:** Conectar el guardado de operadores en `OperadoresFacade` con persistencia en `OperadoresRepository`.
- [ ] **T06:** Compactar filtros de `3_Reportes.py` en una única barra horizontal y agregar métricas clave y gráficos livianos.
- [ ] **T07:** Ejecutar `pytest -q -W error` y verificar 100% de pruebas en verde y cero warnings.
