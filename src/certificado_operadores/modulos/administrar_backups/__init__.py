"""Módulo de administración de backups de la base de datos.

Empaqueta la interfaz Streamlit del módulo de copias de seguridad, separada del
punto de entrada en ``pages/``. La interfaz consume exclusivamente la capa
:class:`~certificado_operadores.infra.backup_service.BackupService`, de modo que
no conoce el sistema de archivos, el motor ni las sentencias de la base de datos.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from .ui import render_administrar_backups

__all__ = ["render_administrar_backups"]
