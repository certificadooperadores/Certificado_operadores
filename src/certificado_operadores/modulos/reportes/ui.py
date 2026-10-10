"""Interfaz Streamlit de reportes y exportaciones (specs 010 y 023).

Capa de presentación pura: selecciona el reporte, captura los filtros en una
**barra horizontal compacta** y muestra los resultados con tarjetas de KPI, un
gráfico de barras nativo y sus botones de descarga. Delega **todo** el acceso a
datos (catálogos de filtros, consultas consolidadas y auditoría) en
:class:`~certificado_operadores.infra.reportes_repository.ReportesRepository` y la
generación de archivos en las funciones puras ``generar_excel``/``generar_csv``.
No contiene sentencias de base de datos ni conoce el motor ni el esquema.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

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

from certificado_operadores.estilos import COLOR_PRIMARIO  # noqa: E402
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

TITULO = "Reportes y Exportaciones"
"""Título de la vista de reportes, sin emojis informales."""

SUBTITULO = "Selecciona un reporte, aplica los filtros y exporta a Excel o CSV."
"""Subtítulo descriptivo en gris neutro."""

USUARIO_POR_DEFECTO = "Usuario"
"""Usuario usado cuando la sesión no expone uno."""

ETIQUETA_EJECUTAR = "Filtrar"
"""Texto del botón que ejecuta el reporte."""

OPCION_TODAS = "Todas"
"""Opción sin restricción para los filtros femeninos (empresa/tipología)."""

OPCION_TODOS = "Todos"
"""Opción sin restricción para el resto de filtros de selección."""

MENSAJE_SIN_RESULTADOS = "El reporte no arrojó resultados con los filtros actuales."
"""Mensaje cuando el reporte no devuelve filas."""

# --- Reparto de anchos del toolbar horizontal (spec 023, R-04) --------------
PROPORCIONES_TOOLBAR: tuple[float, ...] = (2, 2, 1.5, 2, 1)
"""Reparto de referencia del toolbar ``[Reporte][Concesionaria][Estado][Fechas][Filtrar]``."""

PESO_FILTRO = 2.0
"""Ancho relativo de cada columna de filtro cuando el reparto de referencia no aplica."""

PESO_BOTON = 1.0
"""Ancho relativo de la columna del botón de filtrado."""

LIMITE_GRAFICO = 15
"""Máximo de categorías mostradas en el gráfico de barras nativo."""

COLUMNA_CATEGORIA = "Categoria"
"""Nombre de la columna categórica de la agregación del gráfico."""

COLUMNA_VALOR = "Total"
"""Nombre de la columna numérica de la agregación del gráfico."""

COLUMNAS_TOTAL: tuple[str, ...] = ("Total", "Codigos", "Registros")
"""Columnas numéricas preferidas como valor del gráfico de barras."""

TITULO_KPI_REGISTROS = "Registros"
"""Rótulo de la tarjeta métrica con el total de registros."""

TITULO_KPI_COLUMNAS = "Columnas"
"""Rótulo de la tarjeta métrica con el número de columnas."""

TITULO_GRAFICO = "Distribución"
"""Rótulo del gráfico de barras nativo."""

CLAVE_REPORTE = "sel_reporte"
"""Clave de sesión del selector de reporte."""


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


def pesos_toolbar(numero_filtros: int) -> list[float]:
    """Calcula los anchos de la barra horizontal de filtros.

    Args:
        numero_filtros: Cantidad de filtros del reporte seleccionado.

    Returns:
        La lista de anchos relativos para :func:`streamlit.columns`; replica el
        reparto de referencia de la spec cuando la cantidad coincide.
    """
    if numero_filtros + 1 == len(PROPORCIONES_TOOLBAR):
        return list(PROPORCIONES_TOOLBAR)
    return [PESO_FILTRO] * numero_filtros + [PESO_BOTON]


def construir_agregacion(df: pd.DataFrame, limite: int = LIMITE_GRAFICO) -> pd.DataFrame:
    """Construye la serie agregada que alimenta el gráfico de barras nativo.

    Función pura (sin Streamlit) que agrupa el resultado del reporte por su
    primera columna categórica: si existe una columna numérica usa su suma; en
    caso contrario cuenta las ocurrencias. Ordena de mayor a menor y recorta al
    ``limite`` para mantener el gráfico liviano (<2 ms sobre agregaciones en
    memoria).

    Args:
        df: Datos del reporte ya ejecutado.
        limite: Máximo de categorías a incluir.

    Returns:
        Un ``DataFrame`` de dos columnas (:data:`COLUMNA_CATEGORIA` y
        :data:`COLUMNA_VALOR`) listo para :func:`streamlit.bar_chart`; vacío si
        no hay datos.
    """
    if df is None or df.empty or df.columns.empty:
        return pd.DataFrame(columns=[COLUMNA_CATEGORIA, COLUMNA_VALOR])
    categorica = df.columns[0]
    numericas = [columna for columna in df.columns if pd.api.types.is_numeric_dtype(df[columna])]
    columna_valor = next(
        (nombre for nombre in COLUMNAS_TOTAL if nombre in numericas),
        numericas[-1] if numericas else None,
    )
    if columna_valor is not None:
        serie = df.groupby(categorica, dropna=False)[columna_valor].sum()
    else:
        serie = df[categorica].value_counts(dropna=False)
    serie = serie.sort_values(ascending=False).head(limite)
    return pd.DataFrame(
        {
            COLUMNA_CATEGORIA: [str(indice) for indice in serie.index],
            COLUMNA_VALOR: serie.to_numpy(),
        }
    )


def _render_filtro(
    filtro_tipo: str, filtro_etiqueta: str, defecto: int | None, repositorio, definicion
) -> Any:
    """Renderiza un filtro del reporte y devuelve el valor tipado capturado.

    Args:
        filtro_tipo: Clase de filtro (``empresa``, ``estado``, ``fecha``, etc.).
        filtro_etiqueta: Texto del control en la interfaz.
        defecto: Valor por defecto de los controles numéricos.
        repositorio: Repositorio inyectado, usado para cargar las opciones.
        definicion: Reporte cuyos filtros se capturan.

    Returns:
        El valor capturado: identificador, etiqueta, rango o ``None``.
    """
    if filtro_tipo == "empresa":
        opciones = {
            f"{elemento.id_empresa} - {elemento.nombre_empresa}": elemento.id_empresa
            for elemento in repositorio.listar_empresas()
        }
        seleccion = st.selectbox(
            filtro_etiqueta,
            [OPCION_TODAS, *opciones],
            key=f"filt_emp_{definicion.id}",
        )
        return opciones.get(seleccion)
    if filtro_tipo == "estado":
        seleccion = st.selectbox(
            filtro_etiqueta,
            list(OPCIONES_ESTADO),
            index=0,
            key=f"filt_est_{definicion.id}",
        )
        return None if seleccion == OPCION_TODOS else seleccion
    if filtro_tipo == "estado_activo":
        seleccion = st.selectbox(
            filtro_etiqueta,
            list(OPCIONES_ESTADO_ACTIVO),
            index=0,
            key=f"filt_estac_{definicion.id}",
        )
        return None if seleccion == OPCION_TODOS else seleccion
    if filtro_tipo == "tipologia":
        opciones = {
            elemento.descripcion: elemento.id_perfil_tipologia
            for elemento in repositorio.listar_tipologias()
        }
        seleccion = st.selectbox(
            filtro_etiqueta,
            [OPCION_TODAS, *opciones],
            key=f"filt_tip_{definicion.id}",
        )
        return opciones.get(seleccion)
    if filtro_tipo == "dias_vencer":
        return st.slider(
            filtro_etiqueta,
            DIAS_VENCIMIENTO_MINIMO,
            DIAS_VENCIMIENTO_MAXIMO,
            int(defecto or DIAS_VENCIMIENTO_DEFECTO),
            key=f"filt_dias_{definicion.id}",
        )
    if filtro_tipo == "fecha":
        fecha_desde = st.date_input(
            "Desde",
            value=date.today().replace(day=1),
            key=f"filt_desde_{definicion.id}",
        )
        fecha_hasta = st.date_input(
            "Hasta",
            value=date.today(),
            key=f"filt_hasta_{definicion.id}",
        )
        return (fecha_desde, fecha_hasta)
    if filtro_tipo == "tipo_evento":
        opciones = {
            f"{elemento.id_tipo_evento} - {elemento.nombre_evento.title()}": (
                elemento.id_tipo_evento
            )
            for elemento in repositorio.listar_tipos_evento()
        }
        seleccion = st.selectbox(
            filtro_etiqueta,
            [OPCION_TODOS, *opciones],
            key=f"filt_tev_{definicion.id}",
        )
        return opciones.get(seleccion)
    if filtro_tipo == "impacto":
        opciones = {
            f"{elemento.id_impacto} - {elemento.impacto}": elemento.id_impacto
            for elemento in repositorio.listar_impactos()
        }
        seleccion = st.selectbox(
            filtro_etiqueta,
            [OPCION_TODOS, *opciones],
            key=f"filt_imp_{definicion.id}",
        )
        return opciones.get(seleccion)
    if filtro_tipo == "codigo":
        return parsear_entero(st.text_input(filtro_etiqueta, key=f"filt_cod_{definicion.id}"))
    return None


def _construir_seleccion(
    definicion: DefinicionReporte, repositorio: ReportesRepository
) -> tuple[SeleccionFiltros, bool]:
    """Renderiza la barra horizontal de filtros y devuelve la selección tipada.

    Coloca todos los filtros del reporte en una sola fila de columnas (spec 023,
    R-04) y reserva la última columna para el botón de filtrado.

    Args:
        definicion: Reporte cuyos filtros se van a capturar.
        repositorio: Repositorio inyectado, usado para cargar las opciones.

    Returns:
        La selección capturada y ``True`` si el usuario pulsó el botón.
    """
    valores: dict[str, Any] = {
        "empresa": None,
        "estado": None,
        "estado_activo": None,
        "tipologia": None,
        "dias_vencer": None,
        "fecha_desde": None,
        "fecha_hasta": None,
        "tipo_evento": None,
        "impacto": None,
        "codigo": None,
    }
    columnas = st.columns(pesos_toolbar(len(definicion.filtros)))
    for indice, filtro in enumerate(definicion.filtros):
        with columnas[indice]:
            capturado = _render_filtro(
                filtro.tipo, filtro.etiqueta, filtro.defecto, repositorio, definicion
            )
        if filtro.tipo == "fecha":
            valores["fecha_desde"], valores["fecha_hasta"] = capturado
        else:
            valores[filtro.tipo] = capturado

    with columnas[-1]:
        ejecutar = st.form_submit_button(ETIQUETA_EJECUTAR, type="primary")

    return SeleccionFiltros(**valores), ejecutar


def _render_kpis(df: pd.DataFrame) -> None:
    """Muestra las tarjetas métricas ejecutivas del resultado.

    Args:
        df: Datos del reporte ya ejecutado.
    """
    numericas = [columna for columna in df.columns if pd.api.types.is_numeric_dtype(df[columna])]
    col_registros, col_total, col_columnas = st.columns(3)
    with col_registros:
        st.metric(TITULO_KPI_REGISTROS, len(df))
    with col_total:
        etiqueta = numericas[0] if numericas else TITULO_KPI_COLUMNAS
        valor = int(df[numericas[0]].sum()) if numericas else len(df.columns)
        st.metric(etiqueta, valor)
    with col_columnas:
        st.metric(TITULO_KPI_COLUMNAS, len(df.columns))


def _render_grafico(df: pd.DataFrame) -> None:
    """Dibuja el gráfico de barras horizontal nativo de la agregación.

    Args:
        df: Datos del reporte ya ejecutado.
    """
    agregacion = construir_agregacion(df)
    if agregacion.empty:
        return
    st.markdown(f"**{TITULO_GRAFICO}**")
    st.bar_chart(
        agregacion,
        x=COLUMNA_CATEGORIA,
        y=COLUMNA_VALOR,
        horizontal=True,
        color=COLOR_PRIMARIO,
    )


def _render_resultado(
    df: pd.DataFrame | None,
    definicion: DefinicionReporte,
    repositorio: ReportesRepository,
    usuario: str,
) -> None:
    """Muestra KPIs, tabla, gráfico y botones de exportación del reporte.

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
    _render_kpis(df)
    st.dataframe(df, use_container_width=True, hide_index=True)
    _render_grafico(df)

    col_excel, col_csv = st.columns(2)
    with col_excel:
        st.download_button(
            "Exportar a Excel",
            data=generar_excel(df, definicion.nombre),
            file_name=f"{definicion.id}_{date.today()}.xlsx",
            mime=TIPO_MIME_EXCEL,
            key=f"exp_xlsx_{definicion.id}",
        )
    with col_csv:
        st.download_button(
            "Exportar a CSV",
            data=generar_csv(df),
            file_name=f"{definicion.id}_{date.today()}.csv",
            mime=TIPO_MIME_CSV,
            key=f"exp_csv_{definicion.id}",
        )
    repositorio.registrar_exportacion(usuario, definicion.nombre, len(df))


