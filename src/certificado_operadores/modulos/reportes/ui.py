"""Interfaz Streamlit de reportes y exportaciones (spec 010).

Capa de presentación pura: selecciona el reporte, captura los filtros y muestra
los resultados con sus botones de descarga. Delega **todo** el acceso a datos
(catálogos de filtros, consultas consolidadas y auditoría) en
:class:`~certificado_operadores.infra.reportes_repository.ReportesRepository` y la
generación de archivos en las funciones puras ``generar_excel``/``generar_csv``.
No contiene sentencias de base de datos ni conoce el motor ni el esquema.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from datetime import date
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

from certificado_operadores.infra.reportes_repository import (  # noqa: E402
    DIAS_VENCIMIENTO_DEFECTO,
    DIAS_VENCIMIENTO_MAXIMO,
    DIAS_VENCIMIENTO_MINIMO,
    OPCIONES_ESTADO,
    OPCIONES_ESTADO_ACTIVO,
    TIPO_MIME_CSV,
    TIPO_MIME_EXCEL,
    DefinicionReporte,
    ReportesRepository,
    SeleccionFiltros,
    generar_csv,
    generar_excel,
)

TITULO = "📊 Reportes y Exportaciones"
"""Título de la vista de reportes."""

DESCRIPCION = "Selecciona un reporte, aplica los filtros y exporta a Excel o CSV."
"""Texto introductorio de la vista."""

USUARIO_POR_DEFECTO = "Usuario"
"""Usuario usado cuando la sesión no expone uno."""

ETIQUETA_EJECUTAR = "🔍 Ejecutar Reporte"
"""Texto del botón que ejecuta el reporte."""

OPCION_TODAS = "Todas"
"""Opción sin restricción para los filtros femeninos (empresa/tipología)."""

OPCION_TODOS = "Todos"
"""Opción sin restricción para el resto de filtros de selección."""

MENSAJE_SIN_RESULTADOS = "El reporte no arrojó resultados con los filtros actuales."
"""Mensaje cuando el reporte no devuelve filas."""


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


def _construir_seleccion(
    definicion: DefinicionReporte, repositorio: ReportesRepository
) -> SeleccionFiltros:
    """Renderiza los controles de filtro y devuelve la selección tipada.

    Args:
        definicion: Reporte cuyos filtros se van a capturar.
        repositorio: Repositorio inyectado, usado para cargar las opciones.

    Returns:
        Los valores tipados seleccionados por el usuario.
    """
    empresa: int | None = None
    estado: str | None = None
    estado_activo: str | None = None
    tipologia: int | None = None
    dias_vencer: int | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    tipo_evento: int | None = None
    impacto: int | None = None
    codigo: int | None = None

    for filtro in definicion.filtros:
        tipo = filtro.tipo
        if tipo == "empresa":
            opciones = {
                f"{elemento.id_empresa} - {elemento.nombre_empresa}": elemento.id_empresa
                for elemento in repositorio.listar_empresas()
            }
            seleccion = st.selectbox(
                filtro.etiqueta,
                [OPCION_TODAS, *opciones],
                key=f"filt_emp_{definicion.id}",
            )
            empresa = opciones.get(seleccion)
        elif tipo == "estado":
            seleccion = st.selectbox(
                filtro.etiqueta,
                list(OPCIONES_ESTADO),
                index=0,
                key=f"filt_est_{definicion.id}",
            )
            estado = None if seleccion == OPCION_TODOS else seleccion
        elif tipo == "estado_activo":
            seleccion = st.selectbox(
                filtro.etiqueta,
                list(OPCIONES_ESTADO_ACTIVO),
                index=0,
                key=f"filt_estac_{definicion.id}",
            )
            estado_activo = None if seleccion == OPCION_TODOS else seleccion
        elif tipo == "tipologia":
            opciones = {
                elemento.descripcion: elemento.id_perfil_tipologia
                for elemento in repositorio.listar_tipologias()
            }
            seleccion = st.selectbox(
                filtro.etiqueta,
                [OPCION_TODAS, *opciones],
                key=f"filt_tip_{definicion.id}",
            )
            tipologia = opciones.get(seleccion)
        elif tipo == "dias_vencer":
            dias_vencer = st.slider(
                filtro.etiqueta,
                DIAS_VENCIMIENTO_MINIMO,
                DIAS_VENCIMIENTO_MAXIMO,
                int(filtro.defecto or DIAS_VENCIMIENTO_DEFECTO),
                key=f"filt_dias_{definicion.id}",
            )
        elif tipo == "fecha":
            col_desde, col_hasta = st.columns(2)
            with col_desde:
                fecha_desde = st.date_input(
                    "Desde",
                    value=date.today().replace(day=1),
                    key=f"filt_desde_{definicion.id}",
                )
            with col_hasta:
                fecha_hasta = st.date_input(
                    "Hasta",
                    value=date.today(),
                    key=f"filt_hasta_{definicion.id}",
                )
        elif tipo == "tipo_evento":
            opciones = {
                f"{elemento.id_tipo_evento} - {elemento.nombre_evento.title()}": (
                    elemento.id_tipo_evento
                )
                for elemento in repositorio.listar_tipos_evento()
            }
            seleccion = st.selectbox(
                filtro.etiqueta,
                [OPCION_TODOS, *opciones],
                key=f"filt_tev_{definicion.id}",
            )
            tipo_evento = opciones.get(seleccion)
        elif tipo == "impacto":
            opciones = {
                f"{elemento.id_impacto} - {elemento.impacto}": elemento.id_impacto
                for elemento in repositorio.listar_impactos()
            }
            seleccion = st.selectbox(
                filtro.etiqueta,
                [OPCION_TODOS, *opciones],
                key=f"filt_imp_{definicion.id}",
            )
            impacto = opciones.get(seleccion)
        elif tipo == "codigo":
            codigo = parsear_entero(st.text_input(filtro.etiqueta, key=f"filt_cod_{definicion.id}"))

    return SeleccionFiltros(
        empresa=empresa,
        estado=estado,
        estado_activo=estado_activo,
        tipologia=tipologia,
        dias_vencer=dias_vencer,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo_evento=tipo_evento,
        impacto=impacto,
        codigo=codigo,
    )


def _render_resultado(
    df: pd.DataFrame | None,
    definicion: DefinicionReporte,
    repositorio: ReportesRepository,
    usuario: str,
) -> None:
    """Muestra el resultado del reporte y sus botones de exportación.

    Args:
        df: Datos del reporte (``None`` si aún no se ha ejecutado).
        definicion: Reporte mostrado.
        repositorio: Repositorio inyectado, usado para auditar la exportación.
        usuario: Usuario de la sesión (para auditoría).
    """
    if df is None:
        return
    if df.empty:
        st.info(MENSAJE_SIN_RESULTADOS)
        return
    st.success(f"✅ {len(df)} registros encontrados")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if "Totales" not in df.columns.tolist():
        st.markdown("**Resumen de totales:**")
        resumen = pd.DataFrame([{"Reporte": f"Total: {len(df)} registros"}])
        st.dataframe(resumen, use_container_width=True, hide_index=True)

    col_excel, col_csv = st.columns(2)
    with col_excel:
        st.download_button(
            "📥 Exportar a Excel",
            data=generar_excel(df, definicion.nombre),
            file_name=f"{definicion.id}_{date.today()}.xlsx",
            mime=TIPO_MIME_EXCEL,
            key=f"exp_xlsx_{definicion.id}",
        )
    with col_csv:
        st.download_button(
            "📄 Exportar a CSV",
            data=generar_csv(df),
            file_name=f"{definicion.id}_{date.today()}.csv",
            mime=TIPO_MIME_CSV,
            key=f"exp_csv_{definicion.id}",
        )
    repositorio.registrar_exportacion(usuario, definicion.nombre, len(df))


def render_reportes(repositorio: ReportesRepository | None = None) -> None:
    """Renderiza la vista completa de reportes y exportaciones (spec 010).

    Args:
        repositorio: Repositorio de reportes a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las
            pruebas.
    """
    repositorio = repositorio or ReportesRepository()
    usuario = st.session_state.get("usuario", USUARIO_POR_DEFECTO)
    st.title(TITULO)
    st.markdown(DESCRIPCION)

    definiciones = repositorio.listar_reportes()
    nombres = [definicion.nombre for definicion in definiciones]
    nombre_elegido = st.selectbox("Reporte", nombres, key="sel_reporte")
    definicion = next(d for d in definiciones if d.nombre == nombre_elegido)
    st.markdown(f"**{definicion.descripcion}**")

    with st.form(f"form_report_{definicion.id}"):
        col_filtros, col_boton = st.columns([3, 1])
        with col_filtros:
            seleccion = _construir_seleccion(definicion, repositorio)
        with col_boton:
            st.write("")
            st.write("")
            ejecutar = st.form_submit_button(ETIQUETA_EJECUTAR)

    clave = f"df_report_{definicion.id}"
    if ejecutar:
        df = repositorio.ejecutar_reporte(definicion.id, seleccion)
        st.session_state[clave] = df
    else:
        df = st.session_state.get(clave)

    _render_resultado(df, definicion, repositorio, usuario)


__all__ = [
    "DESCRIPCION",
    "ETIQUETA_EJECUTAR",
    "MENSAJE_SIN_RESULTADOS",
    "OPCION_TODAS",
    "OPCION_TODOS",
    "TITULO",
    "USUARIO_POR_DEFECTO",
    "parsear_entero",
    "render_reportes",
]
