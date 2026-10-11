"""Módulo de gestión de certificados (spec 008).

Empaqueta la interfaz Streamlit de registro de eventos e historial de
certificaciones, separada del punto de entrada en ``pages/``. La interfaz
consume exclusivamente la capa
:class:`~certificado_operadores.facade_certificados.CertificadosFacade`,
de modo que no conoce el motor ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_gestion_certificados

__all__ = ["render_gestion_certificados"]
