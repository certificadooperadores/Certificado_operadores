"""Interfaz Streamlit del módulo de administración de backups (spec 005).

Capa de presentación pura: muestra el listado de respaldos y delega la creación,
protección, desprotección y eliminación en
:class:`~certificado_operadores.infra.backup_service.BackupService`. No realiza
operaciones de sistema de archivos ni contiene sentencias SQL: toda la gestión
física de los archivos pasa por el servicio de infraestructura.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# --- Ajuste de ruta de importación -------------------------------------------
# Streamlit agrega al ``sys.path`` la carpeta del script principal
# (``src/certificado_operadores``), no su padre (``src``). Para importar el
# paquete ``certificado_operadores`` dentro de la app —sin depender del
# directorio de trabajo— se agrega ``src`` una sola vez. En las pruebas ya viene
# en el ``path`` (``pythonpath = ["src"]``), por lo que el ajuste es un no-op.
_RUTA_SRC = Path(__file__).resolve().parents[3]
if str(_RUTA_SRC) not in sys.path:
    sys.path.append(str(_RUTA_SRC))

from certificado_operadores.infra.backup_service import (  # noqa: E402
    BackupError,
    BackupInfo,
    BackupService,
)

FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"
"""Formato de fecha y hora usado en la tabla de respaldos."""

ETIQUETA_PROTEGIDO = "🔒 Protegido"
"""Texto mostrado para un respaldo protegido."""

ETIQUETA_DESPROTEGIDO = "🔓 Desprotegido"
"""Texto mostrado para un respaldo desprotegido."""


def filas_backups(backups: list[BackupInfo]) -> list[dict[str, object]]:
    """Traduce los metadatos de respaldo a filas para la tabla de Streamlit.

    Args:
        backups: Respaldos devueltos por el servicio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "Nombre del Archivo": respaldo.nombre,
            "Tamaño (MB)": respaldo.tamano_mb,
            "Fecha de Modificación": respaldo.fecha_modificacion.strftime(FORMATO_FECHA_HORA),
            "Estado": ETIQUETA_PROTEGIDO if respaldo.protegido else ETIQUETA_DESPROTEGIDO,
        }
        for respaldo in backups
    ]


def _render_encabezado() -> None:
    """Pinta el título y la ayuda del módulo."""
    st.title("💾 Gestión de Backups")
    st.markdown("Desde aquí puedes crear, proteger o eliminar backups de la base de datos.")


def _render_creacion(fachada: BackupService) -> None:
    """Pinta y procesa la creación de un nuevo respaldo.

    Args:
        fachada: Servicio de backups inyectado desde el punto de entrada.
    """
    st.subheader("📦 Crear Nuevo Backup")
    confirmar = st.checkbox(
        "Entiendo que el backup se guardará con la fecha y hora actual.",
        key="backup_confirmar",
    )
    if st.button("💾 Crear Backup Ahora", disabled=not confirmar, key="backup_crear"):
        try:
            respaldo = fachada.crear_backup()
        except (BackupError, OSError) as error:
            st.error(f"❌ No se pudo crear el backup: {error}")
        else:
            st.success(f"✅ Backup creado: `{respaldo.nombre}` ({respaldo.tamano_mb} MB)")
            st.rerun()


def _render_proteccion(fachada: BackupService, respaldos: list[BackupInfo]) -> None:
    """Pinta y procesa la protección o desprotección de un respaldo.

    Args:
        fachada: Servicio de backups inyectado desde el punto de entrada.
        respaldos: Respaldos disponibles.
    """
    st.markdown("### 🔒 Proteger / Desproteger")
    seleccionado = st.selectbox(
        "Seleccione el archivo:",
        [respaldo.nombre for respaldo in respaldos],
        key="backup_proteccion_sel",
    )
    respaldo = next((item for item in respaldos if item.nombre == seleccionado), None)
    if respaldo is None:
        return

    if respaldo.protegido:
        if st.button("Quitar Protección", key="backup_desproteger"):
            try:
                actualizado = fachada.desproteger(seleccionado)
            except (BackupError, OSError) as error:
                st.error(f"❌ No se pudo desproteger: {error}")
            else:
                st.success(f"Protección removida: `{actualizado.nombre}`.")
                st.rerun()
    elif st.button("Proteger Backup", key="backup_proteger"):
        try:
            actualizado = fachada.proteger(seleccionado)
        except (BackupError, OSError) as error:
            st.error(f"❌ No se pudo proteger: {error}")
        else:
            st.success(f"Backup protegido: `{actualizado.nombre}`.")
            st.rerun()


def _render_eliminacion(fachada: BackupService, respaldos: list[BackupInfo]) -> None:
    """Pinta y procesa la eliminación de un respaldo desprotegido.

    Args:
        fachada: Servicio de backups inyectado desde el punto de entrada.
        respaldos: Respaldos disponibles.
    """
    st.markdown("### 🗑️ Eliminar Backup")
    desprotegidos = [respaldo.nombre for respaldo in respaldos if not respaldo.protegido]
    if not desprotegidos:
        st.info("No hay backups desprotegidos para eliminar.")
        return

    seleccionado = st.selectbox(
        "Seleccione el archivo (solo desprotegidos):",
        desprotegidos,
        key="backup_eliminacion_sel",
    )
    confirmar = st.checkbox(
        "Estoy seguro de querer eliminar este archivo físicamente.",
        key="backup_eliminacion_confirmar",
    )
    if st.button("🔴 Eliminar Backup", disabled=not confirmar, key="backup_eliminar"):
        try:
            fachada.eliminar(seleccionado)
        except (BackupError, OSError) as error:
            st.error(f"❌ No se pudo eliminar: {error}")
        else:
            st.warning(f"Archivo `{seleccionado}` eliminado permanentemente.")
            st.rerun()


def render_administrar_backups(fachada: BackupService | None = None) -> None:
    """Renderiza la pestaña completa de administración de backups.

    Args:
        fachada: Servicio de backups a usar. Si es ``None`` se construye uno con
            la configuración por defecto; inyectarlo facilita las pruebas.
    """
    fachada = fachada or BackupService()

    _render_encabezado()
    respaldos = fachada.listar_backups()
    _render_creacion(fachada)

    st.markdown("---")
    st.subheader("📋 Backups Existentes")
    if not respaldos:
        st.info("No hay backups disponibles en la carpeta configurada.")
        return
    st.dataframe(filas_backups(respaldos), use_container_width=True)

    st.markdown("---")
    st.subheader("Acciones sobre Backups")
    columna_proteccion, columna_eliminacion = st.columns(2)
    with columna_proteccion:
        _render_proteccion(fachada, respaldos)
    with columna_eliminacion:
        _render_eliminacion(fachada, respaldos)


__all__ = ["filas_backups", "render_administrar_backups"]
