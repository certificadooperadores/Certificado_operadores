import streamlit as st
from utils import mostrar_badge_version

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")
if not st.session_state.get('logged_in'): st.error("Acceso Denegado."); st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario','')} ({st.session_state.get('rol','')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.switch_page("Inicio.py")

mostrar_badge_version()

exec(open("modulos/10_Reportes.py").read(), globals())
