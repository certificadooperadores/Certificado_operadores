"""Interfaz Streamlit de gestión de certificados (spec 008).

Capa de presentación pura: busca al operador activo por cédula o código,
captura los campos de cada tipo de evento y delega **todo** el acceso a datos
(catálogos, validación de operador y registro de eventos) en
:class:`~certificado_operadores.infra.certificados_repository.CertificadosRepository`.
No contiene sentencias SQL ni conoce el motor ni el esquema.

También expone las funciones puras de validación y construcción de datos que
usa el formulario, de modo que la lógica de negocio sea verificable sin
Streamlit.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import io
import math
import sys
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

import pandas as pd
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

from certificado_operadores.infra.catalogos_repository import VehiculoInfo  # noqa: E402
from certificado_operadores.infra.certificados_repository import (  # noqa: E402
    ACCION_CARGA_MASIVA,
    TIPO_EVENTO_ADVERTENCIA,
    TIPO_EVENTO_CANCELACION,
    TIPO_EVENTO_CERTIFICACION,
    TIPO_EVENTO_CONDICIONAMIENTO,
    TIPO_EVENTO_OBSERVACION,
    TIPO_EVENTO_REACTIVACION,
    TIPO_EVENTO_RENOVACION,
    TIPO_EVENTO_RESTRICCION_MEDICA,
    TIPO_EVENTO_SUSPENSION,
    CertificadosRepository,
    DatosEvento,
)
from certificado_operadores.infra.eventos_repository import TipoEventoInfo  # noqa: E402

TITULO = "Registro de Eventos e Historial"
"""Título de la vista de gestión de certificados."""

EVALUADOR_OTRO = "➕ OTRO (Nuevo Evaluador)"  # noqa: RUF001 - emoji intencional del diseño
"""Opción del selector para registrar un evaluador que aún no existe."""

SEPARADOR_OPCION = " - "
"""Separador entre el identificador y el nombre en las opciones del selector."""

NOMBRE_ARCHIVO_PLANTILLA = "Plantilla_Eventos_Operadores.xlsx"
"""Nombre del archivo Excel de la plantilla maestra de eventos."""

TIPO_MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
"""Tipo MIME de un archivo ``.xlsx``."""

HOJA_INSTRUCCIONES = "INSTRUCCIONES"
"""Nombre de la hoja de instrucciones y evaluadores de la plantilla."""

# Una hoja por tipo de evento, con el nombre exacto que espera la carga masiva.
HOJAS_POR_EVENTO: dict[int, str] = {
    TIPO_EVENTO_CERTIFICACION: "1-Certificacion",
    TIPO_EVENTO_REACTIVACION: "2-Reactivacion",
    TIPO_EVENTO_RENOVACION: "3-Renovacion",
    TIPO_EVENTO_OBSERVACION: "4-Observacion",
    TIPO_EVENTO_RESTRICCION_MEDICA: "5-Restriccion Medica",
    TIPO_EVENTO_SUSPENSION: "6-Suspension",
    TIPO_EVENTO_CANCELACION: "7-Retiros",
    TIPO_EVENTO_ADVERTENCIA: "8-Advertencia",
    TIPO_EVENTO_CONDICIONAMIENTO: "9-Condicionamiento",
}
"""Nombre de la hoja de Excel que corresponde a cada tipo de evento."""

# Columnas esperadas en la hoja de cada tipo de evento.
COLUMNAS_POR_EVENTO: dict[int, list[str]] = {
    TIPO_EVENTO_CERTIFICACION: [
        "cedula",
        "id_vehiculo_evaluado",
        "evaluador",
        "fecha_prueba",
        "fecha_certificado",
        "observacion",
    ],
    TIPO_EVENTO_REACTIVACION: [
        "cedula",
        "fecha_certificado",
        "fecha_prueba",
        "evaluador",
        "observacion",
    ],
    TIPO_EVENTO_RENOVACION: ["cedula", "fecha_prueba", "evaluador", "observacion"],
    TIPO_EVENTO_OBSERVACION: ["cedula", "fecha_observacion", "observacion"],
    TIPO_EVENTO_RESTRICCION_MEDICA: [
        "cedula",
        "restriccion_medica",
        "elemento_de_proteccion",
        "inicio_restriccion_medica",
        "fin_restriccion_medica",
        "observacion",
    ],
    TIPO_EVENTO_SUSPENSION: ["cedula", "fecha_suspension", "observacion"],
    TIPO_EVENTO_CANCELACION: [
        "cedula",
        "fecha_retiro",
        "fecha_notificacion_retiro",
        "observacion",
    ],
    TIPO_EVENTO_ADVERTENCIA: ["cedula", "fecha_observacion", "observacion"],
    TIPO_EVENTO_CONDICIONAMIENTO: ["cedula", "fecha_observacion", "observacion"],
}
"""Columnas que espera la carga masiva en la hoja de cada tipo de evento."""

INSTRUCCIONES_PLANTILLA: tuple[tuple[str, str], ...] = (
    (
        "Cédula (Todas las hojas)",
        "Es obligatoria. Identifica al operador y aplica el evento a su código activo.",
    ),
    (
        "Evento 1 (Certificación)",
        "Requiere id_vehiculo_evaluado, evaluador, fecha_prueba, fecha_certificado.",
    ),
    ("Evento 2 (Reactivación)", "Requiere fecha_certificado, fecha_prueba, evaluador."),
    ("Evento 3 (Renovación)", "Requiere fecha_prueba, evaluador."),
    ("Evento 4 (Observación)", "Requiere fecha_observacion y observacion."),
    (
        "Evento 5 (Restricción Médica)",
        "Requiere restriccion_medica, inicio_restriccion_medica y fin_restriccion_medica.",
    ),
    ("Evento 6 (Suspensión)", "Requiere fecha_suspension."),
    (
        "Evento 7 (Cancelación / Notif. Retiro)",
        "Requiere observacion y al menos una fecha (fecha_retiro o fecha_notificacion_retiro).",
    ),
    ("Evento 8 (Advertencia)", "Requiere fecha_observacion y observacion."),
    ("Evento 9 (Condicionamiento)", "Requiere fecha_observacion y observacion."),
)
"""Filas de la hoja de instrucciones de la plantilla maestra."""

COLUMNA_EVALUADORES = "Evaluadores Históricos Disponibles"
"""Encabezado de la lista de evaluadores en la hoja de instrucciones."""

MENSAJE_SIN_EVALUADORES = "No hay registros"
"""Texto que se muestra cuando aún no hay evaluadores históricos."""

ERROR_CEDULA = "🔴 ERROR: Cédula inválida o vacía"
"""Mensaje de error para una fila sin cédula válida."""

ERROR_SIN_CODIGO = "🔴 ERROR: Cédula no tiene código activo registrado."
"""Mensaje de error para un operador sin código activo."""

ESTADO_LISTO = "Listo para procesar"
"""Estado de una fila válida lista para registrarse."""

VALIDACION_OK = "🟢 OK"
"""Marca de validación de una fila sin errores."""

MARCA_ERROR = "🔴"
"""Prefijo que identifica una fila con errores de validación."""

USUARIO_POR_DEFECTO = "Usuario"
"""Usuario usado cuando la sesión no expone uno."""


def _es_vacio(valor: object) -> bool:
    """Indica si un valor de celda está vacío (``None``, cadena o ``NaN``).

    Args:
        valor: Valor leído de un formulario o del Excel.

    Returns:
        ``True`` si el valor está ausente o vacío.
    """
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return str(valor).strip() == ""


def limpiar_texto(valor: object) -> str | None:
    """Normaliza un valor de celda a texto sin espacios sobrantes.

    Args:
        valor: Valor leído de un formulario o del Excel.

    Returns:
        El texto limpio, o ``None`` si el valor está vacío.
    """
    if _es_vacio(valor):
        return None
    return str(valor).strip()


def limpiar_entero(valor: object) -> int | None:
    """Convierte un valor de celda en entero, admitiendo decimales de Excel.

    Args:
        valor: Valor leído de un formulario o del Excel.

    Returns:
        El entero resultante, o ``None`` si el valor está vacío o es inválido.
    """
    if _es_vacio(valor):
        return None
    try:
        return int(float(str(valor)))
    except (TypeError, ValueError):
        return None


def parsear_entero(texto: str) -> int | None:
    """Convierte el texto de un campo de búsqueda en un entero.

    Args:
        texto: Contenido del campo de texto.

    Returns:
        El entero si el texto es numérico; ``None`` en caso contrario.
    """
    limpio = (texto or "").strip()
    if not limpio.isdigit():
        return None
    return int(limpio)


def es_codigo_operacion(texto: str) -> bool:
    """Indica si el texto corresponde a un código de operación (no a una cédula).

    La regla heredada: los códigos de operación tienen cinco dígitos o menos.

    Args:
        texto: Texto numérico ingresado en la búsqueda.

    Returns:
        ``True`` si el texto tiene cinco caracteres o menos.
    """
    return len(texto.strip()) <= 5


def opciones_evento(tipos: list[TipoEventoInfo]) -> list[str]:
    """Construye las opciones del selector de tipos de evento.

    Args:
        tipos: Tipos de evento devueltos por el repositorio.

    Returns:
        Una opción ``"id - nombre"`` por tipo de evento.
    """
    return [
        f"{tipo.id_tipo_evento}{SEPARADOR_OPCION}{tipo.nombre_evento.title()}" for tipo in tipos
    ]


def id_desde_opcion(opcion: str) -> int:
    """Extrae el identificador de tipo de evento de una opción del selector.

    Args:
        opcion: Opción ``"id - nombre"``.

    Returns:
        El identificador del tipo de evento.
    """
    return int(opcion.split(SEPARADOR_OPCION)[0])


def nombre_hoja(id_tipo_evento: int) -> str:
    """Devuelve la hoja de Excel que corresponde a un tipo de evento.

    Args:
        id_tipo_evento: Identificador del tipo de evento.

    Returns:
        El nombre de la hoja de la plantilla maestra.
    """
    return HOJAS_POR_EVENTO[id_tipo_evento]


def _como_fecha(valor: object) -> date | None:
    """Normaliza un valor de fecha del formulario o del Excel a ``date``.

    Args:
        valor: Valor leído de un selector de fecha, de Excel o de texto ISO.

    Returns:
        La fecha interpretada, o ``None`` si el valor no es una fecha válida.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor.strip()[:10])
        except ValueError:
            return None
    return None


