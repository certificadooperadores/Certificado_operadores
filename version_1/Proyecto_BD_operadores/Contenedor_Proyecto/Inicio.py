import streamlit as st, bcrypt
from db import run_query

st.set_page_config(page_title="Gestión de Operadores", page_icon="🚌", layout="wide")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚌 Plataforma de Gestión de Operadores")
    st.subheader("🔒 Iniciar Sesión")
    with st.form("login"):
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            data = run_query("SELECT password_hash, rol, estado FROM dim_usuarios WHERE usuario=:u", {"u": u})
            if data.empty: st.error("❌ Usuario no encontrado.")
            elif data.iloc[0]['estado'] != "Activo": st.error("❌ Usuario inactivo.")
            elif bcrypt.checkpw(p.encode(), data.iloc[0]['password_hash'].encode()):
                st.session_state['logged_in'] = True
                st.session_state['usuario'] = u
                st.session_state['rol'] = data.iloc[0]['rol']
                st.rerun()
            else: st.error("❌ Contraseña incorrecta.")
    st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario','')} ({st.session_state.get('rol','')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

from utils import mostrar_badge_version
st.title("🚌 Plataforma de Gestión de Operadores")
mostrar_badge_version()
