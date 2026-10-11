"""Módulo de reporte de comportamientos (spec 009).

Empaqueta la interfaz Streamlit del registro individual, la carga masiva y el
reporte de reincidencia de comportamientos, separada del punto de entrada en
``pages/``. La interfaz consume exclusivamente la capa
:class:`~certificado_operadores.facade_comportamientos.ComportamientosFacade`,
de modo que no conoce el motor ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_reporte_comportamientos

__all__ = ["render_reporte_comportamientos"]
