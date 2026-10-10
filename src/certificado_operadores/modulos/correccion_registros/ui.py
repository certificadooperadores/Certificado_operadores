"""Interfaz Streamlit del módulo de corrección de registros (spec 015).

Capa de presentación pura: organiza la corrección en sub-pestañas por tabla del
sistema (Eventos, Licencias, Comportamientos y Operadores) y delega toda
consulta y mutación en
:class:`~certificado_operadores.infra.eventos_repository.EventosRepository`.

Cada sub-pestaña muestra directamente la tabla interactiva, aprovechando la
búsqueda y el ordenamiento nativos de ``st.dataframe`` y la selección múltiple
de filas, sin formularios externos de filtros. Sobre las filas seleccionadas se
ofrece una barra compacta de acciones (reactivar/vigente, anular/inactivo y
eliminar). No contiene sentencias SQL ni conoce el motor ni el esquema.

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

from certificado_operadores.domain.models import (  # noqa: E402
    VIGENCIA_ACTIVA,
    VIGENCIA_ANULADA,
)
from certificado_operadores.domain.usuarios import ROL_SUPER_ADMINISTRADOR  # noqa: E402
from certificado_operadores.infra.eventos_repository import (  # noqa: E402
    TABLAS_CORRECCION,
    DefinicionTabla,
    EventosRepository,
    RegistroInfo,
)

ETIQUETA_REACTIVAR = "🟢 Reactivar / Vigente"
"""Texto del botón que cambia la vigencia de los registros seleccionados a activa."""

ETIQUETA_ANULAR = "🟡 Anular / Inactivo"
"""Texto del botón que cambia la vigencia de los registros seleccionados a anulada."""

ETIQUETA_ELIMINAR = "🔴 Eliminar"
"""Texto del botón que elimina físicamente los registros seleccionados."""

PREFIJO_CLAVE_TABLA = "corr_tabla_"
"""Prefijo de la clave de sesión de cada ``st.dataframe``."""

PREFIJO_CLAVE_CONFIRMAR = "corr_confirmar_"
"""Prefijo de la clave de sesión del checkbox de confirmación de cada tabla."""

PREFIJO_CLAVE_ACCION = "corr_accion_"
"""Prefijo de la clave de sesión de los botones de acción de cada tabla."""


def filas_registros(
    definicion: DefinicionTabla, registros: list[RegistroInfo]
) -> list[dict[str, object]]:
    """Traduce los DTOs de registro a filas para la tabla de Streamlit.

    Args:
        definicion: Metadatos de la tabla (aporta las etiquetas de columna).
        registros: Registros devueltos por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": registro.id_registro,
            **{
                columna.etiqueta: registro.datos.get(columna.etiqueta)
                for columna in definicion.columnas
            },
            "Estado": registro.estado,
        }
        for registro in registros
    ]


def filas_seleccionadas(seleccion: object) -> list[int]:
    """Extrae los índices de fila marcados en el resultado de ``st.dataframe``.

    Args:
        seleccion: Valor devuelto por ``st.dataframe`` con ``on_select``.

    Returns:
        La lista de índices seleccionados; vacía si no hay selección.
    """
    try:
        filas = getattr(getattr(seleccion, "selection", None), "rows", None) or []
        return [int(indice) for indice in filas]
    except (AttributeError, TypeError, ValueError):
        return []


def ids_seleccionados(registros: list[RegistroInfo], indices: list[int]) -> list[int]:
    """Traduce los índices seleccionados a los IDs de sus registros.

    Args:
        registros: Registros mostrados en la tabla, en el mismo orden.
        indices: Índices de fila devueltos por ``st.dataframe``.

    Returns:
        Los identificadores válidos de las filas seleccionadas.
    """
    return [registros[indice].id_registro for indice in indices if 0 <= indice < len(registros)]


def puede_eliminar(rol: str) -> bool:
    """Indica si el rol puede eliminar registros físicamente.

    Args:
        rol: Rol del usuario de la sesión.

    Returns:
        ``True`` únicamente para el rol Super Administrador.
    """
    return rol == ROL_SUPER_ADMINISTRADOR


def _render_encabezado() -> None:
    """Pinta la ayuda del módulo."""
    st.markdown(
        "Corrige los registros por tabla. Usá la búsqueda y el ordenamiento "
        "integrados de cada tabla, seleccioná una o varias filas y aplicá una "
        "acción (reactivar/vigente, anular/inactivo o eliminar)."
    )


