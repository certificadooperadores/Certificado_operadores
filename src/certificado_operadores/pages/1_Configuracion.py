import streamlit as st
from modulos.administrar_backups.ui import render_administrar_backups
from modulos.correccion_registros.ui import render_correccion_registros
from modulos.gestion_usuarios.ui import render_gestion_usuarios
from utils import mostrar_badge_version

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
if not st.session_state.get("logged_in"):
    st.error("Acceso Denegado.")
    st.stop()
if st.session_state.get("rol") not in ["Administrador", "Super Administrador"]:
    st.error("Acceso Denegado. Solo Administradores.")
    st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario', '')} ({st.session_state.get('rol', '')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.switch_page("Inicio.py")

mostrar_badge_version()
rol = st.session_state.get("rol", "")

nombres = ["🔐 Gestión de Usuarios", "🗑️ Corrección de Registros", "⚙️ Catálogos"]
if rol == "Super Administrador":
    nombres.insert(1, "💾 Administrar Backups")
    t1, t2, t3, t4 = st.tabs(nombres)
    with t1:
        render_gestion_usuarios()
    with t2:
        render_administrar_backups()
    with t3:
        render_correccion_registros()
    with t4:
        exec(open("modulos/4_Catalogos.py").read(), globals())  # noqa: SIM115
else:
    t1, t2, t3 = st.tabs(nombres)
    with t1:
        render_gestion_usuarios()
    with t2:
        render_correccion_registros()
    with t3:
        exec(open("modulos/4_Catalogos.py").read(), globals())  # noqa: SIM115
