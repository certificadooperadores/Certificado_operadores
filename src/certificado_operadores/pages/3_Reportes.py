"""Punto de entrada de Streamlit: Reportes y Exportaciones.

Página delgada (patrón Facade): delega toda la vista en
``modulos.reportes.render_reportes``, que consume ``ReportesRepository``. No
ejecuta código dinámico (``exec``) ni sentencias de base de datos (spec 010).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

import streamlit as st
from utils import mostrar_badge_version

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")
if not st.session_state.get("logged_in"):
    st.error("Acceso Denegado.")
    st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario', '')} ({st.session_state.get('rol', '')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]
    st.switch_page("Inicio.py")

mostrar_badge_version()

from modulos.reportes.ui import render_reportes  # noqa: E402

render_reportes()
