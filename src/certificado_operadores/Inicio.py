"""Punto de entrada de la aplicación Streamlit (login y panel principal).

Capa de presentación pura: captura las credenciales y delega la autenticación en
:class:`~certificado_operadores.facade_usuarios.UsuariosFacade`. No contiene
sentencias de base de datos ni usa librerías criptográficas directamente: toda
validación de credenciales pasa por el Facade (patrón Facade).

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

from utils import mostrar_badge_version  # noqa: E402

from certificado_operadores.facade_usuarios import UsuariosFacade  # noqa: E402

st.set_page_config(page_title="Gestión de Operadores", page_icon="🚌", layout="wide")
st.markdown(
    "<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>",
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🚌 Plataforma de Gestión de Operadores")
    st.subheader("🔒 Iniciar Sesión")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            resultado = UsuariosFacade().autenticar(u, p)
            if resultado.exito:
                st.session_state["logged_in"] = True
                st.session_state["usuario"] = u
                st.session_state["rol"] = resultado.rol
                st.rerun()
            else:
                st.error(f"❌ {resultado.mensaje}")
    st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario', '')} ({st.session_state.get('rol', '')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

st.title("🚌 Plataforma de Gestión de Operadores")
mostrar_badge_version()
