# Plan 013 — Persistencia de Sesión con Timeout por Inactividad (20 min) y Refresco de Datos

| Campo     | Valor                                  |
|-----------|----------------------------------------|
| Spec      | [`013-spec.md`](./013-spec.md)         |
| Tareas    | [`013-tareas.md`](./013-tareas.md)     |
| Rama      | `feat/persistencia-sesion-y-refresco`  |
| Enfoque   | TDD (red-green-refactor) + Clean Architecture |

## 1. Arquitectura y diseño

1. **Capa de Infraestructura (`src/certificado_operadores/infra/seguridad.py`):**
   - Constante `SEGUNDOS_INACTIVIDAD_SESION: int = 1200` (20 minutos).
   - Función `generar_token_sesion(usuario: str, rol: str, timestamp: float | None = None) -> str`:
     - Payload JSON con `usuario`, `rol`, `ts` (marca de tiempo actual o proporcionada).
     - Codificación URL-safe en Base64.
     - Firma criptográfica HMAC con SHA-256 usando clave secreta (`SECRET_KEY_SESION` tomada de entorno o valor constante de aplicación).
     - Formato: `<payload_b64>.<firma_hex>`.
   - Función `validar_token_sesion(token: str, tiempo_max: int = 1200, ahora: float | None = None) -> tuple[bool, str | None, str | None, str]`:
     - Separa payload y firma.
     - Recalcula HMAC y compara de forma segura (`hmac.compare_digest`).
     - Decodifica el payload y extrae `usuario`, `rol`, `ts`.
     - Si `ahora - ts > tiempo_max`: retorna `(False, None, None, "expirado")`.
     - Si es válido: retorna `(True, usuario, rol, "valido")`.

2. **Capa Facade (`src/certificado_operadores/facade_usuarios.py`):**
   - `generar_token_sesion(self, usuario: str, rol: str) -> str`: delega en `seguridad.py`.
   - `validar_y_renovar_sesion(self, token: str) -> tuple[bool, str | None, str | None, str | None]`:
     - Valida el token. Si es válido, genera uno nuevo con el timestamp actualizado (renovación por actividad).
     - Retorna `(es_valido, usuario, rol, nuevo_token)`.

3. **Módulo de Soporte de UI (`src/certificado_operadores/ui_sesion.py`):**
   - `gestionar_sesion_activa() -> bool`:
     - Revisa `st.session_state` y `st.query_params.get("session")`.
     - Si el usuario no está en `session_state`, intenta validar el token de la URL. Si es válido, restaura sesión y actualiza el query param con el token renovado.
     - Si el token expiró, limpia los query params y muestra mensaje informativo.
     - Devuelve `True` si hay sesión activa válida, `False` en caso contrario.
   - `render_controles_sesion_lateral()`:
     - Muestra caption con usuario y rol.
     - Botón "🔄 Refrescar Datos": limpia `st.cache_data.clear()`, `st.cache_resource.clear()`, renueva token de sesión y hace `st.rerun()`.
     - Botón "🔒 Cerrar Sesión": borra `st.session_state`, ejecuta `st.query_params.clear()` y redirige al inicio.

4. **Integración en Páginas:**
   - En `Inicio.py`: al hacer login exitoso, genera el token y lo asigna a `st.query_params["session"]`.
   - En `1_Configuracion.py`, `2_Administracion_Operadores.py`, `3_Reportes.py`: usar `gestionar_sesion_activa()` y `render_controles_sesion_lateral()` unificados.

## 2. Fases de ejecución

1. **Fase 1 (TDD Red):** Escribir pruebas en `tests/test_seguridad_sesion.py` validando la firma HMAC, el límite de 1200 segundos y la renovación de tokens.
2. **Fase 2 (Green):** Implementar funciones en `infra/seguridad.py` y métodos en `facade_usuarios.py`.
3. **Fase 3 (UI):** Crear `ui_sesion.py` e integrar en `Inicio.py` y las páginas maestras.
4. **Fase 4 (Verificación):** Comprobar que `uv run pytest` pasa al 100% en verde y que `make check` está limpio.
5. **Fase 5 (Documentación y Commit):** Actualizar `CONSTITUTION.md` y tareas.
