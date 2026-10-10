"""Módulo de administración de operadores.

Empaqueta la interfaz de Streamlit del módulo de administración de operadores,
separada del punto de entrada en ``pages/``. La interfaz consume
exclusivamente la capa :class:`~certificado_operadores.facade.OperadoresFacade`,
de modo que no conoce el motor, el esquema ni las sentencias de la base de
datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import OperadoresFacade, render_page

__all__ = ["OperadoresFacade", "render_page"]
