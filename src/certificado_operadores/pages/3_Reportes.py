"""Punto de entrada de Streamlit: Reportes y Exportaciones.

Página delgada (patrón Facade): delega toda la vista en
``modulos.reportes.render_reportes``, que consume ``ReportesRepository``. No
ejecuta código dinámico (``exec``) ni sentencias de base de datos (spec 010).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

import streamlit as st
from ui_sesion import gestionar_sesion_activa, render_controles_sesion_lateral
from utils import mostrar_badge_version

from certificado_operadores.estilos import inyectar_estilos_metrocali

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")
inyectar_estilos_metrocali()
if not gestionar_sesion_activa():
    st.error("Acceso Denegado.")
    st.stop()

render_controles_sesion_lateral()

mostrar_badge_version()

from modulos.reportes.ui import render_reportes  # noqa: E402

render_reportes()
