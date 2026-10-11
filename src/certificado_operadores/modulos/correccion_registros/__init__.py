"""Módulo de corrección de registros de eventos (spec 006).

Empaqueta la interfaz Streamlit de corrección de registros, separada del punto
de entrada en ``pages/``. La interfaz consume exclusivamente la capa
:class:`~certificado_operadores.facade_configuracion.ConfiguracionFacade`, de
modo que no conoce el motor ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_correccion_registros

__all__ = ["render_correccion_registros"]
