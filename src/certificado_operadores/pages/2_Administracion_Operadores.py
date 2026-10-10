"""Punto de entrada de Streamlit: Administración de Operadores.

Página delgada (patrón Facade): delega la pestaña "Operadores" al módulo
``admin_operadores``, la pestaña "Gestión de Certificados" al módulo
``gestion_certificados`` y la pestaña "Reporte de Comportamientos" al módulo
``reporte_comportamientos`` —los tres consumen sus repositorios— cerrando la
Fase 2. Este archivo no ejecuta sentencias de base de datos ni código dinámico
(specs 003, 008 y 009).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

import streamlit as st
from ui_sesion import gestionar_sesion_activa, render_controles_sesion_lateral
from utils import mostrar_badge_version

from certificado_operadores.estilos import inyectar_estilos_metrocali

st.set_page_config(page_title="Administración de Operadores", page_icon="📋", layout="wide")
inyectar_estilos_metrocali()
if not gestionar_sesion_activa():
    st.error("Acceso Denegado.")
    st.stop()

render_controles_sesion_lateral()

mostrar_badge_version()

from modulos.admin_operadores import OperadoresFacade, render_page  # noqa: E402
from modulos.gestion_certificados import render_gestion_certificados  # noqa: E402
from modulos.reporte_comportamientos import render_reporte_comportamientos  # noqa: E402

t1, t2, t3 = st.tabs(["Operadores", "Gestión de Certificados", "Reporte de Comportamientos"])
with t1:
    render_page(OperadoresFacade())
with t2:
    render_gestion_certificados()
with t3:
    render_reporte_comportamientos()