def validar_evento_individual(id_tipo_evento: int, campos: Mapping[str, object]) -> list[str]:
    """Valida los campos de un evento individual según su tipo.

    Args:
        id_tipo_evento: Identificador del tipo de evento.
        campos: Valores capturados por el formulario (vehículo, evaluador,
            restricción médica, fechas y observación).

    Returns:
        La lista de mensajes de error; vacía si el evento es válido.
    """
    if id_tipo_evento == TIPO_EVENTO_CERTIFICACION and (
        campos.get("id_vehiculo_evaluado") is None or not campos.get("evaluador")
    ):
        return ["Vehículo y Evaluador son obligatorios para este evento."]
    if id_tipo_evento in (TIPO_EVENTO_REACTIVACION, TIPO_EVENTO_RENOVACION) and not campos.get(
        "evaluador"
    ):
        return ["Evaluador es obligatorio para este evento."]
    if id_tipo_evento == TIPO_EVENTO_RESTRICCION_MEDICA and not campos.get("restriccion_medica"):
        return ["Debe describir la restricción médica."]
    if (
        id_tipo_evento == TIPO_EVENTO_RESTRICCION_MEDICA
        and campos.get("fin_restriccion_medica") is None
    ):
        return ["La fecha de Fin de Restricción es obligatoria."]
    if id_tipo_evento == TIPO_EVENTO_CANCELACION and not campos.get("observacion"):
        return ["Debe escribir un motivo para la Cancelación / Retiro."]
    if (
        id_tipo_evento == TIPO_EVENTO_CANCELACION
        and campos.get("fecha_retiro") is None
        and campos.get("fecha_notificacion_retiro") is None
    ):
        return ["Debe seleccionar al menos una fecha (Retiro o Notificación)."]
    if id_tipo_evento in (
        TIPO_EVENTO_OBSERVACION,
        TIPO_EVENTO_ADVERTENCIA,
        TIPO_EVENTO_CONDICIONAMIENTO,
    ) and not campos.get("observacion"):
        return ["Debe escribir la observación."]
    if (
        id_tipo_evento
        in (TIPO_EVENTO_OBSERVACION, TIPO_EVENTO_ADVERTENCIA, TIPO_EVENTO_CONDICIONAMIENTO)
        and campos.get("fecha_observacion") is None
    ):
        return ["Debe seleccionar la fecha de la novedad."]
    return []


