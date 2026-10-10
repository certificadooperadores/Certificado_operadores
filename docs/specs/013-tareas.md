# Tareas 013 — Persistencia de Sesión con Timeout por Inactividad (20 min) y Refresco de Datos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Spec    | [`013-spec.md`](./013-spec.md)                     |
| Plan    | [`013-plan.md`](./013-plan.md)                     |
| Rama    | `feat/persistencia-sesion-y-refresco`              |
| Estado  | en progreso                                        |

## Lista de tareas

- [ ] **T-01:** Crear pruebas en `tests/test_seguridad_sesion.py` validando la generación, validación, expiración a los 20 minutos (1200s), tamper-proofing y renovación de tokens HMAC.
- [ ] **T-02:** Implementar `generar_token_sesion` y `validar_token_sesion` en `src/certificado_operadores/infra/seguridad.py`.
- [ ] **T-03:** Añadir métodos `generar_token_sesion` y `validar_y_renovar_sesion` en `src/certificado_operadores/facade_usuarios.py`.
- [ ] **T-04:** Crear módulo de soporte UI `src/certificado_operadores/ui_sesion.py` con `gestionar_sesion_activa()` y `render_controles_sesion_lateral()` (con botón de Refrescar Datos y Cerrar Sesión).
- [ ] **T-05:** Integrar soporte de sesión en `Inicio.py` y en las páginas de Streamlit (`1_Configuracion.py`, `2_Administracion_Operadores.py`, `3_Reportes.py`).
- [ ] **T-06:** Ejecutar `uv run pytest` hasta 100% de pruebas verdes.
- [ ] **T-07:** Actualizar `docs/referencia-funciones.md` y `CONSTITUTION.md`.
