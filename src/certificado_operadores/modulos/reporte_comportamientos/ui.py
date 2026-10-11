"""Interfaz Streamlit del reporte de comportamientos (spec 009).

Capa de presentación pura: busca al operador, captura el registro individual,
procesa la carga masiva desde Excel y muestra el reporte de reincidencia.
Delega **todo** el acceso a datos (consultas y mutaciones) en
:class:`~certificado_operadores.facade_comportamientos.ComportamientosFacade`.
No contiene sentencias de base de datos ni conoce el motor ni el esquema.

También expone funciones puras (limpieza de celdas, validación de plantillas y
construcción de archivos Excel) para poder verificarlas sin Streamlit.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import io
import sys
from collections.abc import Hashable
from dataclasses import asdict
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

from certificado_operadores.facade_comportamientos import (  # noqa: E402
    AccionReincidencia,
    ComportamientosFacade,
    DatosComportamiento,
    DetalleComportamientoInfo,
    DetalleReincidenciaInfo,
    ReincidenciaInfo,
)

TITULO = "Reporte de Comportamientos"
"""Título de la vista del reporte de comportamientos."""

USUARIO_POR_DEFECTO = "Usuario"
"""Usuario usado cuando la sesión no expone uno."""

NOMBRE_ARCHIVO_PLANTILLA = "Plantilla_Comportamientos.xlsx"
"""Nombre del archivo Excel de plantilla de comportamientos."""

NOMBRE_ARCHIVO_PLANTILLA_ACCIONES = "Plantilla_Acciones_Reincidencia.xlsx"
"""Nombre del archivo Excel de plantilla de acciones de reincidencia."""

TIPO_MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
"""Tipo MIME de un archivo ``.xlsx``."""

HOJA_INSTRUCCIONES = "INSTRUCCIONES"
"""Nombre de la hoja de instrucciones de las plantillas."""

HOJA_DATOS = "DATOS"
"""Nombre de la hoja de datos de las plantillas."""

MENSAJE_ERROR_GENERICO = "Error"
"""Prefijo del mensaje de error al leer un Excel inválido."""

OPCIONES_DETERMINACION: tuple[str, ...] = (
    "",
    "advertencia",
    "condicionamiento",
    "suspensión",
    "cancelación",
)
"""Decisiones de Metrocali disponibles para un caso de reincidencia."""

TIPO_EVENTO_POR_DETERMINACION: dict[str, int] = {
    "advertencia": 8,
    "condicionamiento": 9,
    "suspensión": 6,
    "cancelación": 7,
}
"""Tipo de evento del historial asociado a cada determinación."""

TIPO_EVENTO_POR_ACCION: dict[str, int] = {
    "advertencia": 8,
    "condicionamiento": 9,
    "suspensión": 6,
    "suspension": 6,
    "cancelación": 7,
    "cancelacion": 7,
}
"""Tipo de evento del historial asociado a cada acción importada."""

COLUMNAS_PLANTILLA_COMPORTAMIENTO: tuple[str, ...] = (
    "id_codigo",
    "descripcion_comportamiento",
    "fecha_evento",
    "caso_bitacora_ticket",
    "nota",
    "hora_evento",
    "vehiculo",
    "viaje",
    "tarea",
    "ruta",
    "sitio_salida",
    "sitio_novedad",
    "numero_lesionados",
    "observacion_concesionario",
    "respuesta_mc",
    "responsable_pqrs_cot",
    "direccion_infraccion",
    "clase_servicio",
    "tipo_servicio",
    "fuente_infraccion",
    "placa",
)
"""Columnas de la hoja de datos de la plantilla de comportamientos."""

INSTRUCCIONES_COMPORTAMIENTO: tuple[tuple[str, str], ...] = (
    ("id_codigo", "Obligatorio. Código de operación del operador. Ej: 10001."),
    (
        "descripcion_comportamiento",
        "Obligatorio. Texto exacto de la jerarquía. El sistema asigna el id automáticamente.",
    ),
    ("fecha_evento", "Obligatorio. Formato DD/MM/AAAA o AAAA-MM-DD."),
    (
        "caso_bitacora_ticket",
        "Opcional. Número de caso/ticket. Si existe, se actualiza el registro.",
    ),
    ("nota", "Opcional. Descripción del evento."),
    ("hora_evento", "Opcional. Formato HH:MM:SS."),
    ("vehiculo", "Opcional. Número MC del vehículo."),
    ("viaje", "Opcional."),
    ("tarea", "Opcional."),
    ("ruta", "Opcional."),
    ("sitio_salida", "Opcional."),
    ("sitio_novedad", "Opcional."),
    ("numero_lesionados", "Opcional."),
    ("observacion_concesionario", "Opcional."),
    ("respuesta_mc", "Opcional."),
    ("responsable_pqrs_cot", "Opcional."),
    ("direccion_infraccion", "Opcional."),
    ("clase_servicio", "Opcional."),
    ("tipo_servicio", "Opcional."),
    ("fuente_infraccion", "Opcional."),
    ("placa", "Opcional."),
)
"""Filas de la hoja de instrucciones de la plantilla de comportamientos."""

COLUMNAS_PLANTILLA_ACCIONES: tuple[str, ...] = (
    "id_reincidencia",
    "id_codigo",
    "accion",
    "fecha_observacion",
    "observacion",
)
"""Columnas de la hoja de datos de la plantilla de acciones."""

INSTRUCCIONES_ACCIONES: tuple[tuple[str, str], ...] = (
    ("id_reincidencia", "Obligatorio. ID del caso de reincidencia."),
    ("id_codigo", "Obligatorio. Código del operador."),
    ("accion", "Obligatorio: advertencia, condicionamiento, suspensión o cancelación."),
    ("fecha_observacion", "Obligatorio. Formato AAAA-MM-DD."),
    ("observacion", "Opcional. Descripción de la acción."),
)
"""Filas de la hoja de instrucciones de la plantilla de acciones."""


# --- Funciones puras de apoyo ------------------------------------------------
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


def opciones_detalle(detalles: list[DetalleComportamientoInfo]) -> dict[str, str]:
    """Construye el mapa de opciones del selector de comportamientos.

    Args:
        detalles: Detalles de comportamiento devueltos por el repositorio.

    Returns:
        Un mapa ``{str(id_jerarquia): descripción}``.
    """
    return {str(detalle.id_jerarquia): detalle.descripcion for detalle in detalles}


def texto_celda(valor: object) -> str | None:
    """Normaliza una celda de Excel a texto sin espacios sobrantes.

    Args:
        valor: Valor leído de una fila del Excel.

    Returns:
        El texto limpio, o ``None`` si la celda está vacía.
    """
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def entero_celda(valor: object) -> int | None:
    """Convierte una celda de Excel en entero, admitiendo decimales.

    Args:
        valor: Valor leído de una fila del Excel.

    Returns:
        El entero resultante, o ``None`` si la celda está vacía o es inválida.
    """
    if valor is None or pd.isna(valor):
        return None
    try:
        return int(float(str(valor)))
    except (TypeError, ValueError):
        return None


def fecha_celda(valor: object) -> date | None:
    """Convierte una celda de Excel en ``datetime.date``.

    Args:
        valor: Valor leído de una fila del Excel.

    Returns:
        La fecha interpretada, o ``None`` si la celda está vacía o es inválida.
    """
    if valor is None or pd.isna(valor):
        return None
    interpretada = pd.to_datetime(str(valor), dayfirst=False, errors="coerce")
    if pd.isna(interpretada):
        return None
    return interpretada.date()


def fecha_texto(valor: object) -> str | None:
    """Formatea una celda de fecha como texto ``YYYY-MM-DD``.

    Args:
        valor: Valor leído de una fila del Excel.

    Returns:
        La fecha formateada, o ``None`` si la celda está vacía o es inválida.
    """
    fecha = fecha_celda(valor)
    return fecha.isoformat() if fecha is not None else None


def _como_date(valor: object) -> date | None:
    """Normaliza un valor de fecha (texto ISO o ``date``) a ``datetime.date``.

    Args:
        valor: Valor crudo de fecha proveniente de la base de datos.

    Returns:
        La fecha interpretada, o ``None`` si no es válida.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or pd.isna(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError:
        return None


def construir_plantilla_comportamiento() -> bytes:
    """Construye la plantilla de carga masiva de comportamientos en memoria.

    Returns:
        El contenido binario del archivo ``.xlsx`` de la plantilla.
    """
    df_instrucciones = pd.DataFrame(INSTRUCCIONES_COMPORTAMIENTO, columns=["Campo", "Instrucción"])
    df_datos = pd.DataFrame(columns=list(COLUMNAS_PLANTILLA_COMPORTAMIENTO))
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        df_instrucciones.to_excel(escritor, index=False, sheet_name=HOJA_INSTRUCCIONES)
        df_datos.to_excel(escritor, index=False, sheet_name=HOJA_DATOS)
    return salida.getvalue()


def construir_plantilla_acciones() -> bytes:
    """Construye la plantilla de importación de acciones en memoria.

    Returns:
        El contenido binario del archivo ``.xlsx`` de la plantilla.
    """
    df_instrucciones = pd.DataFrame(INSTRUCCIONES_ACCIONES, columns=["Campo", "Instrucción"])
    df_datos = pd.DataFrame(columns=list(COLUMNAS_PLANTILLA_ACCIONES))
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        df_instrucciones.to_excel(escritor, index=False, sheet_name=HOJA_INSTRUCCIONES)
        df_datos.to_excel(escritor, index=False, sheet_name=HOJA_DATOS)
    return salida.getvalue()


def filas_reincidencias(casos: list[ReincidenciaInfo]) -> list[dict[str, object]]:
    """Convierte los casos de reincidencia en filas tabulables.

    Args:
        casos: Casos devueltos por el repositorio.

    Returns:
        Una lista de diccionarios lista para un ``DataFrame``.
    """
    return [asdict(caso) for caso in casos]


def filas_detalle_reincidencias(
    detalles: list[DetalleReincidenciaInfo],
) -> list[dict[str, object]]:
    """Convierte el detalle de reincidencia en filas tabulables.

    Args:
        detalles: Detalles devueltos por el repositorio.

    Returns:
        Una lista de diccionarios lista para un ``DataFrame``.
    """
    return [asdict(detalle) for detalle in detalles]


# --- Render: registro individual (RF-01) -------------------------------------
def _render_individual(repositorio: ComportamientosFacade, usuario: str) -> None:
    """Renderiza y procesa el registro individual de comportamientos (RF-01).

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown("Busca un operador por **Cédula** o **Código** para registrarle un comportamiento.")
    busqueda_str = st.text_input("Buscar por Cédula o Código", key="busqueda_comp").strip()
    busqueda = parsear_entero(busqueda_str)
    if busqueda is None:
        return

    if es_codigo_operacion(str(busqueda)):
        operador = repositorio.buscar_operador_por_codigo(busqueda)
        if operador is None:
            st.error("❌ No se encontró código activo.")
            st.stop()
    else:
        operador = repositorio.buscar_operador_por_cedula(busqueda)
        if operador is None:
            st.error("❌ El operador no tiene código activo.")
            st.stop()

    st.info(
        f"👤 **Operador:** {operador.nombre_completo()} | "
        f"**Cédula:** {operador.cedula} | **Código:** {operador.id_codigo}"
    )
    st.subheader("1. Seleccionar Comportamiento")
    desc_opts = opciones_detalle(repositorio.listar_detalles_comportamiento())
    desc_sel = st.selectbox(
        "Comportamiento",
        list(desc_opts.keys()),
        format_func=lambda opcion: desc_opts[opcion],
        key="desc_comp",
    )
    jerarquia_id = int(desc_sel) if desc_sel else None
    if not jerarquia_id:
        return

    st.caption(f"Seleccionado: {desc_opts[desc_sel]}")
    with st.form("form_comportamiento"):
        st.subheader("2. Detalles del Evento")
        col1, col2 = st.columns(2)
        with col1:
            f_evento = st.date_input("Fecha del Evento", value=None)
            h_evento = st.time_input("Hora del Evento", value=None)
            vehiculo = st.number_input(
                "Vehículo (MC)", min_value=0, step=1, value=None, key="vehiculo_comp"
            )
            viaje = st.number_input("Viaje", min_value=0, step=1, value=None, key="viaje_comp")
        with col2:
            tarea = st.number_input("Tarea", min_value=0, step=1, value=None, key="tarea_comp")
            ruta = st.text_input("Ruta")
            sitio_salida = st.text_input("Sitio de Salida")
            sitio_novedad = st.text_input("Sitio de Novedad")
        caso = st.text_input("Caso / Ticket / Bitácora")
        nota = st.text_area("Nota / Descripción")
        col3, col4 = st.columns(2)
        with col3:
            num_les = st.number_input(
                "Número de Lesionados", min_value=0, step=1, value=None, key="num_les_comp"
            )
            obs_conc = st.text_area("Observación Concesionario")
        with col4:
            resp_mc = st.text_area("Respuesta Metrocali")
            resp_pqrs = st.text_input("Responsable PQRS/COT")
        submit = st.form_submit_button("💾 Guardar Comportamiento")
        if submit and f_evento:
            datos = DatosComportamiento(
                id_jerarquia=jerarquia_id,
                id_codigo=operador.id_codigo,
                fecha_evento=f_evento,
                hora_evento=h_evento.strftime("%H:%M:%S") if h_evento else None,
                caso_bitacora_ticket=caso,
                nota=nota,
                vehiculo=vehiculo,
                viaje=viaje,
                tarea=tarea,
                ruta=ruta,
                sitio_salida=sitio_salida,
                sitio_novedad=sitio_novedad,
                numero_lesionados=num_les,
                observacion_concesionario=obs_conc,
                respuesta_mc=resp_mc,
                responsable_pqrs_cot=resp_pqrs,
            )
            repositorio.registrar_comportamiento(datos, usuario)
            st.success("✅ ¡Comportamiento registrado exitosamente!")
            st.balloons()


# --- Render: carga masiva (RF-02) --------------------------------------------
def _validar_fila_masiva(
    repositorio: ComportamientosFacade, indice: Hashable, fila: pd.Series, df: pd.DataFrame
) -> None:
    """Valida una fila del Excel y anota el resultado en el ``DataFrame``.

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        indice: Índice de la fila en el ``DataFrame``.
        fila: Fila leída del Excel.
        df: ``DataFrame`` que se anota con la validación y los identificadores.
    """
    cod_raw = fila.get("id_codigo")
    if pd.isna(cod_raw):
        df.at[indice, "validacion"] = " id_codigo vacío"
        return
    try:
        cod_val = int(float(cod_raw))
    except (TypeError, ValueError):
        df.at[indice, "validacion"] = " id_codigo inválido"
        return
    codigo_activo = repositorio.resolver_codigo_activo(cod_val)
    if codigo_activo is None:
        df.at[indice, "validacion"] = " Código no existe o está inactivo"
        return
    df.at[indice, "id_codigo_int"] = codigo_activo

    descripcion = fila.get("descripcion_comportamiento")
    if pd.isna(descripcion) or not str(descripcion).strip():
        df.at[indice, "validacion"] = " descripcion_comportamiento vacía"
        return
    jerarquia = repositorio.resolver_jerarquia_por_descripcion(str(descripcion).strip())
    if jerarquia is None:
        df.at[indice, "validacion"] = " descripcion_comportamiento no encontrada"
        return
    df.at[indice, "id_jerarquia_int"] = jerarquia

    if pd.isna(fila.get("fecha_evento")):
        df.at[indice, "validacion"] = " fecha_evento vacía"
        return

    caso = fila.get("caso_bitacora_ticket")
    if pd.notna(caso) and str(caso).strip():
        existente = repositorio.buscar_comportamiento_por_caso(str(caso).strip())
        if existente is not None:
            df.at[indice, "id_existente"] = existente
            df.at[indice, "validacion"] = " Ya existe - se actualizará"
            return
    df.at[indice, "validacion"] = " Nuevo"


def _datos_desde_fila(fila: pd.Series) -> DatosComportamiento:
    """Traduce una fila validada del Excel a :class:`DatosComportamiento`.

    Args:
        fila: Fila del ``DataFrame`` ya validada.

    Returns:
        Los datos del comportamiento listos para el repositorio.
    """
    id_existente = fila.get("id_existente")
    return DatosComportamiento(
        id_jerarquia=int(fila["id_jerarquia_int"]),
        id_codigo=int(fila["id_codigo_int"]),
        fecha_evento=fecha_celda(fila.get("fecha_evento")),
        # Se preserva el formato heredado de la carga masiva para la hora.
        hora_evento=fecha_texto(fila.get("hora_evento")),
        caso_bitacora_ticket=texto_celda(fila.get("caso_bitacora_ticket")),
        nota=texto_celda(fila.get("nota")),
        vehiculo=entero_celda(fila.get("vehiculo")),
        viaje=entero_celda(fila.get("viaje")),
        tarea=entero_celda(fila.get("tarea")),
        ruta=texto_celda(fila.get("ruta")),
        sitio_salida=texto_celda(fila.get("sitio_salida")),
        sitio_novedad=texto_celda(fila.get("sitio_novedad")),
        numero_lesionados=entero_celda(fila.get("numero_lesionados")),
        observacion_concesionario=texto_celda(fila.get("observacion_concesionario")),
        respuesta_mc=texto_celda(fila.get("respuesta_mc")),
        responsable_pqrs_cot=texto_celda(fila.get("responsable_pqrs_cot")),
        direccion_infraccion=texto_celda(fila.get("direccion_infraccion")),
        clase_servicio=texto_celda(fila.get("clase_servicio")),
        tipo_servicio=texto_celda(fila.get("tipo_servicio")),
        fuente_infraccion=texto_celda(fila.get("fuente_infraccion")),
        placa=texto_celda(fila.get("placa")),
        id_existente=int(id_existente) if pd.notna(id_existente) else None,
    )


def _render_masiva(repositorio: ComportamientosFacade, usuario: str) -> None:
    """Renderiza y procesa la carga masiva de comportamientos (RF-02).

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown("Descarga la plantilla, diligénciala y súbela para carga masiva.")
    st.download_button(
        "📥 Descargar Plantilla",
        data=construir_plantilla_comportamiento(),
        file_name=NOMBRE_ARCHIVO_PLANTILLA,
        mime=TIPO_MIME_EXCEL,
    )
    st.markdown("---")
    archivo = st.file_uploader("Sube el Excel diligenciado", type=["xlsx"])
    if not archivo:
        return
    try:
        df = pd.read_excel(archivo, sheet_name=HOJA_DATOS)
    except Exception as error:
        st.error(f"{MENSAJE_ERROR_GENERICO}: {error}")
        return

    st.write("🔍 Vista previa:")
    df["validacion"] = ""
    df["id_jerarquia_int"] = None
    df["id_existente"] = None
    df["id_codigo_int"] = None
    for indice, fila in df.iterrows():
        _validar_fila_masiva(repositorio, indice, fila, df)
    st.dataframe(df, use_container_width=True)

    errores = [
        valor
        for valor in df["validacion"]
        if str(valor).startswith((" id_codigo", " Código", " descripcion", " fecha"))
    ]
    dupes = [valor for valor in df["validacion"] if valor == " Ya existe - se actualizará"]
    nuevos = [valor for valor in df["validacion"] if valor == " Nuevo"]
    if errores:
        st.error(f"Corrige los errores ({len(errores)} filas) y vuelve a subir.")
        return
    if dupes:
        st.warning(
            f"Se actualizarán {len(dupes)} registros existentes (mismo caso_bitacora_ticket)."
        )
    st.info(
        f"**{len(nuevos)}** nuevos + **{len(dupes)}** actualizaciones = "
        f"**{len(nuevos) + len(dupes)}** total"
    )
    if not st.button("🚀 Procesar Carga"):
        return
    filas = [_datos_desde_fila(fila) for _, fila in df.iterrows()]
    exitosos, actualizados = repositorio.guardar_comportamientos(filas, usuario)
    st.success(f"✅ {exitosos} nuevos insertados, {actualizados} actualizados!")
    st.balloons()


# --- Render: reincidencia (RF-03) --------------------------------------------
def _render_evaluacion(repositorio: ComportamientosFacade, usuario: str) -> None:
    """Renderiza y ejecuta la evaluación de reincidencia (RF-03).

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        usuario: Usuario de la sesión (para auditoría).
    """
    if not st.button("🔎 Evaluar Reincidencia", type="primary"):
        return
    with st.spinner("Analizando comportamientos..."):
        nuevos = repositorio.generar_reincidencias(usuario)
    if nuevos:
        st.success(f"✅ {nuevos} casos de reincidencia generados!")
        st.balloons()
    else:
        st.info("No se encontraron nuevos casos de reincidencia.")


def _render_detalle_casos(repositorio: ComportamientosFacade, usuario: str) -> None:
    """Renderiza el detalle de casos, filtros y determinación (RF-03).

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown("### 📊 Detalle de Casos")
    empresas = repositorio.listar_empresas()
    emp_opts = ["Todas"] + [empresa.nombre_empresa for empresa in empresas]

    reincidencias = repositorio.listar_reincidencias()
    if not reincidencias:
        st.info("No hay casos de reincidencia registrados.")
        return

    df_reinc = pd.DataFrame(filas_reincidencias(reincidencias))

    col_emp, col_cod, col_caso, col_lim, col_exp = st.columns([2.5, 2, 2, 2, 2.5])
    with col_emp:
        emp_filtro = st.selectbox("Empresa", emp_opts, key="reinc_emp")
    with col_cod:
        codigos = sorted(df_reinc["id_codigo"].dropna().astype(int).astype(str).unique().tolist())
        cod_filtro = st.selectbox("Código", ["Todos", *codigos], key="reinc_cod")
    with col_caso:
        caso_filtro = st.selectbox(
            "Caso",
            ["Todos", *df_reinc["id_reincidencia"].astype(str).tolist()],
            key="reinc_caso",
        )
    with col_lim:
        tam_pagina = st.selectbox(
            "Por página",
            [10, 20, 50],
            index=1,
            key="reinc_tam_pag",
        )

    if caso_filtro != "Todos":
        df_reinc = df_reinc[df_reinc["id_reincidencia"].astype(str) == caso_filtro]
    if cod_filtro != "Todos":
        df_reinc = df_reinc[df_reinc["id_codigo"].astype(int).astype(str) == cod_filtro]
    if emp_filtro != "Todas":
        df_reinc = df_reinc[df_reinc["nombre_empresa"] == emp_filtro]

    df_detalle = pd.DataFrame(
        filas_detalle_reincidencias(repositorio.listar_detalle_reincidencias())
    )
    if not df_detalle.empty and emp_filtro != "Todas":
        df_detalle = df_detalle[df_detalle["nombre_empresa"] == emp_filtro]

    with col_exp:
        if not df_detalle.empty:
            salida = io.BytesIO()
            with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
                df_detalle.to_excel(escritor, index=False, sheet_name="Detalle Reincidencia")
            st.download_button(
                "⬇️ Exportar Excel",
                data=salida.getvalue(),
                file_name=f"reincidencia_detalle_{emp_filtro}.xlsx",
                mime=TIPO_MIME_EXCEL,
                key="export_reinc",
                use_container_width=True,
            )

    total_casos = len(df_reinc)
    total_paginas = max(1, (total_casos + tam_pagina - 1) // tam_pagina)
    pagina_actual = st.session_state.get("reinc_pagina_actual", 1)
    if pagina_actual > total_paginas:
        pagina_actual = total_paginas
        st.session_state["reinc_pagina_actual"] = pagina_actual

    col_info, col_ant, col_pag, col_sig = st.columns([4, 1.2, 2, 1.2])
    with col_info:
        inicio = (pagina_actual - 1) * tam_pagina + 1 if total_casos > 0 else 0
        fin = min(pagina_actual * tam_pagina, total_casos)
        st.caption(
            f"**{total_casos} casos** | Mostrando {inicio}-{fin} "
            f"(Página {pagina_actual} de {total_paginas})"
        )
    with col_ant:
        if st.button(
            "⬅️ Anterior",
            disabled=(pagina_actual <= 1),
            key="btn_reinc_ant",
            use_container_width=True,
        ):
            st.session_state["reinc_pagina_actual"] = pagina_actual - 1
            st.rerun()
    with col_pag:
        st.markdown(
            f"<p style='text-align: center; margin-top: 8px; font-weight: bold;'>"
            f"Página {pagina_actual} / {total_paginas}</p>",
            unsafe_allow_html=True,
        )
    with col_sig:
        if st.button(
            "Siguiente ➡️",
            disabled=(pagina_actual >= total_paginas),
            key="btn_reinc_sig",
            use_container_width=True,
        ):
            st.session_state["reinc_pagina_actual"] = pagina_actual + 1
            st.rerun()

    filas_pagina = df_reinc.iloc[(pagina_actual - 1) * tam_pagina : pagina_actual * tam_pagina]
    for _, rw in filas_pagina.iterrows():
        _render_caso(rw, df_detalle, usuario, repositorio)


def _render_caso(
    rw: pd.Series, df_detalle: pd.DataFrame, usuario: str, repositorio: ComportamientosFacade
) -> None:
    """Renderiza un caso de reincidencia con su determinación y acción.

    Args:
        rw: Fila del caso seleccionado.
        df_detalle: Detalle completo de hechos de todos los casos.
        usuario: Usuario de la sesión (para auditoría).
        repositorio: Repositorio de comportamientos inyectado.
    """
    rid = int(rw["id_reincidencia"])
    etiqueta = (
        f"Reincidencia #{rid} | Cod:{rw['id_codigo']} | {rw['impacto']} | {rw['comportamiento']}"
    )
    with st.expander(etiqueta):
        col_det, col_def = st.columns([2, 1])
        det_caso = (
            df_detalle[df_detalle["id_reincidencia"] == rid] if not df_detalle.empty else None
        )
        with col_det:
            if det_caso is not None and not det_caso.empty:
                columnas = [
                    "descripcion_comportamiento",
                    "caso_bitacora_ticket",
                    "fecha_evento",
                    "vehiculo",
                    "viaje",
                    "tarea",
                    "hora_evento",
                    "ruta",
                    "clase_servicio",
                    "tipo_servicio",
                    "fuente_infraccion",
                    "placa",
                ]
                st.dataframe(det_caso[columnas], use_container_width=True, hide_index=True)
        with col_def:
            st.markdown("**Determinación Metrocali**")
            actual = rw["determinacion_mc"] if pd.notna(rw["determinacion_mc"]) else ""
            indice = (
                OPCIONES_DETERMINACION.index(actual.lower())
                if actual and actual.lower() in OPCIONES_DETERMINACION
                else 0
            )
            nueva_det = st.selectbox(
                "Decisión", list(OPCIONES_DETERMINACION), index=indice, key=f"det_mc_{rid}"
            )
            if nueva_det and nueva_det != actual.lower():
                repositorio.actualizar_determinacion(rid, nueva_det, usuario)
                st.rerun()
            if nueva_det:
                _render_accion_caso(rid, rw, det_caso, nueva_det, usuario, repositorio)


def _render_accion_caso(
    rid: int,
    rw: pd.Series,
    det_caso: pd.DataFrame | None,
    nueva_det: str,
    usuario: str,
    repositorio: ComportamientosFacade,
) -> None:
    """Renderiza y registra la acción del caso en el historial del operador.

    Args:
        rid: Identificador del caso.
        rw: Fila del caso seleccionado.
        det_caso: Detalle de hechos del caso (puede estar vacío).
        nueva_det: Determinación seleccionada.
        usuario: Usuario de la sesión (para auditoría).
        repositorio: Repositorio de comportamientos inyectado.
    """
    fecha_defecto = (
        _como_date(rw["fecha_fin"]) if pd.notna(rw["fecha_fin"]) else date.today()
    ) or date.today()
    fecha_acc = st.date_input("Fecha de la Acción", value=fecha_defecto, key=f"fecha_acc_{rid}")
    st.markdown("**Comportamientos del caso (se registrarán):**")
    if det_caso is not None and not det_caso.empty:
        descripciones = "; ".join(
            f"{fila['descripcion_comportamiento']} (caso {fila['caso_bitacora_ticket']})"
            for _, fila in det_caso.iterrows()
        )
        st.caption(f"{len(det_caso)} comportamiento(s): {descripciones}")
    else:
        descripciones = ""
    evt_existente = int(rw["id_hecho_evento"]) if pd.notna(rw["id_hecho_evento"]) else None
    if evt_existente:
        st.warning(
            f"⚠️ Ya existe una acción registrada (evento #{evt_existente}). "
            "Al guardar se **REEMPLAZARÁ** ese evento en el historial."
        )
        etiqueta_boton = "🔄 Actualizar Acción en Historial"
    else:
        etiqueta_boton = "📝 Registrar Acción en Historial"
    if not st.button(etiqueta_boton, key=f"btn_acc_{rid}"):
        return
    observacion = f"{nueva_det.capitalize()} por reincidencia #{rid}: {descripciones}"
    accion = AccionReincidencia(
        id_reincidencia=rid,
        id_codigo=int(rw["id_codigo"]),
        id_tipo_evento=TIPO_EVENTO_POR_DETERMINACION[nueva_det],
        fecha_observacion=fecha_acc,
        observacion=observacion,
        id_hecho_evento=evt_existente,
    )
    repositorio.registrar_accion_reincidencia(accion, usuario)
    st.success(f"Acción '{nueva_det}' guardada en el historial del operador {rw['id_codigo']}.")
    st.rerun()


def _render_importar_acciones(repositorio: ComportamientosFacade, usuario: str) -> None:
    """Renderiza y procesa la importación de acciones desde Excel (RF-03).

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        usuario: Usuario de la sesión (para auditoría).
    """
    st.markdown("### 📥 Importar Acciones (Excel)")
    st.download_button(
        "⬇️ Descargar Plantilla de Acciones",
        data=construir_plantilla_acciones(),
        file_name=NOMBRE_ARCHIVO_PLANTILLA_ACCIONES,
        mime=TIPO_MIME_EXCEL,
        key="dl_plant_acciones",
    )
    archivo = st.file_uploader("Sube el Excel de acciones", type=["xlsx"], key="up_acciones")
    if not archivo:
        return
    try:
        df = pd.read_excel(archivo, sheet_name=HOJA_DATOS)
    except Exception as error:
        st.error(f"{MENSAJE_ERROR_GENERICO}: {error}")
        return

    st.write("🔍 Vista previa:")
    df["validacion"] = ""
    df["id_hecho_existente"] = None
    for indice, fila in df.iterrows():
        _validar_fila_accion(repositorio, indice, fila, df)
    st.dataframe(df, use_container_width=True)

    if any(
        str(valor).startswith(("id_", "Acción", "Falta", "Reincidencia"))
        for valor in df["validacion"]
    ):
        st.error("Corrige los errores y vuelve a subir.")
        return
    n_nuevos = sum(1 for valor in df["validacion"] if valor == "Nuevo")
    n_reemplazos = sum(1 for valor in df["validacion"] if valor == "Reemplazará acción existente")
    st.info(f"**{n_nuevos}** nuevos + **{n_reemplazos}** reemplazarán acciones existentes")
    if n_reemplazos:
        st.warning(
            f"⚠️ {n_reemplazos} acción(es) ya registrada(s) se **REEMPLAZARÁN** en el historial."
        )
    if not st.button("🚀 Procesar Acciones", key="btn_proc_acc"):
        return
    acciones = [_accion_desde_fila(fila) for _, fila in df.iterrows()]
    insertados, actualizados = repositorio.importar_acciones_reincidencia(acciones, usuario)
    st.success(f"✅ {insertados} nuevas + {actualizados} actualizadas en el historial!")
    st.balloons()


def _validar_fila_accion(
    repositorio: ComportamientosFacade, indice: Hashable, fila: pd.Series, df: pd.DataFrame
) -> None:
    """Valida una fila de acción y anota el resultado en el ``DataFrame``.

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        indice: Índice de la fila en el ``DataFrame``.
        fila: Fila leída del Excel.
        df: ``DataFrame`` que se anota con la validación y el evento existente.
    """
    rid_raw = fila.get("id_reincidencia")
    if pd.isna(rid_raw):
        df.at[indice, "validacion"] = "id_reincidencia vacío"
        return
    try:
        rid = int(float(rid_raw))
    except (TypeError, ValueError):
        df.at[indice, "validacion"] = "id_reincidencia inválido"
        return
    reincidencia = repositorio.obtener_reincidencia_accion(rid)
    if reincidencia is None:
        df.at[indice, "validacion"] = "Reincidencia no existe"
        return
    cod = fila.get("id_codigo")
    if pd.isna(cod) or int(float(cod)) != int(reincidencia.id_codigo):
        df.at[indice, "validacion"] = "id_codigo no coincide con la reincidencia"
        return
    accion = str(fila.get("accion")).strip().lower() if pd.notna(fila.get("accion")) else ""
    if accion not in TIPO_EVENTO_POR_ACCION:
        df.at[indice, "validacion"] = "Acción inválida"
        return
    if pd.isna(fila.get("fecha_observacion")):
        df.at[indice, "validacion"] = "Falta fecha"
        return
    if reincidencia.id_hecho_evento is not None:
        df.at[indice, "id_hecho_existente"] = reincidencia.id_hecho_evento
        df.at[indice, "validacion"] = "Reemplazará acción existente"
    else:
        df.at[indice, "validacion"] = "Nuevo"


def _accion_desde_fila(fila: pd.Series) -> AccionReincidencia:
    """Traduce una fila validada de acción a :class:`AccionReincidencia`.

    Args:
        fila: Fila del ``DataFrame`` ya validada.

    Returns:
        La acción lista para el repositorio.
    """
    accion = str(fila["accion"]).strip().lower()
    fecha = fecha_celda(fila["fecha_observacion"]) or date.today()
    observacion = texto_celda(fila.get("observacion")) or f"{accion.capitalize()} importada"
    existente = fila.get("id_hecho_existente")
    return AccionReincidencia(
        id_reincidencia=int(float(fila["id_reincidencia"])),
        id_codigo=int(float(fila["id_codigo"])),
        id_tipo_evento=TIPO_EVENTO_POR_ACCION[accion],
        fecha_observacion=fecha,
        observacion=observacion,
        id_hecho_evento=int(existente) if pd.notna(existente) else None,
    )


def _render_reincidencia(repositorio: ComportamientosFacade, usuario: str) -> None:
    """Renderiza la pestaña completa de reincidencia (RF-03).

    Args:
        repositorio: Repositorio de comportamientos inyectado.
        usuario: Usuario de la sesión (para auditoría).
    """
    col_tit, col_btn = st.columns([3, 1])
    with col_tit:
        st.markdown("### 🔁 Reincidencia de Comportamientos")
        st.caption(
            "Evalúa si un operador ha incurrido en comportamientos reincidentes "
            "según las reglas de impacto."
        )
    with col_btn:
        _render_evaluacion(repositorio, usuario)

    with st.expander("📥 Importar Acciones desde Excel (opcional)", expanded=False):
        _render_importar_acciones(repositorio, usuario)

    st.markdown("---")
    _render_detalle_casos(repositorio, usuario)


def render_reporte_comportamientos(repositorio: ComportamientosFacade | None = None) -> None:
    """Renderiza la pestaña completa del reporte de comportamientos (spec 009).

    Args:
        repositorio: Repositorio de comportamientos a usar. Si es ``None`` se
            construye uno con la configuración por defecto; inyectarlo facilita
            las pruebas.
    """
    repositorio = repositorio or ComportamientosFacade()
    usuario = st.session_state.get("usuario", USUARIO_POR_DEFECTO)
    st.title(TITULO)
    st.markdown(
        "<style>input[type=number]::-webkit-outer-spin-button,"
        "input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}"
        "input[type=number]{-moz-appearance:textfield}</style>",
        unsafe_allow_html=True,
    )
    tab_manual, tab_masiva, tab_reinc = st.tabs(
        ["Ingreso Individual", "Carga Masiva (Excel)", "Reincidencia"]
    )
    with tab_manual:
        _render_individual(repositorio, usuario)
    with tab_masiva:
        _render_masiva(repositorio, usuario)
    with tab_reinc:
        _render_reincidencia(repositorio, usuario)


__all__ = [
    "COLUMNAS_PLANTILLA_ACCIONES",
    "COLUMNAS_PLANTILLA_COMPORTAMIENTO",
    "HOJA_DATOS",
    "HOJA_INSTRUCCIONES",
    "NOMBRE_ARCHIVO_PLANTILLA",
    "NOMBRE_ARCHIVO_PLANTILLA_ACCIONES",
    "OPCIONES_DETERMINACION",
    "TIPO_EVENTO_POR_ACCION",
    "TIPO_EVENTO_POR_DETERMINACION",
    "TIPO_MIME_EXCEL",
    "TITULO",
    "USUARIO_POR_DEFECTO",
    "construir_plantilla_acciones",
    "construir_plantilla_comportamiento",
    "entero_celda",
    "es_codigo_operacion",
    "fecha_celda",
    "fecha_texto",
    "filas_detalle_reincidencias",
    "filas_reincidencias",
    "opciones_detalle",
    "parsear_entero",
    "render_reporte_comportamientos",
    "texto_celda",
]