def validar_fila_masiva(id_tipo_evento: int, fila: Mapping[str, object]) -> str:
    """Valida los campos de una fila de carga masiva según su tipo de evento.

    Args:
        id_tipo_evento: Identificador del tipo de evento.
        fila: Fila leída del Excel.

    Returns:
        El mensaje de error, o cadena vacía si la fila es válida.
    """
    if id_tipo_evento == TIPO_EVENTO_CERTIFICACION:
        if (
            limpiar_entero(fila.get("id_vehiculo_evaluado")) is None
            or limpiar_texto(fila.get("evaluador")) is None
        ):
            return "🔴 ERROR: Vehículo evaluado y evaluador son obligatorios."
    elif id_tipo_evento in (TIPO_EVENTO_REACTIVACION, TIPO_EVENTO_RENOVACION):
        if limpiar_texto(fila.get("evaluador")) is None:
            return "🔴 ERROR: Evaluador es obligatorio."
    elif id_tipo_evento == TIPO_EVENTO_RESTRICCION_MEDICA:
        if limpiar_texto(fila.get("restriccion_medica")) is None:
            return "🔴 ERROR: Falta Descripción de Restricción."
        if _es_vacio(fila.get("fin_restriccion_medica")):
            return "🔴 ERROR: Falta Fin de Restricción."
    elif id_tipo_evento == TIPO_EVENTO_CANCELACION:
        if limpiar_texto(fila.get("observacion")) is None:
            return "🔴 ERROR: Retiro/Cancelación requiere Motivo (observación)."
        if _es_vacio(fila.get("fecha_retiro")) and _es_vacio(fila.get("fecha_notificacion_retiro")):
            return "🔴 ERROR: Debe indicar al menos una fecha (retiro o notificación)."
    elif id_tipo_evento in (
        TIPO_EVENTO_OBSERVACION,
        TIPO_EVENTO_ADVERTENCIA,
        TIPO_EVENTO_CONDICIONAMIENTO,
    ):
        if limpiar_texto(fila.get("observacion")) is None:
            return "🔴 ERROR: Observación requiere una nota."
        if _es_vacio(fila.get("fecha_observacion")):
            return "🔴 ERROR: Falta fecha_observacion."
    return ""


