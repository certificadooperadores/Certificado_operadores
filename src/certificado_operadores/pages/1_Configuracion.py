import streamlit as st
from modulos.administrar_backups.ui import render_administrar_backups
from modulos.catalogos.ui import render_catalogos
from modulos.correccion_registros.ui import render_correccion_registros
from modulos.gestion_usuarios.ui import render_gestion_usuarios
from ui_sesion import gestionar_sesion_activa, render_controles_sesion_lateral
from utils import mostrar_badge_version

from certificado_operadores.estilos import inyectar_estilos_metrocali

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
inyectar_estilos_metrocali()
if not gestionar_sesion_activa():
    st.error("Acceso Denegado.")
    st.stop()
if st.session_state.get("rol") not in ["Administrador", "Super Administrador"]:
    st.error("Acceso Denegado. Solo Administradores.")
    st.stop()

render_controles_sesion_lateral()

mostrar_badge_version()
rol = st.session_state.get("rol", "")

nombres = ["Gestión de Usuarios", "Corrección de Registros", "Catálogos"]
if rol == "Super Administrador":
    nombres.insert(1, "Administrar Backups")
    t1, t2, t3, t4 = st.tabs(nombres)
    with t1:
        render_gestion_usuarios()
    with t2:
        render_administrar_backups()
    with t3:
        render_correccion_registros()
    with t4:
        render_catalogos()
else:
    t1, t2, t3 = st.tabs(nombres)
    with t1:
        render_gestion_usuarios()
    with t2:
        render_correccion_registros()
    with t3:
        render_catalogos()
