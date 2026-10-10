"""Interfaz Streamlit del módulo de corrección de registros (specs 015 y 017).

Capa de presentación pura: organiza la corrección en sub-pestañas por tabla del
sistema (Eventos, Licencias, Comportamientos y Operadores) y ofrece un **editor
tipo hoja de cálculo** (``st.data_editor``) con listas desplegables en las
columnas permitidas, columnas protegidas de solo lectura y un botón explícito
**Guardar Cambios**. Toda consulta, validación y mutación se delega en
:class:`~certificado_operadores.infra.eventos_repository.EventosRepository`, que
aplica integridad referencial y transacciones atómicas con auditoría.

La UI no contiene sentencias SQL (RNF-01), no conoce el esquema (RNF-02) ni
aprueba reglas de negocio: se limita a capturar la intención del usuario y a
mostrar el resultado o el error controlado que devuelve la infraestructura.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
)
from certificado_operadores.domain.usuarios import ROL_SUPER_ADMINISTRADOR  # noqa: E402
from certificado_operadores.infra.eventos_repository import (  # noqa: E402
    ETIQUETA_ESTADO,
    GENEROS_VALIDOS,
    OPCION_ANULADO,
    OPCION_VIGENTE,
    OPCIONES_ESTADO,
    TABLAS_CORRECCION,
    TIPO_EDICION_CODIGO,
    TIPO_EDICION_ENTERO,
    TIPO_EDICION_EVENTO,
    TIPO_EDICION_GENERO,
    CambioRegistro,
    CodigoInexistenteError,
    ColumnaEditable,
    ColumnaProtegidaError,
    DefinicionTabla,
    DependenciaRegistroError,
    EventosRepository,
    RegistroInfo,
    ValorInvalidoError,
)

ETIQUETA_GUARDAR = "💾 Guardar Cambios"
"""Texto del botón que aplica los cambios del editor."""

PREFIJO_CLAVE_TABLA = "corr_editor_"
"""Prefijo de la clave de sesión del editor de cada tabla."""

PREFIJO_CLAVE_BOTON = "corr_guardar_"
"""Prefijo de la clave de sesión del botón de guardado de cada tabla."""

PREFIJO_CLAVE_MENSAJE = "corr_mensaje_"
"""Prefijo de la clave de sesión del mensaje de resultado de cada tabla."""

CLAVE_TIPO_MENSAJE = "corr_tipo_"
"""Prefijo de la clave de sesión del tipo de mensaje (éxito/error/aviso)."""

MENSAJE_DISPONIBLE = "Disponible solo para Super Administrador."
"""Aviso mostrado cuando un rol no puede eliminar registros."""

ERROR_ELIMINAR_SIN_PERMISO = "🔒 Eliminar registros requiere el rol Super Administrador."
"""Error mostrado cuando un rol distinto al Super Administrador intenta borrar."""

MENSAJE_SIN_CAMBIOS = "No hay cambios por guardar."
"""Aviso mostrado cuando el editor no registra diferencias."""


def _como_entero(valor: object) -> int:
    """Convierte el valor de una celda a entero, tolerando cadenas y decimales.

    Args:
        valor: Valor crudo de la columna ``ID`` del editor.

    Returns:
        El valor convertido a ``int``.
    """
    return int(float(str(valor)))


def filas_editor(
    definicion: DefinicionTabla, registros: list[RegistroInfo]
) -> list[dict[str, object]]:
    """Traduce los DTOs de registro a filas para el editor tipo Excel.

    Añade la columna ``ID`` (protegida), las columnas visibles de la tabla y la
    columna ``Estado`` con las opciones restringidas ``vigente``/``anulado``.

    Args:
        definicion: Metadatos de la tabla (aporta las etiquetas de columna).
        registros: Registros devueltos por el repositorio.

    Returns:
        Lista de diccionarios listos para ``st.data_editor``.
    """
    return [
        {
            "ID": registro.id_registro,
            **{
                columna.etiqueta: registro.datos.get(columna.etiqueta)
                for columna in definicion.columnas
            },
            ETIQUETA_ESTADO: (
                OPCION_VIGENTE if registro.id_vigencia == VIGENCIA_ACTIVA else OPCION_ANULADO
            ),
        }
        for registro in registros
    ]


def opciones_evento(nombres_evento: list[str]) -> list[str]:
    """Construye las opciones de la lista desplegable de tipo de evento.

    Args:
        nombres_evento: Nombres de los tipos de evento del catálogo.

    Returns:
        La lista de nombres, sin duplicados, en el orden recibido.
    """
    return list(dict.fromkeys(nombres_evento))


def _editable_por_etiqueta(definicion: DefinicionTabla) -> dict[str, ColumnaEditable]:
    """Indexa las columnas editables de la tabla por su etiqueta."""
    return {columna.etiqueta: columna for columna in definicion.editables}


def columnas_protegidas(definicion: DefinicionTabla) -> list[str]:
    """Lista los encabezados de las columnas de solo lectura (spec 017, S-03).

    Protege la clave primaria ``ID`` y toda columna visible que no sea editable
    (fechas de auditoría, nombres calculados y cédula).

    Args:
        definicion: Metadatos de la tabla.

    Returns:
        Los encabezados que el editor no debe permitir modificar.
    """
    editables = _editable_por_etiqueta(definicion)
    return ["ID"] + [
        columna.etiqueta for columna in definicion.columnas if columna.etiqueta not in editables
    ]


def _config_editable(columna: ColumnaEditable, opciones_evento: list[str]) -> Any:
    """Construye la configuración de una columna editable del editor."""
    if columna.tipo == TIPO_EDICION_EVENTO:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=opciones_evento)
    if columna.tipo == TIPO_EDICION_GENERO:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=list(GENEROS_VALIDOS))
    if columna.tipo in (TIPO_EDICION_CODIGO, TIPO_EDICION_ENTERO):
        return st.column_config.NumberColumn(columna.etiqueta, step=1)
    return st.column_config.TextColumn(columna.etiqueta)


def configuracion_columnas(
    definicion: DefinicionTabla, opciones_evento: list[str]
) -> dict[str, Any]:
    """Construye el ``column_config`` del editor tipo Excel (spec 017, S-04).

    Configura ``SelectboxColumn`` para el estado (``vigente``/``anulado``), el
    tipo de evento y el género; columnas numéricas para códigos y cédula; y
    columnas de texto para el resto. Las columnas protegidas se marcan como
    deshabilitadas.

    Args:
        definicion: Metadatos de la tabla.
        opciones_evento: Nombres de los tipos de evento para la lista desplegable.

    Returns:
        El mapa ``etiqueta -> column_config`` para ``st.data_editor``.
    """
    editables = _editable_por_etiqueta(definicion)
    protegidas = set(columnas_protegidas(definicion))
    config: dict[str, Any] = {
        "ID": st.column_config.NumberColumn("ID", disabled=True),
    }
    for columna in definicion.columnas:
        if columna.etiqueta in editables:
            config[columna.etiqueta] = _config_editable(
                editables[columna.etiqueta], opciones_evento
            )
        elif columna.etiqueta in protegidas:
            config[columna.etiqueta] = st.column_config.TextColumn(columna.etiqueta, disabled=True)
    config[ETIQUETA_ESTADO] = st.column_config.SelectboxColumn(
        ETIQUETA_ESTADO, options=list(OPCIONES_ESTADO), required=True
    )
    return config


def _columnas_editables(definicion: DefinicionTabla) -> list[str]:
    """Devuelve las etiquetas editables, incluida la columna de estado."""
    return [columna.etiqueta for columna in definicion.editables] + [ETIQUETA_ESTADO]


def detectar_cambios(
    definicion: DefinicionTabla,
    original: list[dict[str, object]],
    editado: list[dict[str, object]],
) -> list[CambioRegistro]:
    """Compara las filas originales con las editadas y extrae los cambios.

    Args:
        definicion: Metadatos de la tabla.
        original: Filas tal como se cargaron en el editor.
        editado: Filas devueltas por ``st.data_editor``.

    Returns:
        La lista de :class:`CambioRegistro` con las celdas modificadas.
    """
    etiquetas = _columnas_editables(definicion)
    originales_por_id = {_como_entero(fila["ID"]): fila for fila in original}
    cambios: list[CambioRegistro] = []
    for fila in editado:
        if "ID" not in fila:
            continue
        id_registro = _como_entero(fila["ID"])
        fila_original = originales_por_id.get(id_registro)
        if fila_original is None:
            continue
        for etiqueta in etiquetas:
            if fila_original.get(etiqueta) != fila.get(etiqueta):
                cambios.append(CambioRegistro(id_registro, etiqueta, fila.get(etiqueta)))
    return cambios


def ids_eliminados(
    original: list[dict[str, object]], editado: list[dict[str, object]]
) -> list[int]:
    """Detecta los IDs que estaban presentes y ya no aparecen en el editor.

    Args:
        original: Filas tal como se cargaron en el editor.
        editado: Filas devueltas por ``st.data_editor``.

    Returns:
        Los identificadores de las filas eliminadas por el usuario.
    """
    presentes = {_como_entero(fila["ID"]) for fila in editado if "ID" in fila}
    return [
        _como_entero(fila["ID"])
        for fila in original
        if "ID" in fila and _como_entero(fila["ID"]) not in presentes
    ]


def puede_eliminar(rol: str) -> bool:
    """Indica si el rol puede eliminar registros físicamente.

    Args:
        rol: Rol del usuario de la sesión.

    Returns:
        ``True`` únicamente para el rol Super Administrador.
    """
    return rol == ROL_SUPER_ADMINISTRADOR


def _como_filas(editor: object) -> list[dict[str, object]]:
    """Normaliza la salida de ``st.data_editor`` a una lista de diccionarios.

    Args:
        editor: Valor devuelto por ``st.data_editor`` (DataFrame o lista).

    Returns:
        Las filas del editor como lista de diccionarios.
    """
    convertidor = getattr(editor, "to_dict", None)
    if callable(convertidor):
        return [dict(fila) for fila in convertidor("records")]
    if isinstance(editor, list):
        return [dict(fila) for fila in editor]
    return []


def _render_mensaje(definicion: DefinicionTabla) -> None:
    """Muestra y descarta el mensaje de resultado pendiente de la tabla.

    Args:
        definicion: Metadatos de la tabla en curso.
    """
    clave = f"{PREFIJO_CLAVE_MENSAJE}{definicion.clave}"
    mensaje = st.session_state.pop(clave, None)
    if not mensaje:
        return
    tipo = st.session_state.pop(f"{CLAVE_TIPO_MENSAJE}{definicion.clave}", "info")
    if tipo == "success":
        st.success(mensaje)
    elif tipo == "error":
        st.error(mensaje)
    elif tipo == "warning":
        st.warning(mensaje)
    else:
        st.info(mensaje)


def _guardar_mensaje(definicion: DefinicionTabla, tipo: str, mensaje: str) -> None:
    """Registra el mensaje de resultado para mostrarlo tras el ``rerun``.

    Args:
        definicion: Metadatos de la tabla en curso.
        tipo: Tipo de mensaje (``success``, ``error``, ``warning`` o ``info``).
        mensaje: Texto a mostrar.
    """
    st.session_state[f"{PREFIJO_CLAVE_MENSAJE}{definicion.clave}"] = mensaje
    st.session_state[f"{CLAVE_TIPO_MENSAJE}{definicion.clave}"] = tipo


def _procesar_guardado(
    repositorio: EventosRepository,
    definicion: DefinicionTabla,
    original: list[dict[str, object]],
    editor: object,
    rol: str,
    usuario: str,
) -> None:
    """Aplica las eliminaciones y ediciones del editor con manejo de errores.

    Args:
        repositorio: Repositorio de tablas inyectado.
        definicion: Metadatos de la tabla en curso.
        original: Filas tal como se cargaron en el editor.
        editor: Valor devuelto por ``st.data_editor``.
        rol: Rol del usuario (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
    """
    editado = _como_filas(editor)
    eliminados = ids_eliminados(original, editado)
    cambios = detectar_cambios(definicion, original, editado)
    if not eliminados and not cambios:
        _guardar_mensaje(definicion, "info", MENSAJE_SIN_CAMBIOS)
        st.rerun()
    if eliminados and not puede_eliminar(rol):
        _guardar_mensaje(definicion, "error", ERROR_ELIMINAR_SIN_PERMISO)
        st.rerun()
    try:
        resumen: list[str] = []
        if eliminados:
            borrados = repositorio.eliminar_registros_tabla(definicion.clave, eliminados, usuario)
            resumen.append(f"🗑️ {borrados} registro(s) eliminado(s).")
        if cambios:
            afectados = repositorio.actualizar_registros_seguros(definicion.clave, cambios, usuario)
            resumen.append(f"✅ {afectados} cambio(s) guardado(s).")
        _guardar_mensaje(definicion, "success", " ".join(resumen))
    except (
        DependenciaRegistroError,
        CodigoInexistenteError,
        ColumnaProtegidaError,
        ValorInvalidoError,
    ) as error:
        _guardar_mensaje(definicion, "error", f"⛔ {error}")
    st.rerun()


def _render_encabezado() -> None:
    """Pinta la ayuda del módulo."""
    st.markdown(
        "Edita como en una hoja de cálculo: las celdas con lista desplegable solo "
        "aceptan valores del catálogo, las llaves primarias y fechas de auditoría "
        "son de solo lectura y al final debes pulsar **Guardar Cambios**. La "
        "eliminación se bloquea si el registro tiene eventos o comportamientos "
        "dependientes."
    )


def _render_tabla(
    repositorio: EventosRepository,
    definicion: DefinicionTabla,
    rol: str,
    usuario: str,
    opciones_tipo_evento: list[str],
) -> None:
    """Renderiza una sub-pestaña: el editor tipo Excel y su botón de guardado.

    Args:
        repositorio: Repositorio de tablas inyectado desde el punto de entrada.
        definicion: Metadatos de la tabla a mostrar.
        rol: Rol del usuario de la sesión (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
        opciones_tipo_evento: Nombres de tipos de evento para la lista desplegable.
    """
    _render_mensaje(definicion)
    registros = repositorio.listar_registros(definicion.clave)
    if not registros:
        st.info(f"No hay registros en {definicion.etiqueta.lower()}.")
        return

    original = filas_editor(definicion, registros)
    editor = st.data_editor(
        original,
        key=f"{PREFIJO_CLAVE_TABLA}{definicion.clave}",
        hide_index=True,
        use_container_width=True,
        num_rows="delete",
        column_config=configuracion_columnas(definicion, opciones_tipo_evento),
        disabled=columnas_protegidas(definicion),
    )
    if st.button(
        ETIQUETA_GUARDAR,
        key=f"{PREFIJO_CLAVE_BOTON}{definicion.clave}",
    ):
        _procesar_guardado(repositorio, definicion, original, editor, rol, usuario)
    if not puede_eliminar(rol):
        st.caption(f"🔒 {MENSAJE_DISPONIBLE}")


def render_correccion_registros(repositorio: EventosRepository | None = None) -> None:
    """Renderiza la pestaña completa de corrección de registros.

    Args:
        repositorio: Repositorio de tablas a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las pruebas.
    """
    repositorio = repositorio or EventosRepository()
    rol = st.session_state.get("rol", "")
    usuario = st.session_state.get("usuario", "")
    opciones_tipo_evento = opciones_evento(
        [tipo.nombre_evento for tipo in repositorio.listar_tipos_evento()]
    )

    _render_encabezado()
    pestanas = st.tabs([definicion.etiqueta for definicion in TABLAS_CORRECCION])
    for pestana, definicion in zip(pestanas, TABLAS_CORRECCION, strict=True):
        with pestana:
            _render_tabla(repositorio, definicion, rol, usuario, opciones_tipo_evento)


__all__ = [
    "ETIQUETA_GUARDAR",
    "columnas_protegidas",
    "configuracion_columnas",
    "detectar_cambios",
    "filas_editor",
    "ids_eliminados",
    "opciones_evento",
    "puede_eliminar",
    "render_correccion_registros",
]