def construir_datos_evento(
    id_codigo: int, id_tipo_evento: int, campos: Mapping[str, object]
) -> DatosEvento:
    """Traduce los campos capturados a un :class:`DatosEvento`.

    Sirve tanto al formulario individual como a la carga masiva, ya que ambos
    usan los mismos nombres de campo.

    Args:
        id_codigo: Código de operación al que se asocia el evento.
        id_tipo_evento: Identificador del tipo de evento.
        campos: Valores capturados por el formulario o leídos del Excel.

    Returns:
        Los datos del evento listos para el repositorio.
    """
    return DatosEvento(
        id_codigo=id_codigo,
        id_tipo_evento=id_tipo_evento,
        id_vehiculo_evaluado=limpiar_entero(campos.get("id_vehiculo_evaluado")),
        evaluador=limpiar_texto(campos.get("evaluador")),
        fecha_prueba=_como_fecha(campos.get("fecha_prueba")),
        fecha_certificado=_como_fecha(campos.get("fecha_certificado")),
        fecha_retiro=_como_fecha(campos.get("fecha_retiro")),
        fecha_notificacion_retiro=_como_fecha(campos.get("fecha_notificacion_retiro")),
        fecha_suspension=_como_fecha(campos.get("fecha_suspension")),
        restriccion_medica=limpiar_texto(campos.get("restriccion_medica")),
        elemento_de_proteccion=limpiar_texto(campos.get("elemento_de_proteccion")),
        inicio_restriccion_medica=_como_fecha(campos.get("inicio_restriccion_medica")),
        fin_restriccion_medica=_como_fecha(campos.get("fin_restriccion_medica")),
        fecha_observacion=_como_fecha(campos.get("fecha_observacion")),
        observacion=limpiar_texto(campos.get("observacion")),
    )


