"""Estilos visuales institucionales de Metrocali (specs 023 y 024).

Capa de presentación pura: centraliza la paleta clara y moderna del portal
oficial ``metrocali.gov.co`` —fondo blanco ``#FFFFFF``, fondos suaves
``#F8FAFC``, azul institucional ``#046BD2`` y texto grafito ``#111827``— y la
inyecta en cualquier página de Streamlit mediante
:func:`inyectar_estilos_metrocali`. También expone el logo oficial para la barra
lateral. No ejecuta tareas de negocio ni accede a la base de datos: solo aplica
presentación.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

# --- Paleta institucional (constantes con nombre, sin colores quemados) -----
COLOR_PRIMARIO = "#046BD2"
"""Azul institucional vivo oficial de Metrocali."""

COLOR_FONDO = "#FFFFFF"
"""Fondo blanco luminoso de la aplicación."""

COLOR_FONDO_SUAVE = "#F8FAFC"
"""Fondo suave para tarjetas y contenedores secundarios."""

COLOR_TEXTO = "#111827"
"""Color de texto grafito de alta legibilidad."""

COLOR_TEXTO_SECUNDARIO = "#6B7280"
"""Gris neutro para subtítulos descriptivos."""

COLOR_BORDE = "#E5E7EB"
"""Borde limpio y sobrio de tarjetas y controles."""

# --- Configuración del logo oficial -----------------------------------------
NOMBRE_ARCHIVO_LOGO = "logo_metrocali.png"
"""Nombre del archivo del logo oficial dentro de ``assets/``."""

VARIABLE_ENTORNO_LOGO = "LOGO_METROCALI"
"""Variable de entorno que permite personalizar la ruta del logo oficial."""

# ``src/certificado_operadores/estilos.py`` → raíz del proyecto es ``parents[2]``.
_DIRECTORIO_ASSETS = Path(__file__).resolve().parents[2] / "assets"

_CSS_METROCALI = f"""
<style>
    /* Contenedor principal a ancho fluido (spec 024): sin tope de anchura y con
       un padding horizontal equilibrado para aprovechar toda la pantalla. */
    .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 2rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
        max-width: none;
    }}

    /* Subtítulos descriptivos en gris neutro (jerarquía tipográfica limpia). */
    h1, h2, h3 {{ color: {COLOR_TEXTO}; }}
    .subtitulo-metrocali {{
        color: {COLOR_TEXTO_SECUNDARIO};
        font-size: 1rem;
        margin-top: -0.6rem;
        margin-bottom: 1rem;
    }}

    /* Tarjetas y contenedores con borde limpio y esquinas suaves. */
    div[data-testid="stMetric"],
    div[data-testid="stForm"],
    div[data-testid="stExpander"] {{
        border: 1px solid {COLOR_BORDE};
        border-radius: 0.75rem;
        background-color: {COLOR_FONDO};
        padding: 0.5rem 0.75rem;
    }}

    /* Pestañas sobrias con acento azul institucional (sin subrayado rojo). */
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
    .stTabs [data-baseweb="tab"] {{
        color: {COLOR_TEXTO_SECUNDARIO};
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{ color: {COLOR_PRIMARIO}; }}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{ background-color: {COLOR_PRIMARIO}; }}
</style>
"""


def ruta_logo() -> Path:
    """Devuelve la ruta del logo oficial de Metrocali.

    La ruta se resuelve de forma relativa al repositorio (nunca absoluta
    quemada) y puede sobrescribirse con la variable de entorno
    :data:`VARIABLE_ENTORNO_LOGO` para entornos donde los recursos viven en otra
    ubicación.

    Returns:
        La ruta del archivo del logo oficial.
    """
    personalizada = os.environ.get(VARIABLE_ENTORNO_LOGO, "").strip()
    if personalizada:
        return Path(personalizada)
    return _DIRECTORIO_ASSETS / NOMBRE_ARCHIVO_LOGO


def inyectar_estilos_metrocali() -> None:
    """Inyecta el CSS institucional y muestra el logo en la barra lateral.

    Aplica los estilos de Metrocali —márgenes, bordes, pestañas y tipografía—
    mediante un bloque ``<style>`` y, si el archivo del logo existe, lo publica
    en la barra lateral con :func:`streamlit.logo`. Es idempotente: puede
    invocarse en cada página sin efectos adversos.
    """
    st.markdown(_CSS_METROCALI, unsafe_allow_html=True)
    logo = ruta_logo()
    if logo.exists():
        st.logo(str(logo))


__all__ = [
    "COLOR_BORDE",
    "COLOR_FONDO",
    "COLOR_FONDO_SUAVE",
    "COLOR_PRIMARIO",
    "COLOR_TEXTO",
    "COLOR_TEXTO_SECUNDARIO",
    "NOMBRE_ARCHIVO_LOGO",
    "VARIABLE_ENTORNO_LOGO",
    "inyectar_estilos_metrocali",
    "ruta_logo",
]
