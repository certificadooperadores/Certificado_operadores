"""Módulo de gestión de usuarios del sistema.

Empaqueta la interfaz Streamlit del módulo de gestión de usuarios, separada del
punto de entrada en ``pages/``. La interfaz consume exclusivamente la capa
:class:`~certificado_operadores.facade_usuarios.UsuariosFacade`, de modo que no
conoce el motor, el esquema ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_gestion_usuarios

__all__ = ["render_gestion_usuarios"]
