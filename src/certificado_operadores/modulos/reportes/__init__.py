"""Módulo de reportes y exportaciones (spec 010).

Empaqueta la interfaz Streamlit de reportes consolidados (UTRYT, certificados,
reincidencias, etc.) y sus exportaciones a Excel/CSV, separada del punto de
entrada en ``pages/``. La interfaz consume exclusivamente la capa
:class:`~certificado_operadores.infra.reportes_repository.ReportesRepository`, de
modo que no conoce el motor ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_reportes

__all__ = ["render_reportes"]