def render_reportes(repositorio: ReportesRepository | None = None) -> None:
    """Renderiza la vista completa de reportes y exportaciones (specs 010 y 023).

    Args:
        repositorio: Repositorio de reportes a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las
            pruebas.
    """
    repositorio = repositorio or ReportesRepository()
    usuario = st.session_state.get("usuario", USUARIO_POR_DEFECTO)
    st.title(TITULO)
    st.markdown(f'<p class="subtitulo-metrocali">{SUBTITULO}</p>', unsafe_allow_html=True)

    definiciones = repositorio.listar_reportes()
    nombres = [definicion.nombre for definicion in definiciones]
    nombre_elegido = st.selectbox("Reporte", nombres, key=CLAVE_REPORTE)
    definicion = next(d for d in definiciones if d.nombre == nombre_elegido)
    st.markdown(f"**{definicion.descripcion}**")

    with st.form(f"form_report_{definicion.id}"):
        seleccion, ejecutar = _construir_seleccion(definicion, repositorio)

    clave = f"df_report_{definicion.id}"
    if ejecutar:
        df = repositorio.ejecutar_reporte(definicion.id, seleccion)
        st.session_state[clave] = df
    else:
        df = st.session_state.get(clave)

    _render_resultado(df, definicion, repositorio, usuario)


__all__ = [
    "MENSAJE_SIN_RESULTADOS",
    "OPCION_TODAS",
    "OPCION_TODOS",
    "PROPORCIONES_TOOLBAR",
    "TITULO",
    "USUARIO_POR_DEFECTO",
    "construir_agregacion",
    "parsear_entero",
    "pesos_toolbar",
    "render_reportes",
]
