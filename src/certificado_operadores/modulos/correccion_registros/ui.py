"""Interfaz Streamlit del módulo de corrección de registros (spec 006).

Capa de presentación pura: filtra eventos por código, cédula, tipo, estado y
rango de fechas, y delega toda búsqueda y mutación (reactivar, anular o eliminar
registros individuales o lotes completos) en
:class:`~certificado_operadores.infra.eventos_repository.EventosRepository`. No
contiene sentencias SQL ni conoce el motor ni el esquema: toda interacción con
datos pasa por el repositorio.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from datetime import date, datetime
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
    LIMITE_POR_DEFECTO,
    EventoInfo,
    EventosRepository,
    FiltroEventos,
    LoteInfo,
    TipoEventoInfo,
)

ETIQUETA_TODOS = "Todos"
"""Opción por defecto de los selectores que no aplican filtro."""

OPCION_VIGENTE = "Vigente"
"""Opción de estado para filtrar los eventos vigentes."""

OPCION_ANULADO = "Anulado"
"""Opción de estado para filtrar los eventos anulados."""

OPCIONES_ESTADO: tuple[str, ...] = (ETIQUETA_TODOS, OPCION_VIGENTE, OPCION_ANULADO)
"""Opciones del selector de estado."""

SEPARADOR_OPCION = " - "
"""Separador entre el identificador y el nombre en las opciones del selector."""

SEPARADOR_ETIQUETA_LOTE = " ("
"""Separador entre el lote y su conteo en la etiqueta del selector."""


def parsear_entero_positivo(texto: str) -> int | None:
    """Convierte el texto de un campo en un entero positivo.

    Args:
        texto: Contenido del campo de texto.

    Returns:
        El entero positivo, o ``None`` si el texto está vacío o no es numérico.
    """
    limpio = texto.strip()
    if limpio.isdigit() and int(limpio) > 0:
        return int(limpio)
    return None


def opciones_tipos_evento(tipos: list[TipoEventoInfo]) -> list[str]:
    """Construye las opciones del selector de tipos de evento.

    Args:
        tipos: Tipos de evento devueltos por el repositorio.

    Returns:
        La opción "Todos" seguida de cada tipo como "id - nombre".
    """
    return [
        ETIQUETA_TODOS,
        *(f"{tipo.id_tipo_evento}{SEPARADOR_OPCION}{tipo.nombre_evento}" for tipo in tipos),
    ]


def id_tipo_evento_desde_opcion(opcion: str) -> int | None:
    """Extrae el identificador de tipo de evento de la opción seleccionada.

    Args:
        opcion: Opción "Todos" o "id - nombre".

    Returns:
        El identificador del tipo de evento, o ``None`` si no aplica filtro.
    """
    if opcion == ETIQUETA_TODOS:
        return None
    return int(opcion.split(SEPARADOR_OPCION)[0])


def vigencia_desde_estado(estado: str) -> int | None:
    """Traduce la opción de estado a la vigencia correspondiente.

    Args:
        estado: Opción seleccionada ("Todos", "Vigente" o "Anulado").

    Returns:
        La vigencia (activa o anulada), o ``None`` si no aplica filtro.
    """
    if estado == OPCION_VIGENTE:
        return VIGENCIA_ACTIVA
    if estado == OPCION_ANULADO:
        return VIGENCIA_ANULADA
    return None


def construir_filtro(
    codigo: str,
    cedula: str,
    tipo_evento: str,
    estado: str,
    fecha_desde: object,
    fecha_hasta: object,
) -> FiltroEventos:
    """Traduce los campos del formulario a un :class:`FiltroEventos`.

    Args:
        codigo: Texto del campo de código de operador.
        cedula: Texto del campo de cédula.
        tipo_evento: Opción del selector de tipo de evento.
        estado: Opción del selector de estado.
        fecha_desde: Valor del selector de fecha inicial.
        fecha_hasta: Valor del selector de fecha final.

    Returns:
        El filtro listo para el repositorio.
    """
    return FiltroEventos(
        codigo=parsear_entero_positivo(codigo),
        cedula=parsear_entero_positivo(cedula),
        id_tipo_evento=id_tipo_evento_desde_opcion(tipo_evento),
        vigencia=vigencia_desde_estado(estado),
        fecha_desde=_como_fecha(fecha_desde),
        fecha_hasta=_como_fecha(fecha_hasta),
    )


def etiqueta_lote(lote: LoteInfo) -> str:
    """Construye la etiqueta legible de un lote para el selector.

    Args:
        lote: Lote devuelto por el repositorio.

    Returns:
        La etiqueta "YYYY-MM-DD HH:MM (n reg.)".
    """
    return f"{lote.lote}{SEPARADOR_ETIQUETA_LOTE}{lote.total} reg.)"


def lote_desde_etiqueta(etiqueta: str) -> str:
    """Extrae la marca temporal del lote a partir de su etiqueta.

    Args:
        etiqueta: Etiqueta "YYYY-MM-DD HH:MM (n reg.)".

    Returns:
        La marca temporal del lote.
    """
    return etiqueta.split(SEPARADOR_ETIQUETA_LOTE)[0]


def filas_eventos(eventos: list[EventoInfo]) -> list[dict[str, object]]:
    """Traduce los DTOs de evento a filas para la tabla de Streamlit.

    Args:
        eventos: Eventos devueltos por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": evento.id_hecho_evento,
            "Código": evento.id_codigo,
            "Cédula": evento.cedula,
            "Nombre": evento.nombre,
            "Evento": evento.nombre_evento,
            "Fecha": evento.fecha,
            "Estado": evento.estado,
        }
        for evento in eventos
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


