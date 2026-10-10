# Spec 013 — Persistencia de Sesión con Timeout por Inactividad (20 min) y Refresco de Datos

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/persistencia-sesion-y-refresco`              |
| Relaciona | `004-spec.md` (Usuarios), `011-spec.md` (Login), `012-spec.md` (Auto-inicialización) |

## 1. Contexto y problema

1. **Pérdida de sesión al recargar (F5):**
   - Actualmente, `st.session_state` se almacena exclusivamente en memoria por conexión WebSocket.
   - Si el usuario recarga el navegador con `F5` o actualiza la página para refrescar los datos, Streamlit destruye la sesión y lo expulsa a la pantalla de login.
2. **Requisitos de seguridad de sesión:**
   - El usuario requiere que la sesión permanezca activa entre recargas normales (`F5`), pero debe expirar automáticamente tras **20 minutos de inactividad** (sin interacción del usuario).
   - Al pulsar el botón "Cerrar Sesión", la sesión debe destruirse de inmediato.
3. **Refresco manual de datos y conexión:**
   - Para evitar que el usuario tenga que dar `F5` al navegador cuando desea ver cambios recientes de base de datos o sincronizaciones, se requiere un botón explícito de **Refrescar Datos** en la barra lateral que limpie cachés y vuelva a consultar la base de datos sin cerrar la sesión.

## 2. Objetivos

1. **Criptografía y Tokens de Sesión en Infraestructura (`infra/seguridad.py`):**
   - Implementar generación y validación de tokens de sesión con firma criptográfica HMAC-SHA256 (`generar_token_sesion` y `validar_token_sesion`).
   - El payload del token incluye `usuario`, `rol` y `timestamp_actividad` (marca de tiempo UNIX).
   - La validación verifica la firma y comprueba que `tiempo_actual - timestamp_actividad <= 1200` segundos (20 minutos). Si transcurrieron más de 20 minutos, el token se declara expirado.
2. **Orquestación en Dominio y Facade (`facade_usuarios.py`):**
   - Exponer métodos en `UsuariosFacade` para generar tokens tras login exitoso, validar tokens existentes y renovar el timestamp con la actividad reciente.
3. **Manejo de Sesión en Streamlit UI (`Inicio.py`, páginas y barra lateral):**
   - Al autenticarse, guardar el token en `st.query_params["session"]`.
   - Al cargar `Inicio.py` o cualquiera de las páginas (`1_Configuracion.py`, `2_Administracion_Operadores.py`, `3_Reportes.py`):
     - Si `st.session_state` no tiene sesión pero existe el parámetro `session` en la URL y está vigente (<= 20 min), restaurar la sesión automáticamente y renovar el token.
     - Si el token expiró (> 20 min), eliminar los query params, mostrar advertencia y redirigir al login.
   - Incorporar en la barra lateral el botón **🔄 Refrescar Datos** que limpie la caché de Streamlit (`st.cache_data.clear()`, `st.cache_resource.clear()`) y ejecute `st.rerun()`.
   - El botón **🔒 Cerrar Sesión** debe limpiar `st.session_state` y `st.query_params.clear()`, cerrando la sesión de forma inmediata y definitiva.
4. **Pruebas Unitarias:**
   - Pruebas con `pytest` que validen:
     - Token válido dentro de los 20 minutos.
     - Rechazo por expiración pasados 1201 segundos.
     - Rechazo de tokens manipulados o alterados.
     - Renovación de token.
     - `make test` pasa al 100% en verde.

## 3. No-objetivos

- No utilizar almacenamiento en bases de datos externas de sesiones de servidor; el token es autocontenido y firmado con clave secreta de la app.
- No alterar la lógica de negocio de los operadores ni reportes.

## 4. Requisitos funcionales

- **RF-01:** Recargar el navegador con F5 no cierra la sesión si no han transcurrido más de 20 minutos desde la última interacción.
- **RF-02:** Si transcurren más de 20 minutos de inactividad, la sesión expira y el sistema requiere login nuevamente.
- **RF-03:** El botón "Cerrar Sesión" invalida la sesión de inmediato y borra el parámetro de la URL.
- **RF-04:** El botón "Refrescar Datos" en la barra lateral recarga los datos de la base de datos sin cerrar la sesión ni requerir F5.

## 5. Requisitos no funcionales

- **RNF-01 (Seguridad):** Los tokens deben estar firmados criptográficamente para impedir falsificación de usuario o rol.
- **RNF-02 (Arquitectura):** Se respeta `UI → Facade → Dominio → Infraestructura`.
- **RNF-03 (Pruebas):** Suite de pruebas unitarias al 100% en verde.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** `seguridad.py` contiene `generar_token_sesion` y `validar_token_sesion` con límite de 20 minutos (1200s).
- [ ] **CA-02:** `UsuariosFacade` orquesta la validación y renovación de tokens.
- [ ] **CA-03:** Al recargar la página en Streamlit, la sesión se restaura si el token tiene menos de 20 minutos de inactividad.
- [ ] **CA-04:** Si el token tiene más de 20 minutos de inactividad, se limpia y se solicita autenticación.
- [ ] **CA-05:** La barra lateral incluye el botón para refrescar datos limpiando caché sin cerrar sesión.
- [ ] **CA-06:** Pruebas unitarias cubren todos los escenarios y pasan en verde con `uv run pytest`.

## 10. Enlaces

- Plan: [`013-plan.md`](./013-plan.md)
- Tareas: [`013-tareas.md`](./013-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
