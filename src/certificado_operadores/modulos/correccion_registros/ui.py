"""Interfaz Streamlit del módulo de corrección de registros (specs 015, 017 y 018).

Capa de presentación pura: organiza la corrección en sub-pestañas por tabla del
sistema (Eventos, Licencias, Comportamientos, Operadores y Códigos) y ofrece un
**editor tipo hoja de cálculo** (``st.data_editor``) con listas desplegables en las
columnas permitidas, columnas protegidas de solo lectura y un botón explícito
**Guardar Cambios**. La spec 018 añade una barra de **búsqueda rápida** por
sub-pestaña, listas oficiales de licencias y comportamientos, la tabla de
**Códigos** y los botones de **acción en bloque** (marcar vigente/anulado y
eliminar las filas seleccionadas). Toda consulta, validación y mutación se delega
en :class:`~certificado_operadores.facade_configuracion.ConfiguracionFacade`, que
aplica integridad referencial y transacciones atómicas con auditoría.

La UI no contiene sentencias SQL (RNF-01), no conoce el esquema (RNF-02) ni
aprueba reglas de negocio: se limita a capturar la intención del usuario y a
mostrar el resultado o el error controlado que devuelve la infraestructura.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from dataclasses import replace
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
    VIGENCIA_ANULADA,
)
from certificado_operadores.domain.usuarios import ROL_SUPER_ADMINISTRADOR  # noqa: E402
from certificado_operadores.facade_configuracion import (  # noqa: E402
    CLAVE_TABLA_EVENTOS,
    ETIQUETA_ESTADO,
    ETIQUETA_EVENTO,
    GENEROS_VALIDOS,
    OPCION_ANULADO,
    OPCION_VIGENTE,
    OPCIONES_ESTADO,
    OPCIONES_LICENCIA,
    TABLAS_CORRECCION,
    TIPO_EDICION_CODIGO,
    TIPO_EDICION_DESCRIPCION,
    TIPO_EDICION_ENTERO,
    TIPO_EDICION_EVENTO,
    TIPO_EDICION_FECHA,
    TIPO_EDICION_FUENTE,
    TIPO_EDICION_GENERO,
    TIPO_EDICION_LICENCIA,
    CambioRegistro,
    CampoIncompatibleError,
    CodigoInexistenteError,
    ColumnaEditable,
    ColumnaProtegidaError,
    ConfiguracionFacade,
    DefinicionTabla,
    DependenciaRegistroError,
    RegistroInfo,
    TipoEventoInfo,
    ValorInvalidoError,
    campos_permitidos_evento,
)

ETIQUETA_GUARDAR = "💾 Guardar Cambios"
"""Texto del botón que aplica los cambios del editor."""

PREFIJO_CLAVE_TABLA = "corr_editor_"
"""Prefijo de la clave de sesión del editor de cada tabla."""

PREFIJO_CLAVE_BOTON = "corr_guardar_"
"""Prefijo de la clave de sesión del botón de guardado de cada tabla."""

PREFIJO_CLAVE_MENSAJE = "corr_mensaje_"
"""Prefijo de la clave de sesión del mensaje de resultado de cada tabla."""

PREFIJO_CLAVE_FILTRO = "filtro_"
"""Prefijo de la clave de sesión de la barra de búsqueda rápida (spec 018)."""

PREFIJO_CLAVE_BLOQUE = "corr_bloque_"
"""Prefijo de la clave de sesión de los botones de acción en bloque (spec 018)."""

CLAVE_TIPO_MENSAJE = "corr_tipo_"
"""Prefijo de la clave de sesión del tipo de mensaje (éxito/error/aviso)."""

MENSAJE_DISPONIBLE = "Disponible solo para Super Administrador."
"""Aviso mostrado cuando un rol no puede eliminar registros."""

ERROR_ELIMINAR_SIN_PERMISO = "🔒 Eliminar registros requiere el rol Super Administrador."
"""Error mostrado cuando un rol distinto al Super Administrador intenta borrar."""

MENSAJE_SIN_CAMBIOS = "No hay cambios por guardar."
"""Aviso mostrado cuando el editor no registra diferencias."""

ETIQUETA_FILTRO = "🔍 Filtrar tabla:"
"""Etiqueta de la barra de búsqueda rápida de cada tabla (spec 018)."""

PLACEHOLDER_FILTRO = "Buscar por código, cédula, nombre, evento, fecha o estado..."
"""Texto guía de la barra de búsqueda rápida por sub-pestaña (spec 018)."""

ETIQUETA_SELECCION = "Seleccionar"
"""Encabezado de la casilla de selección múltiple de filas (spec 018)."""

ETIQUETA_VIGENTE_BLOQUE = "Marcar Vigente (Seleccionados)"
"""Texto del botón que marca como vigentes las filas seleccionadas (spec 018)."""

ETIQUETA_ANULADO_BLOQUE = "Marcar Anulado (Seleccionados)"
"""Texto del botón que marca como anuladas las filas seleccionadas (spec 018)."""

ETIQUETA_ELIMINAR_BLOQUE = "Eliminar (Seleccionados)"
"""Texto del botón que elimina las filas seleccionadas (spec 018)."""

MENSAJE_SIN_SELECCION = "Seleccione al menos una fila para la acción en bloque."
"""Aviso mostrado cuando no hay filas marcadas para una acción en bloque (spec 018)."""

MENSAJE_SIN_COINCIDENCIAS = "Ningún registro coincide con el filtro."
"""Aviso mostrado cuando la búsqueda rápida no encuentra coincidencias (spec 018)."""

ETIQUETA_TIPO_EVENTO = "🎫 Tipo de evento:"
"""Etiqueta del selector de categoría de evento de la sub-pestaña Eventos (spec 020)."""

OPCION_TODOS_EVENTOS = "Todos"
"""Opción del selector que muestra todas las categorías y columnas (spec 020)."""

MENSAJE_RESTRICCIONES_EVENTO = (
    "Con un tipo de evento específico solo se muestran las columnas aplicables a "
    "esa categoría. En «Todos» se muestran todas las columnas y el sistema "
    "rechazará al guardar los campos incompatibles con cada evento."
)
"""Mensaje orientativo sobre las restricciones de campos por categoría (spec 020)."""


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


def filtrar_filas(filas: list[dict[str, object]], termino: str) -> list[dict[str, object]]:
    """Filtra en memoria las filas del editor por un término de búsqueda (spec 018).

    La comparación es insensible a mayúsculas y busca el término como subcadena
    en cualquiera de las celdas de la fila. Un término vacío devuelve todas las
    filas.

    Args:
        filas: Filas del editor (diccionarios ``etiqueta -> valor``).
        termino: Texto introducido en la barra de búsqueda rápida.

    Returns:
        Las filas que contienen el término en alguna de sus celdas.
    """
    limpio = termino.strip().lower()
    if not limpio:
        return list(filas)
    return [
        fila
        for fila in filas
        if any(limpio in str(valor).lower() for valor in fila.values() if valor is not None)
    ]


def filas_con_seleccion(filas: list[dict[str, object]]) -> list[dict[str, object]]:
    """Añade la casilla ``Seleccionar`` (sin marcar) a las filas del editor (spec 018).

    Args:
        filas: Filas del editor sin la columna de selección.

    Returns:
        Nuevas filas con ``Seleccionar`` en primer lugar y valor ``False``.
    """
    return [{ETIQUETA_SELECCION: False, **fila} for fila in filas]


def ids_seleccionados(filas: list[dict[str, object]]) -> list[int]:
    """Extrae los IDs de las filas cuya casilla ``Seleccionar`` está marcada (spec 018).

    Se descartan las filas añadidas por el usuario (sin ``ID``) y los valores no
    convertibles a entero.

    Args:
        filas: Filas devueltas por el editor, con la casilla de selección.

    Returns:
        Los identificadores de las filas seleccionadas, en el orden recibido.
    """
    seleccionados: list[int] = []
    for fila in filas:
        if not fila.get(ETIQUETA_SELECCION):
            continue
        if fila.get("ID") in (None, ""):
            continue
        try:
            seleccionados.append(_como_entero(fila["ID"]))
        except (TypeError, ValueError):
            continue
    return seleccionados


def opciones_evento(nombres_evento: list[str]) -> list[str]:
    """Construye las opciones de la lista desplegable de tipo de evento.

    Args:
        nombres_evento: Nombres de los tipos de evento del catálogo.

    Returns:
        La lista de nombres, sin duplicados, en el orden recibido.
    """
    return list(dict.fromkeys(nombres_evento))


def id_tipo_evento_por_nombre(tipos_evento: list[TipoEventoInfo], nombre: str) -> int | None:
    """Resuelve el identificador de un tipo de evento a partir de su nombre (spec 020).

    Args:
        tipos_evento: Tipos de evento del catálogo con su identificador.
        nombre: Nombre legible del tipo de evento seleccionado.

    Returns:
        El identificador del tipo de evento, o ``None`` si no coincide ninguno.
    """
    for tipo in tipos_evento:
        if tipo.nombre_evento == nombre:
            return tipo.id_tipo_evento
    return None


def columnas_por_tipo_evento(
    definicion: DefinicionTabla, id_tipo_evento: int | None
) -> DefinicionTabla:
    """Proyecta la definición de Eventos a las columnas aplicables a una categoría.

    Conserva siempre las columnas protegidas (cédula, nombre, registro) y, de las
    editables, solo las que la matriz de compatibilidad permite para el tipo de
    evento indicado (spec 020, S-05). Con ``id_tipo_evento`` nulo devuelve la
    definición completa (opción «Todos»).

    Args:
        definicion: Definición de la tabla de eventos.
        id_tipo_evento: Tipo de evento seleccionado, o ``None`` para todas.

    Returns:
        Una copia de la definición con las columnas y editables aplicables.
    """
    if id_tipo_evento is None:
        return definicion
    permitidos = campos_permitidos_evento(id_tipo_evento)
    editables = {columna.etiqueta: columna for columna in definicion.editables}
    columnas = tuple(
        columna
        for columna in definicion.columnas
        if columna.etiqueta not in editables or editables[columna.etiqueta].columna in permitidos
    )
    return replace(
        definicion,
        columnas=columnas,
        editables=tuple(
            columna for columna in definicion.editables if columna.columna in permitidos
        ),
    )


def filas_por_tipo_evento(
    filas: list[dict[str, object]], nombre_evento: str
) -> list[dict[str, object]]:
    """Deja solo las filas cuyo tipo de evento coincide con el nombre indicado (spec 020).

    Args:
        filas: Filas del editor (diccionarios ``etiqueta -> valor``).
        nombre_evento: Nombre del tipo de evento a conservar.

    Returns:
        Las filas cuyo valor en la columna ``Evento`` coincide con el nombre.
    """
    if not nombre_evento:
        return list(filas)
    return [fila for fila in filas if str(fila.get(ETIQUETA_EVENTO, "")).strip() == nombre_evento]


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


def _config_editable(
    columna: ColumnaEditable,
    opciones_evento: list[str],
    opciones_fuente: list[str],
    opciones_descripcion: list[str],
) -> Any:
    """Construye la configuración de una columna editable del editor.

    Args:
        columna: Metadatos de la columna editable.
        opciones_evento: Nombres de los tipos de evento del catálogo.
        opciones_fuente: Fuentes oficiales de ``dim_detalle_comportamiento``.
        opciones_descripcion: Descripciones oficiales del catálogo.

    Returns:
        La configuración de la columna para ``st.data_editor``.
    """
    if columna.tipo == TIPO_EDICION_EVENTO:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=opciones_evento)
    if columna.tipo == TIPO_EDICION_GENERO:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=list(GENEROS_VALIDOS))
    if columna.tipo == TIPO_EDICION_LICENCIA:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=list(OPCIONES_LICENCIA))
    if columna.tipo == TIPO_EDICION_FUENTE:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=opciones_fuente)
    if columna.tipo == TIPO_EDICION_DESCRIPCION:
        return st.column_config.SelectboxColumn(columna.etiqueta, options=opciones_descripcion)
    if columna.tipo in (TIPO_EDICION_CODIGO, TIPO_EDICION_ENTERO):
        return st.column_config.NumberColumn(columna.etiqueta, step=1)
    if columna.tipo == TIPO_EDICION_FECHA:
        # Las fechas se almacenan como texto ISO (``AAAA-MM-DD``) en SQLite; el
        # editor las expone como texto editable para no romper la persistencia.
        return st.column_config.TextColumn(columna.etiqueta, help="Formato AAAA-MM-DD")
    return st.column_config.TextColumn(columna.etiqueta)


def configuracion_columnas(
    definicion: DefinicionTabla,
    opciones_evento: list[str],
    opciones_fuente: list[str] | None = None,
    opciones_descripcion: list[str] | None = None,
) -> dict[str, Any]:
    """Construye el ``column_config`` del editor tipo Excel (specs 017 y 018).

    Configura ``SelectboxColumn`` para el estado (``vigente``/``anulado``), el
    tipo de evento, el género, la licencia (``C1``/``C2``/``C3``), la fuente y la
    descripción de comportamiento; además añade la casilla ``Seleccionar`` para
    las acciones en bloque (spec 018). Las columnas protegidas se marcan como
    deshabilitadas.

    Args:
        definicion: Metadatos de la tabla.
        opciones_evento: Nombres de los tipos de evento para la lista desplegable.
        opciones_fuente: Fuentes oficiales para la lista desplegable; si es
            ``None`` se usa una lista vacía.
        opciones_descripcion: Descripciones oficiales para la lista desplegable; si
            es ``None`` se usa una lista vacía.

    Returns:
        El mapa ``etiqueta -> column_config`` para ``st.data_editor``.
    """
    fuentes = opciones_fuente or []
    descripciones = opciones_descripcion or []
    editables = _editable_por_etiqueta(definicion)
    protegidas = set(columnas_protegidas(definicion))
    config: dict[str, Any] = {
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        ETIQUETA_SELECCION: st.column_config.CheckboxColumn(ETIQUETA_SELECCION),
    }
    for columna in definicion.columnas:
        if columna.etiqueta in editables:
            config[columna.etiqueta] = _config_editable(
                editables[columna.etiqueta], opciones_evento, fuentes, descripciones
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
    repositorio: ConfiguracionFacade,
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
        CampoIncompatibleError,
        ValorInvalidoError,
    ) as error:
        _guardar_mensaje(definicion, "error", f"⛔ {error}")
    st.rerun()


def _procesar_bloque(
    repositorio: ConfiguracionFacade,
    definicion: DefinicionTabla,
    ids: list[int],
    vigencia: int | None,
    rol: str,
    usuario: str,
) -> None:
    """Aplica una acción en bloque a las filas seleccionadas (spec 018).

    Marca la vigencia destino de todos los IDs o, cuando ``vigencia`` es ``None``,
    los elimina físicamente (solo Super Administrador y sin hijos dependientes).

    Args:
        repositorio: Repositorio de tablas inyectado.
        definicion: Metadatos de la tabla en curso.
        ids: Identificadores de las filas seleccionadas.
        vigencia: Vigencia destino; ``None`` solicita la eliminación física.
        rol: Rol del usuario (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
    """
    if not ids:
        _guardar_mensaje(definicion, "info", MENSAJE_SIN_SELECCION)
        st.rerun()
    if vigencia is None:
        if not puede_eliminar(rol):
            _guardar_mensaje(definicion, "error", ERROR_ELIMINAR_SIN_PERMISO)
            st.rerun()
        try:
            borrados = repositorio.eliminar_registros_tabla(definicion.clave, ids, usuario)
            _guardar_mensaje(definicion, "success", f"🗑️ {borrados} registro(s) eliminado(s).")
        except DependenciaRegistroError as error:
            _guardar_mensaje(definicion, "error", f"⛔ {error}")
        st.rerun()
    try:
        afectados = repositorio.mutar_vigencia(definicion.clave, ids, vigencia, usuario)
        estado = "vigente(s)" if vigencia == VIGENCIA_ACTIVA else "anulado(s)"
        _guardar_mensaje(definicion, "success", f"✅ {afectados} registro(s) marcado(s) {estado}.")
    except (DependenciaRegistroError, ValorInvalidoError) as error:
        _guardar_mensaje(definicion, "error", f"⛔ {error}")
    st.rerun()


def _render_encabezado() -> None:
    """Pinta la ayuda del módulo."""
    st.markdown(
        "Busca con la barra **🔍 Filtrar tabla** y edita como en una hoja de "
        "cálculo: las celdas con lista desplegable solo aceptan valores del "
        "catálogo, las llaves primarias y fechas de auditoría son de solo lectura y "
        "al final debes pulsar **Guardar Cambios**. Para las acciones en bloque, "
        "marca la casilla **Seleccionar** de una o varias filas y usa los botones "
        "**Marcar Vigente**, **Marcar Anulado** o **Eliminar**. La eliminación se "
        "bloquea si el registro tiene eventos o comportamientos dependientes."
    )


def _render_tabla(
    repositorio: ConfiguracionFacade,
    definicion: DefinicionTabla,
    rol: str,
    usuario: str,
    tipos_evento: list[TipoEventoInfo],
    opciones_fuente: list[str],
    opciones_descripcion: list[str],
) -> None:
    """Renderiza una sub-pestaña: filtros, editor Excel y acciones en bloque.

    En la sub-pestaña Eventos añade un selector de categoría que proyecta las
    columnas visibles y editables a las aplicables al tipo elegido, y deja solo
    los eventos de esa categoría (spec 020, S-05).

    Args:
        repositorio: Repositorio de tablas inyectado desde el punto de entrada.
        definicion: Metadatos de la tabla a mostrar.
        rol: Rol del usuario de la sesión (controla la eliminación).
        usuario: Usuario de la sesión (para auditoría).
        tipos_evento: Tipos de evento del catálogo (identificador y nombre).
        opciones_fuente: Fuentes oficiales para la lista desplegable.
        opciones_descripcion: Descripciones oficiales para la lista desplegable.
    """
    _render_mensaje(definicion)
    opciones_tipo_evento = opciones_evento([tipo.nombre_evento for tipo in tipos_evento])
    nombre_tipo = ""
    id_tipo: int | None = None
    if definicion.clave == CLAVE_TABLA_EVENTOS:
        seleccion = st.selectbox(
            ETIQUETA_TIPO_EVENTO,
            [OPCION_TODOS_EVENTOS, *opciones_tipo_evento],
            key=f"{PREFIJO_CLAVE_FILTRO}tipo_{definicion.clave}",
        )
        if seleccion == OPCION_TODOS_EVENTOS:
            st.caption(MENSAJE_RESTRICCIONES_EVENTO)
        else:
            nombre_tipo = seleccion
            id_tipo = id_tipo_evento_por_nombre(tipos_evento, nombre_tipo)
        definicion = columnas_por_tipo_evento(definicion, id_tipo)

    registros = (
        repositorio.listar_registros(definicion.clave, id_tipo_evento=id_tipo)
        if definicion.clave == CLAVE_TABLA_EVENTOS
        else repositorio.listar_registros(definicion.clave)
    )
    if not registros:
        st.info(f"No hay registros en {definicion.etiqueta.lower()}.")
        return

    termino = st.text_input(
        ETIQUETA_FILTRO,
        placeholder=PLACEHOLDER_FILTRO,
        key=f"{PREFIJO_CLAVE_FILTRO}{definicion.clave}",
    )
    filas = filtrar_filas(filas_editor(definicion, registros), termino)
    if nombre_tipo:
        filas = filas_por_tipo_evento(filas, nombre_tipo)
    if not filas:
        st.warning(MENSAJE_SIN_COINCIDENCIAS)
        return

    original = filas_con_seleccion(filas)
    editor = st.data_editor(
        original,
        key=f"{PREFIJO_CLAVE_TABLA}{definicion.clave}",
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        column_config=configuracion_columnas(
            definicion, opciones_tipo_evento, opciones_fuente, opciones_descripcion
        ),
        disabled=columnas_protegidas(definicion),
    )
    seleccionados = ids_seleccionados(_como_filas(editor))

    col_vigente, col_anulado, col_eliminar = st.columns(3)
    with col_vigente:
        if st.button(
            ETIQUETA_VIGENTE_BLOQUE,
            key=f"{PREFIJO_CLAVE_BLOQUE}vig_{definicion.clave}",
        ):
            _procesar_bloque(repositorio, definicion, seleccionados, VIGENCIA_ACTIVA, rol, usuario)
    with col_anulado:
        if st.button(
            ETIQUETA_ANULADO_BLOQUE,
            key=f"{PREFIJO_CLAVE_BLOQUE}anu_{definicion.clave}",
        ):
            _procesar_bloque(repositorio, definicion, seleccionados, VIGENCIA_ANULADA, rol, usuario)
    with col_eliminar:
        if st.button(
            ETIQUETA_ELIMINAR_BLOQUE,
            key=f"{PREFIJO_CLAVE_BLOQUE}eli_{definicion.clave}",
            disabled=not puede_eliminar(rol),
        ):
            _procesar_bloque(repositorio, definicion, seleccionados, None, rol, usuario)

    st.divider()
    if st.button(
        ETIQUETA_GUARDAR,
        key=f"{PREFIJO_CLAVE_BOTON}{definicion.clave}",
    ):
        _procesar_guardado(repositorio, definicion, original, editor, rol, usuario)
    if not puede_eliminar(rol):
        st.caption(f"🔒 {MENSAJE_DISPONIBLE}")


def render_correccion_registros(repositorio: ConfiguracionFacade | None = None) -> None:
    """Renderiza la pestaña completa de corrección de registros.

    Args:
        repositorio: Repositorio de tablas a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las pruebas.
    """
    repositorio = repositorio or ConfiguracionFacade()
    rol = st.session_state.get("rol", "")
    usuario = st.session_state.get("usuario", "")
    tipos_evento = repositorio.listar_tipos_evento()
    opciones_fuente = repositorio.listar_fuentes_comportamiento()
    opciones_descripcion = repositorio.listar_descripciones_comportamiento()

    _render_encabezado()
    pestanas = st.tabs([definicion.etiqueta for definicion in TABLAS_CORRECCION])
    for pestana, definicion in zip(pestanas, TABLAS_CORRECCION, strict=True):
        with pestana:
            _render_tabla(
                repositorio,
                definicion,
                rol,
                usuario,
                tipos_evento,
                opciones_fuente,
                opciones_descripcion,
            )


__all__ = [
    "ETIQUETA_ANULADO_BLOQUE",
    "ETIQUETA_ELIMINAR_BLOQUE",
    "ETIQUETA_FILTRO",
    "ETIQUETA_GUARDAR",
    "ETIQUETA_SELECCION",
    "ETIQUETA_TIPO_EVENTO",
    "ETIQUETA_VIGENTE_BLOQUE",
    "MENSAJE_RESTRICCIONES_EVENTO",
    "OPCION_TODOS_EVENTOS",
    "PLACEHOLDER_FILTRO",
    "columnas_por_tipo_evento",
    "columnas_protegidas",
    "configuracion_columnas",
    "detectar_cambios",
    "filas_con_seleccion",
    "filas_editor",
    "filas_por_tipo_evento",
    "filtrar_filas",
    "id_tipo_evento_por_nombre",
    "ids_eliminados",
    "ids_seleccionados",
    "opciones_evento",
    "puede_eliminar",
    "render_correccion_registros",
]
