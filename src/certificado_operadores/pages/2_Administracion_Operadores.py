import streamlit as st
from utils import mostrar_badge_version

st.set_page_config(page_title="Administración de Operadores", page_icon="📋", layout="wide")
if not st.session_state.get('logged_in'): st.error("Acceso Denegado."); st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario','')} ({st.session_state.get('rol','')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.switch_page("Inicio.py")

mostrar_badge_version()

t1, t2, t3 = st.tabs(["👨‍✈️ Operadores", "📅 Gestión de Certificados", "📋 Reporte de Comportamientos"])
with t1: exec(open("modulos/5_Administracion_Operadores.py").read(), globals())
with t2: exec(open("modulos/6_Gestion_Certificados.py").read(), globals())
with t3: exec(open("modulos/9_Reporte_Comportamientos.py").read(), globals())
