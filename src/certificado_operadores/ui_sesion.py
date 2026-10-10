"""Soporte de sesión persistente y refresco de datos para Streamlit (spec 013).

Capa de presentación pura: restaura la sesión a partir del token firmado que
viaja en los *query params* de la URL, la renueva con cada actividad del usuario
y pinta los controles laterales de **Refrescar Datos** y **Cerrar Sesión**. No
contiene lógica de negocio, SQL ni criptografía: toda validación y firma de
tokens pasa por
:class:`~certificado_operadores.facade_usuarios.UsuariosFacade`
(UI → Facade → Dominio → Infraestructura).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# --- Ajuste de ruta de importación -------------------------------------------
# Streamlit agrega al ``sys.path`` la carpeta del script principal
# (``src/certificado_operadores``), no su padre (``src``). Para importar el
# paquete ``certificado_operadores`` dentro de la app —sin depender del
# directorio de trabajo— se agrega ``src`` una sola vez. En las pruebas ya viene
# en el ``path`` (``pythonpath = ["src"]``), por lo que el ajuste es un no-op.
_RUTA_SRC = Path(__file__).resolve().parents[1]
if str(_RUTA_SRC) not in sys.path:
    sys.path.append(str(_RUTA_SRC))

from certificado_operadores.facade_usuarios import UsuariosFacade  # noqa: E402

CLAVE_QUERY_SESION = "session"
"""Parámetro de URL que transporta el token de sesión firmado."""

CLAVE_ESTADO_LOGGED_IN = "logged_in"
"""Clave de ``st.session_state`` que marca la sesión como iniciada."""

CLAVE_ESTADO_USUARIO = "usuario"
"""Clave de ``st.session_state`` con el nombre del usuario autenticado."""

CLAVE_ESTADO_ROL = "rol"
"""Clave de ``st.session_state`` con el rol del usuario autenticado."""

PAGINA_INICIO = "Inicio.py"
"""Ruta de la página de inicio a la que se redirige al cerrar sesión."""

ETIQUETA_REFRESCAR_DATOS = "🔄 Refrescar Datos"
"""Rótulo del botón que limpia la caché y vuelve a consultar la base de datos."""

ETIQUETA_CERRAR_SESION = "🔒 Cerrar Sesión"
"""Rótulo del botón que cierra la sesión de forma inmediata."""

MENSAJE_SESION_EXPIRADA = "Tu sesión expiró por inactividad. Inicia sesión nuevamente."
"""Aviso mostrado cuando el token superó los 20 minutos sin actividad."""


def _restaurar_estado_sesion(usuario: str, rol: str) -> None:
    """Registra en ``st.session_state`` los datos de la cuenta restaurada.

    Args:
        usuario: Nombre de la cuenta autenticada.
        rol: Rol de la cuenta autenticada.
    """
    st.session_state[CLAVE_ESTADO_LOGGED_IN] = True
    st.session_state[CLAVE_ESTADO_USUARIO] = usuario
    st.session_state[CLAVE_ESTADO_ROL] = rol


def _actualizar_token_url(fachada: UsuariosFacade, usuario: str, rol: str) -> None:
    """Renueva el token de la URL con la marca de actividad actual.

    Args:
        fachada: Fachada que firma el token de sesión.
        usuario: Nombre de la cuenta autenticada.
        rol: Rol de la cuenta autenticada.
    """
    st.query_params[CLAVE_QUERY_SESION] = fachada.generar_token_sesion(usuario, rol)


def _limpiar_sesion() -> None:
    """Borra el estado de sesión y el token de la URL de forma definitiva."""
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]
    st.query_params.clear()


def gestionar_sesion_activa(fachada: UsuariosFacade | None = None) -> bool:
    """Garantiza una sesión activa, restaurándola desde la URL si es necesario.

    Si ``st.session_state`` ya tiene sesión, renueva el token con la actividad
    reciente. Si no, intenta validar el token de ``st.query_params``: cuando está
    vigente (<= 20 minutos) restaura la sesión y guarda el token renovado; cuando
    expiró o es inválido, limpia los *query params* y avisa al usuario.

    Args:
        fachada: Fachada de usuarios inyectable; si es ``None`` se construye la
            predeterminada.

    Returns:
        ``True`` si hay una sesión activa válida; ``False`` en caso contrario.
    """
    if st.session_state.get(CLAVE_ESTADO_LOGGED_IN):
        usuario = st.session_state.get(CLAVE_ESTADO_USUARIO, "")
        rol = st.session_state.get(CLAVE_ESTADO_ROL, "")
        _actualizar_token_url(fachada or UsuariosFacade(), usuario, rol)
        return True

    token = st.query_params.get(CLAVE_QUERY_SESION)
    if not token:
        return False

    gestor = fachada or UsuariosFacade()
    es_valido, usuario, rol, nuevo_token = gestor.validar_y_renovar_sesion(token)
    if not es_valido:
        st.query_params.clear()
        st.warning(MENSAJE_SESION_EXPIRADA)
        return False

    _restaurar_estado_sesion(usuario or "", rol or "")
    if nuevo_token:
        st.query_params[CLAVE_QUERY_SESION] = nuevo_token
    return True


def _refrescar_datos(fachada: UsuariosFacade | None, usuario: str, rol: str) -> None:
    """Limpia las cachés de Streamlit y recarga la página sin cerrar sesión.

    Args:
        fachada: Fachada de usuarios inyectable para renovar el token.
        usuario: Nombre de la cuenta con sesión activa.
        rol: Rol de la cuenta con sesión activa.
    """
    st.cache_data.clear()
    st.cache_resource.clear()
    if usuario:
        _actualizar_token_url(fachada or UsuariosFacade(), usuario, rol)
    st.rerun()


def render_controles_sesion_lateral(
    fachada: UsuariosFacade | None = None,
    *,
    pagina_inicio: bool = False,
) -> None:
    """Pinta en la barra lateral los controles de sesión y de refresco.

    Args:
        fachada: Fachada de usuarios inyectable para renovar el token.
        pagina_inicio: ``True`` si se invoca desde ``Inicio.py``; en ese caso el
            cierre de sesión solo refresca la página, en lugar de redirigir.
    """
    usuario = st.session_state.get(CLAVE_ESTADO_USUARIO, "")
    rol = st.session_state.get(CLAVE_ESTADO_ROL, "")
    st.sidebar.caption(f"👤 {usuario} ({rol})")

    if st.sidebar.button(ETIQUETA_REFRESCAR_DATOS, use_container_width=True):
        _refrescar_datos(fachada, usuario, rol)

    if st.sidebar.button(ETIQUETA_CERRAR_SESION, use_container_width=True):
        _limpiar_sesion()
        if pagina_inicio:
            st.rerun()
        else:
            st.switch_page(PAGINA_INICIO)


__all__ = ["gestionar_sesion_activa", "render_controles_sesion_lateral"]
