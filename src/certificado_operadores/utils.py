"""Utilidades de presentación compartidas por la interfaz (spec 025).

Expone el indicador lateral con el estado de la versión de la base de datos.
No ejecuta SQL ni conoce rutas quemadas: consulta el estado a través de
:class:`~certificado_operadores.infra.backup_service.BackupService`, respetando
la regla ``UI → Facade → Dominio → Infraestructura``.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import streamlit as st

from certificado_operadores.infra.backup_service import BackupService

TITULO_ESTADO_DATOS = "### 💾 Estado de Datos"
"""Encabezado del bloque de estado en la barra lateral."""

MENSAJE_DATOS_ACTUALIZADOS = "🟢 **Datos Actualizados**"
"""Mensaje cuando la base activa corresponde al respaldo más reciente."""

MENSAJE_BACKUP_DISPONIBLE = "🟡 **¡Backup Nuevo Disponible!**"
"""Mensaje cuando existe un respaldo nuevo sin restaurar."""

TEXTO_REVISAR_BACKUPS = "Revisa la sección de Backups."
"""Indicación para el usuario cuando hay un respaldo nuevo."""

MENSAJE_ERROR_VERSION = "Error cargando versión de BD"
"""Mensaje mostrado si la consulta del estado de versión falla."""


def mostrar_badge_version(servicio: BackupService | None = None) -> None:
    """Muestra un badge persistente con la versión actual de la base de datos.

    Args:
        servicio: Servicio de respaldos a consultar. Si es ``None`` se crea uno
            con la configuración por defecto (spec 025).
    """
    try:
        servicio = servicio or BackupService()
        estado = servicio.estado_version()
        if estado is None:
            return

        st.sidebar.markdown("---")
        st.sidebar.markdown(TITULO_ESTADO_DATOS)
        if estado.actualizado:
            st.sidebar.success(f"{MENSAJE_DATOS_ACTUALIZADOS}\n\nOrigen: `{estado.archivo_origen}`")
        else:
            st.sidebar.warning(
                f"{MENSAJE_BACKUP_DISPONIBLE}\n\nOrigen actual: `{estado.archivo_origen}`"
                f"\n\n{TEXTO_REVISAR_BACKUPS}"
            )
    except Exception:
        st.sidebar.markdown("---")
        st.sidebar.error(MENSAJE_ERROR_VERSION)
