"""Punto de entrada de Streamlit: Administración de Operadores.

Página delgada (patrón Facade): delega la pestaña "Operadores" al módulo
``admin_operadores`` —que consume exclusivamente ``OperadoresFacade``— y
conserva las pestañas restantes ya existentes. Este archivo no ejecuta
sentencias de base de datos (spec 003).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from pathlib import Path

import streamlit as st
from utils import mostrar_badge_version

st.set_page_config(page_title="Administración de Operadores", page_icon="📋", layout="wide")
if not st.session_state.get("logged_in"):
    st.error("Acceso Denegado.")
    st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario', '')} ({st.session_state.get('rol', '')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.switch_page("Inicio.py")

mostrar_badge_version()

from modulos.admin_operadores import OperadoresFacade, render_page  # noqa: E402

t1, t2, t3 = st.tabs(
    ["👨‍✈️ Operadores", "📅 Gestión de Certificados", "📋 Reporte de Comportamientos"]
)
with t1:
    render_page(OperadoresFacade())
with t2:
    exec(Path("modulos/6_Gestion_Certificados.py").read_text(encoding="utf-8"), globals())
with t3:
    exec(Path("modulos/9_Reporte_Comportamientos.py").read_text(encoding="utf-8"), globals())
