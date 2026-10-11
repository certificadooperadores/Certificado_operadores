"""Módulo de gestión de catálogos (spec 007).

Empaqueta la interfaz Streamlit de los cinco catálogos del sistema, separada del
punto de entrada en ``pages/``. La interfaz consume exclusivamente la capa
:class:`~certificado_operadores.facade_configuracion.ConfiguracionFacade`,
de modo que no conoce el motor ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_catalogos

__all__ = ["render_catalogos"]