def _render_acciones(
    repositorio: EventosRepository,
    definicion: DefinicionTabla,
    registros: list[RegistroInfo],
    seleccion: object,
    rol: str,
    usuario: str,
) -> None:
    """Dibuja la barra de acciones y aplica la mutación sobre la selección.

    Args:
        repositorio: Repositorio de tablas inyectado desde el punto de entrada.
        definicion: Metadatos de la tabla en curso.
        registros: Registros mostrados en la tabla, en el mismo orden.
        seleccion: Valor devuelto por ``st.dataframe`` con ``on_select``.
        rol: Rol del usuario de la sesión (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
    """
    indices = filas_seleccionadas(seleccion)
    ids = ids_seleccionados(registros, indices)
    confirmar = st.checkbox(
        f"Confirmo aplicar la acción a {len(ids)} fila(s) seleccionada(s).",
        key=f"{PREFIJO_CLAVE_CONFIRMAR}{definicion.clave}",
        disabled=not ids,
    )
    deshabilitado = not (ids and confirmar)

    col_reactivar, col_anular, col_eliminar = st.columns(3)
    with col_reactivar:
        if st.button(
            ETIQUETA_REACTIVAR,
            disabled=deshabilitado,
            key=f"{PREFIJO_CLAVE_ACCION}reactivar_{definicion.clave}",
        ):
            afectados = repositorio.mutar_vigencia(definicion.clave, ids, VIGENCIA_ACTIVA, usuario)
            st.success(f"✅ {afectados} registro(s) reactivado(s).")
            st.rerun()
    with col_anular:
        if st.button(
            ETIQUETA_ANULAR,
            disabled=deshabilitado,
            key=f"{PREFIJO_CLAVE_ACCION}anular_{definicion.clave}",
        ):
            afectados = repositorio.mutar_vigencia(definicion.clave, ids, VIGENCIA_ANULADA, usuario)
            st.success(f"✅ {afectados} registro(s) anulado(s).")
            st.rerun()
    with col_eliminar:
        if puede_eliminar(rol):
            if st.button(
                ETIQUETA_ELIMINAR,
                disabled=deshabilitado,
                key=f"{PREFIJO_CLAVE_ACCION}eliminar_{definicion.clave}",
            ):
                afectados = repositorio.eliminar_registros_tabla(definicion.clave, ids, usuario)
                st.error(f"🗑️ {afectados} registro(s) eliminado(s) permanentemente.")
                st.rerun()
        else:
            st.caption("🔒 Eliminar: solo Super Administrador")


def _render_tabla(
    repositorio: EventosRepository,
    definicion: DefinicionTabla,
    rol: str,
    usuario: str,
) -> None:
    """Renderiza una sub-pestaña: la tabla interactiva y sus acciones.

    Args:
        repositorio: Repositorio de tablas inyectado desde el punto de entrada.
        definicion: Metadatos de la tabla a mostrar.
        rol: Rol del usuario de la sesión (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
    """
    registros = repositorio.listar_registros(definicion.clave)
    if not registros:
        st.info(f"No hay registros en {definicion.etiqueta.lower()}.")
        return

    seleccion = st.dataframe(
        filas_registros(definicion, registros),
        on_select="rerun",
        selection_mode="multi-row",
        hide_index=True,
        use_container_width=True,
        key=f"{PREFIJO_CLAVE_TABLA}{definicion.clave}",
    )
    _render_acciones(repositorio, definicion, registros, seleccion, rol, usuario)


def render_correccion_registros(repositorio: EventosRepository | None = None) -> None:
    """Renderiza la pestaña completa de corrección de registros.

    Args:
        repositorio: Repositorio de tablas a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las
            pruebas.
    """
    repositorio = repositorio or EventosRepository()
    rol = st.session_state.get("rol", "")
    usuario = st.session_state.get("usuario", "")

    _render_encabezado()
    pestanas = st.tabs([definicion.etiqueta for definicion in TABLAS_CORRECCION])
    for pestana, definicion in zip(pestanas, TABLAS_CORRECCION, strict=True):
        with pestana:
            _render_tabla(repositorio, definicion, rol, usuario)


__all__ = [
    "ETIQUETA_ANULAR",
    "ETIQUETA_ELIMINAR",
    "ETIQUETA_REACTIVAR",
    "filas_registros",
    "filas_seleccionadas",
    "ids_seleccionados",
    "puede_eliminar",
    "render_correccion_registros",
]