def construir_datos_desde_fila(
    id_tipo_evento: int, id_codigo: int, fila: Mapping[str, object]
) -> DatosEvento:
    """Traduce una fila del Excel a un :class:`DatosEvento`.

    Args:
        id_tipo_evento: Identificador del tipo de evento.
        id_codigo: Código de operación resuelto para la cédula de la fila.
        fila: Fila leída del Excel.

    Returns:
        Los datos del evento listos para el repositorio.
    """
    return construir_datos_evento(id_codigo, id_tipo_evento, fila)


def construir_plantilla_eventos(evaluadores: list[str]) -> bytes:
    """Construye la plantilla maestra de eventos en memoria.

    Args:
        evaluadores: Evaluadores históricos disponibles para la hoja de ayuda.

    Returns:
        El contenido binario del archivo ``.xlsx`` de la plantilla.
    """
    if evaluadores:
        df_evaluadores = pd.DataFrame(evaluadores, columns=[COLUMNA_EVALUADORES])
    else:
        df_evaluadores = pd.DataFrame([MENSAJE_SIN_EVALUADORES], columns=[COLUMNA_EVALUADORES])

    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        pd.DataFrame(INSTRUCCIONES_PLANTILLA, columns=["Aspecto", "Instrucción"]).to_excel(
            escritor, index=False, sheet_name=HOJA_INSTRUCCIONES
        )
        df_evaluadores.to_excel(
            escritor, index=False, sheet_name=HOJA_INSTRUCCIONES, startrow=0, startcol=3
        )
        for id_tipo_evento, hoja in HOJAS_POR_EVENTO.items():
            pd.DataFrame(columns=COLUMNAS_POR_EVENTO[id_tipo_evento]).to_excel(
                escritor, index=False, sheet_name=hoja
            )
    return salida.getvalue()


def _render_encabezado() -> None:
    """Pinta el título, los estilos y la ayuda del módulo."""
    st.title(TITULO)
    st.markdown(
        "<style>input[type=number]::-webkit-outer-spin-button,"
        "input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}"
        "input[type=number]{-moz-appearance:textfield}</style>",
        unsafe_allow_html=True,
    )