def puede_eliminar(rol: str) -> bool:
    """Indica si el rol puede eliminar registros físicamente.

    Args:
        rol: Rol del usuario de la sesión.

    Returns:
        ``True`` únicamente para el rol Super Administrador.
    """
    return rol == ROL_SUPER_ADMINISTRADOR


def _como_fecha(valor: object) -> date | None:
    """Normaliza el valor de un selector de fecha a ``date``.

    Args:
        valor: Valor devuelto por ``st.date_input``.

    Returns:
        La fecha, o ``None`` si el valor no es una fecha simple.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return None


def _render_encabezado() -> None:
    """Pinta la ayuda del módulo."""
    st.markdown(
        "Corrige registros de eventos: filtrá por código, cédula, tipo, fecha o "
        "estado, o trabajá sobre un lote completo por minuto de cargue."
    )


def _render_individual(repositorio: EventosRepository, rol: str, usuario: str) -> None:
    """Renderiza y procesa la corrección de registros individuales (RF-01).

    Args:
        repositorio: Repositorio de eventos inyectado desde el punto de entrada.
        rol: Rol del usuario de la sesión (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown(
        "Buscar registros de eventos por código, cédula, tipo, fecha o estado. "
        "Seleccioná las filas y aplicá una acción."
    )
    tipos = repositorio.listar_tipos_evento()

    col1, col2, col3 = st.columns(3)
    with col1:
        codigo = st.text_input("Código operador", key="corr_cod")
        cedula = st.text_input("Cédula", key="corr_ced")
    with col2:
        evento = st.selectbox("Tipo de evento", opciones_tipos_evento(tipos), key="corr_evt")
        estado = st.selectbox("Estado", OPCIONES_ESTADO, key="corr_est")
    with col3:
        fecha_desde = st.date_input("Fecha desde", value=None, key="corr_desde")
        fecha_hasta = st.date_input("Fecha hasta", value=None, key="corr_hasta")

    filtro = construir_filtro(codigo, cedula, evento, estado, fecha_desde, fecha_hasta)
    eventos = repositorio.buscar_eventos(filtro)
    if not eventos:
        st.info("No se encontraron registros con esos filtros.")
        return

    st.markdown(
        f"**{len(eventos)} registro(s)** (máx {LIMITE_POR_DEFECTO}). "
        "Hacé clic en las filas para seleccionar."
    )
    seleccion = st.dataframe(
        filas_eventos(eventos),
        on_select="rerun",
        selection_mode="multi-row",
        hide_index=True,
        use_container_width=True,
        key="corr_table",
    )

    indices = filas_seleccionadas(seleccion)
    if not indices:
        return

    ids = [eventos[indice].id_hecho_evento for indice in indices]
    st.warning(f"⚠️ {len(ids)} registro(s) seleccionado(s).")
    confirmar = st.checkbox(
        "Confirmo que quiero aplicar la acción a los registros seleccionados.",
        key="corr_conf",
    )

    col_reactivar, col_anular, col_eliminar = st.columns(3)
    with col_reactivar:
        if st.button("🟢 Reactivar", disabled=not confirmar, key="corr_react"):
            repositorio.reactivar_registros(ids, usuario)
            st.success(f"✅ {len(ids)} registro(s) reactivado(s).")
            st.rerun()
    with col_anular:
        if st.button("🟡 Anular", disabled=not confirmar, key="corr_anul"):
            repositorio.anular_registros(ids, usuario)
            st.success(f"✅ {len(ids)} registro(s) anulado(s).")
            st.rerun()
    with col_eliminar:
        if puede_eliminar(rol):
            if st.button("🔴 Eliminar", disabled=not confirmar, key="corr_elim"):
                repositorio.eliminar_registros(ids, usuario)
                st.error(f"🗑️ {len(ids)} registro(s) eliminado(s) permanentemente.")
                st.rerun()
        else:
            st.caption("🔒 Eliminar: solo Super Admin")


def _render_lote(repositorio: EventosRepository, rol: str, usuario: str) -> None:
    """Renderiza y procesa la corrección por lote completo (RF-02).

    Args:
        repositorio: Repositorio de eventos inyectado desde el punto de entrada.
        rol: Rol del usuario de la sesión (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown(
        "Seleccioná un lote (registros cargados en el mismo minuto) para "
        "modificarlo o borrarlo de una vez."
    )
    lotes = repositorio.listar_lotes()
    if not lotes:
        st.info("Sin eventos.")
        return

    etiqueta = st.selectbox("Lote", [etiqueta_lote(lote) for lote in lotes], key="corr_lote")
    detalle = repositorio.listar_eventos_de_lote(lote_desde_etiqueta(etiqueta))
    if not detalle:
        st.info("No hay registros en este lote.")
        return

    vigentes = sum(1 for evento in detalle if evento.id_vigencia == VIGENCIA_ACTIVA)
    anulados = sum(1 for evento in detalle if evento.id_vigencia == VIGENCIA_ANULADA)
    st.caption(f"{vigentes} vigentes · {anulados} anulados · {len(detalle)} total")
    st.dataframe(filas_eventos(detalle), use_container_width=True, hide_index=True)

    confirmar = st.checkbox(
        "Confirmo que quiero aplicar la acción a TODO el lote.", key="corr_conf_lote"
    )
    lote = lote_desde_etiqueta(etiqueta)

    col_reactivar, col_anular, col_eliminar = st.columns(3)
    with col_reactivar:
        if st.button("🟢 Reactivar Lote", disabled=not confirmar, key="corr_react_lote"):
            repositorio.reactivar_lote(lote, usuario)
            st.success("✅ Lote reactivado.")
            st.rerun()
    with col_anular:
        if st.button("🟡 Anular Lote", disabled=not confirmar, key="corr_anul_lote"):
            repositorio.anular_lote(lote, usuario)
            st.success("✅ Lote anulado.")
            st.rerun()
    with col_eliminar:
        if puede_eliminar(rol):
            if st.button("🔴 Borrar Lote", disabled=not confirmar, key="corr_elim_lote"):
                repositorio.eliminar_lote(lote, usuario)
                st.error("🗑️ Lote eliminado.")
                st.rerun()
        else:
            st.caption("🔒 Borrar: solo Super Admin")


def render_correccion_registros(repositorio: EventosRepository | None = None) -> None:
    """Renderiza la pestaña completa de corrección de registros.

    Args:
        repositorio: Repositorio de eventos a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las
            pruebas.
    """
    repositorio = repositorio or EventosRepository()
    rol = st.session_state.get("rol", "")
    usuario = st.session_state.get("usuario", "")

    _render_encabezado()
    tab_individual, tab_lote = st.tabs(["🎯 Registro Individual", "📦 Por Lote"])
    with tab_individual:
        _render_individual(repositorio, rol, usuario)
    with tab_lote:
        _render_lote(repositorio, rol, usuario)


__all__ = [
    "ETIQUETA_TODOS",
    "OPCIONES_ESTADO",
    "OPCION_ANULADO",
    "OPCION_VIGENTE",
    "construir_filtro",
    "etiqueta_lote",
    "filas_eventos",
    "filas_seleccionadas",
    "id_tipo_evento_desde_opcion",
    "lote_desde_etiqueta",
    "opciones_tipos_evento",
    "parsear_entero_positivo",
    "puede_eliminar",
    "render_correccion_registros",
    "vigencia_desde_estado",
]