def _render_individual(
    repositorio: CertificadosRepository,
    tipos: list[TipoEventoInfo],
    vehiculos: list[VehiculoInfo],
    evaluadores: list[str],
    usuario: str,
) -> None:
    """Renderiza y procesa el registro individual de eventos (RF-01 y RF-02).

    Args:
        repositorio: Repositorio de certificados inyectado.
        tipos: Tipos de evento disponibles.
        vehiculos: Vehículos evaluables.
        evaluadores: Evaluadores históricos.
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown(
        "Busca a un operador por su **Cédula** o **Código de Operación** para "
        "registrarle un evento. **El operador debe existir y tener un código activo.**"
    )
    busqueda_str = st.text_input("Buscar por Cédula o Código", key="busqueda_cert").strip()
    busqueda = parsear_entero(busqueda_str)
    if busqueda is None:
        st.info("Ingresa una cédula o un código de operación numérico para buscar.")
        return

    if es_codigo_operacion(str(busqueda)):
        operador = repositorio.buscar_operador_activo_por_codigo(busqueda)
        mensaje_ausente = "❌ No se encontró ningún operador activo con ese Código de Operación."
    else:
        operador = repositorio.buscar_operador_activo_por_cedula(busqueda)
        mensaje_ausente = (
            "❌ El operador no existe o no tiene un código activo registrado. "
            "Créalo o asígnale un código primero."
        )

    if operador is None:
        st.error(mensaje_ausente)
        st.stop()

    st.info(
        f"👤 **Operador Encontrado:** {operador.nombre_completo()} | "
        f"**Cédula:** {operador.cedula} | **Código Activo:** {operador.id_codigo}"
    )
    st.subheader("1. Seleccionar Tipo de Evento")
    opcion = st.selectbox("Evento a registrar", opciones_evento(tipos))
    id_tipo_evento = id_desde_opcion(opcion)

    with st.form("form_evento"):
        st.subheader("2. Detalles del Evento")
        campos: dict[str, object] = {
            "id_vehiculo_evaluado": None,
            "evaluador": None,
            "restriccion_medica": None,
            "fin_restriccion_medica": None,
            "fecha_retiro": None,
            "fecha_notificacion_retiro": None,
            "fecha_observacion": None,
            "observacion": None,
            "fecha_prueba": None,
            "fecha_certificado": None,
            "fecha_suspension": None,
            "elemento_de_proteccion": None,
            "inicio_restriccion_medica": None,
        }
        _render_campos_evento(id_tipo_evento, vehiculos, evaluadores, campos)
        enviado = st.form_submit_button("Guardar Evento")
        if enviado:
            errores = validar_evento_individual(id_tipo_evento, campos)
            for error in errores:
                st.error(error)
            if not errores:
                datos = construir_datos_evento(operador.id_codigo, id_tipo_evento, campos)
                repositorio.registrar_evento(datos, usuario)
                st.success("✅ ¡Evento registrado exitosamente en el historial del operador!")
                st.balloons()


def _render_campos_evento(
    id_tipo_evento: int,
    vehiculos: list[VehiculoInfo],
    evaluadores: list[str],
    campos: dict[str, object],
) -> None:
    """Pinta los campos dinámicos del formulario según el tipo de evento.

    Args:
        id_tipo_evento: Identificador del tipo de evento.
        vehiculos: Vehículos evaluables.
        evaluadores: Evaluadores históricos.
        campos: Diccionario que se completa con los valores capturados.
    """

    def _evaluador() -> None:
        opciones = [*evaluadores, EVALUADOR_OTRO]
        seleccion = st.selectbox("Evaluador Registrado", opciones, key="ev_eval", index=None)
        if seleccion == EVALUADOR_OTRO:
            campos["evaluador"] = (
                st.text_input("Escribe el nombre del Nuevo Evaluador").strip().title()
            )
        else:
            campos["evaluador"] = seleccion

    if id_tipo_evento == TIPO_EVENTO_CERTIFICACION:
        st.markdown("**Campos de Certificación**")
        col1, col2 = st.columns(2)
        with col1:
            if vehiculos:
                opciones = [
                    f"{vehiculo.id_vehiculo}{SEPARADOR_OPCION}{vehiculo.nombre_vehiculo}"
                    for vehiculo in vehiculos
                ]
                seleccion = st.selectbox("Vehículo Evaluado", opciones, index=None)
                campos["id_vehiculo_evaluado"] = id_desde_opcion(seleccion) if seleccion else None
            _evaluador()
        with col2:
            campos["fecha_prueba"] = st.date_input("Fecha de Prueba", value=None)
            campos["fecha_certificado"] = st.date_input("Fecha de Certificado", value=None)
        campos["observacion"] = st.text_area("Observación (Opcional)")
    elif id_tipo_evento == TIPO_EVENTO_REACTIVACION:
        st.markdown("**Campos de Reactivación**")
        col1, col2 = st.columns(2)
        with col1:
            _evaluador()
        with col2:
            campos["fecha_certificado"] = st.date_input("Fecha de Certificado", value=None)
            campos["fecha_prueba"] = st.date_input("Fecha de Prueba", value=None)
        campos["observacion"] = st.text_area("Observación (Opcional)")
    elif id_tipo_evento == TIPO_EVENTO_RENOVACION:
        st.markdown("**Campos de Renovación**")
        col1, col2 = st.columns(2)
        with col1:
            _evaluador()
        with col2:
            campos["fecha_prueba"] = st.date_input("Fecha de Prueba", value=None)
        campos["observacion"] = st.text_area("Observación (Opcional)")
    elif id_tipo_evento in (
        TIPO_EVENTO_OBSERVACION,
        TIPO_EVENTO_ADVERTENCIA,
        TIPO_EVENTO_CONDICIONAMIENTO,
    ):
        st.markdown("**Novedad del Operador**")
        campos["fecha_observacion"] = st.date_input("Fecha de la Novedad", value=None)
        campos["observacion"] = st.text_area("Descripción de la Observación")
    elif id_tipo_evento == TIPO_EVENTO_RESTRICCION_MEDICA:
        st.markdown("**Campos de Restricción Médica**")
        campos["restriccion_medica"] = st.text_area("Descripción de la Restricción Médica")
        campos["elemento_de_proteccion"] = st.text_input("Elemento de Protección (Opcional)")
        col3, col4 = st.columns(2)
        with col3:
            campos["inicio_restriccion_medica"] = st.date_input("Inicio de Restricción", value=None)
        with col4:
            campos["fin_restriccion_medica"] = st.date_input("Fin de Restricción", value=None)
        campos["observacion"] = st.text_area("Observación adicional (Opcional)")
    elif id_tipo_evento == TIPO_EVENTO_SUSPENSION:
        st.markdown("**Campos de Suspensión**")
        campos["fecha_suspension"] = st.date_input("Fecha de Suspensión", value=None)
        campos["observacion"] = st.text_area("Motivo / Observación (Opcional)")
    elif id_tipo_evento == TIPO_EVENTO_CANCELACION:
        st.markdown("**Campos de Retiro y Cancelación**")
        col5, col6 = st.columns(2)
        with col5:
            campos["fecha_retiro"] = st.date_input("Fecha de Retiro / Cancelación", value=None)
        with col6:
            campos["fecha_notificacion_retiro"] = st.date_input("Fecha de Notificación", value=None)
        campos["observacion"] = st.text_area("Motivo (Obligatorio)")


def _render_masiva(
    repositorio: CertificadosRepository,
    tipos: list[TipoEventoInfo],
    evaluadores: list[str],
    usuario: str,
) -> None:
    """Renderiza y procesa la carga masiva de eventos desde Excel (RF-03).

    Args:
        repositorio: Repositorio de certificados inyectado.
        tipos: Tipos de evento disponibles.
        evaluadores: Evaluadores históricos (para la plantilla).
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown(
        "Descarga la Plantilla Maestra y sube la hoja del evento que deseas cargar de forma masiva."
    )
    st.download_button(
        label="📥 Descargar Plantilla Maestra de Eventos",
        data=construir_plantilla_eventos(evaluadores),
        file_name=NOMBRE_ARCHIVO_PLANTILLA,
        mime=TIPO_MIME_EXCEL,
    )
    st.markdown("---")

    col_sel, col_up = st.columns([1, 2])
    with col_sel:
        opcion = st.selectbox("¿Qué tipo de evento vas a procesar?", opciones_evento(tipos))
        id_tipo_masivo = id_desde_opcion(opcion)
        hoja_esperada = nombre_hoja(id_tipo_masivo)
        st.info(f"El sistema leerá ÚNICAMENTE la hoja: **{hoja_esperada}**")
    with col_up:
        archivo = st.file_uploader(
            "Sube el archivo diligenciado (Excel)", type=["xlsx"], key="upload_cert"
        )

    if archivo is None:
        return
    try:
        df = pd.read_excel(archivo, sheet_name=hoja_esperada)
    except Exception as error:
        st.error(f"Error procesando el archivo: {error}")
        return

    df["Estado"] = ""
    df["Validacion"] = VALIDACION_OK
    df["codigo_interno"] = None
    for indice, fila in df.iterrows():
        cedula = limpiar_entero(fila.get("cedula"))
        if cedula is None:
            df.at[indice, "Validacion"] = ERROR_CEDULA
            continue
        operador = repositorio.buscar_operador_activo_por_cedula(cedula)
        if operador is None:
            df.at[indice, "Validacion"] = ERROR_SIN_CODIGO
            continue
        df.at[indice, "codigo_interno"] = operador.id_codigo
        df.at[indice, "Estado"] = ESTADO_LISTO
        error_fila = validar_fila_masiva(id_tipo_masivo, dict(fila))
        if error_fila:
            df.at[indice, "Validacion"] = error_fila

    st.write("🔍 **Vista Previa de los Datos Subidos:**")
    st.dataframe(df.drop(columns=["codigo_interno"]), use_container_width=True)

    if any(MARCA_ERROR in str(valor) for valor in df["Validacion"]):
        st.error("Corrige los errores marcados en rojo en tu Excel y vuelve a subir el archivo.")
        return

    st.info("💡 Haz clic en 'Procesar Carga' para inyectar estos eventos al historial.")
    if not st.button("🚀 Procesar Eventos"):
        return
    eventos = [
        construir_datos_desde_fila(id_tipo_masivo, int(fila["codigo_interno"]), dict(fila))
        for _, fila in df.iterrows()
    ]
    total = repositorio.registrar_eventos(
        eventos, usuario, ACCION_CARGA_MASIVA, f"Registros exitosos: {len(eventos)}"
    )
    st.success(f"✅ ¡Carga completada! {total} eventos procesados e inyectados.")
    st.balloons()


def render_gestion_certificados(repositorio: CertificadosRepository | None = None) -> None:
    """Renderiza la pestaña completa de gestión de certificados (spec 008).

    Args:
        repositorio: Repositorio de certificados a usar. Si es ``None`` se
            construye uno con la configuración por defecto; inyectarlo facilita
            las pruebas.
    """
    repositorio = repositorio or CertificadosRepository()
    usuario = st.session_state.get("usuario", USUARIO_POR_DEFECTO)
    tipos = repositorio.listar_tipos_evento()
    vehiculos = repositorio.listar_vehiculos()
    evaluadores = repositorio.listar_evaluadores()

    _render_encabezado()
    tab_manual, tab_masiva = st.tabs(["Ingreso Individual", "Carga Masiva (Excel)"])
    with tab_manual:
        _render_individual(repositorio, tipos, vehiculos, evaluadores, usuario)
    with tab_masiva:
        _render_masiva(repositorio, tipos, evaluadores, usuario)


__all__ = [
    "COLUMNAS_POR_EVENTO",
    "COLUMNA_EVALUADORES",
    "ESTADO_LISTO",
    "EVALUADOR_OTRO",
    "HOJAS_POR_EVENTO",
    "HOJA_INSTRUCCIONES",
    "INSTRUCCIONES_PLANTILLA",
    "NOMBRE_ARCHIVO_PLANTILLA",
    "SEPARADOR_OPCION",
    "TIPO_MIME_EXCEL",
    "TITULO",
    "USUARIO_POR_DEFECTO",
    "construir_datos_desde_fila",
    "construir_datos_evento",
    "construir_plantilla_eventos",
    "es_codigo_operacion",
    "id_desde_opcion",
    "limpiar_entero",
    "limpiar_texto",
    "nombre_hoja",
    "opciones_evento",
    "parsear_entero",
    "render_gestion_certificados",
    "validar_evento_individual",
    "validar_fila_masiva",
]
