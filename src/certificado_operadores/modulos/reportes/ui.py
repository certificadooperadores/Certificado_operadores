"""Interfaz Streamlit de reportes y exportaciones (specs 010, 023 y 024).

Capa de presentación pura: selecciona el reporte, captura los filtros en una
**barra horizontal compacta** y muestra los resultados con **KPIs de negocio
inteligentes por tipo de reporte**, los **botones de exportación en la cabecera**
(sobre la tabla) y, para los reportes de vencimiento, un **diagrama de Gantt
temporal por concesionario** generado con matplotlib. Delega **todo** el acceso a
datos (catálogos de filtros, consultas consolidadas y auditoría) en
:class:`~certificado_operadores.infra.reportes_repository.ReportesRepository` y la
generación de archivos en las funciones puras ``generar_excel``/``generar_csv``.
No contiene sentencias de base de datos ni conoce el motor ni el esquema, y
**nunca suma identificadores** (códigos, cédulas o IDs) ni muestra la tarjeta de
``Columnas``.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

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

# --- Criticidad de vencimientos (spec 024, R-03 y R-07) ---------------------
DIAS_CRITICO = 30
"""Umbral de días para marcar un vencimiento como crítico (menos de 30 días)."""

DIAS_ALERTA = 60
"""Umbral de días para marcar un vencimiento como alerta (entre 30 y 60 días)."""

COLOR_CRITICO = "#EF4444"
"""Rojo del semáforo: vence en menos de 30 días."""

COLOR_ALERTA = "#F59E0B"
"""Ámbar del semáforo: vence entre 30 y 60 días."""

# Identificadores de los reportes de vencimiento que llevan diagrama de Gantt.
_REPORTES_GANTT = ("licencias_vencer", "certificados_vencer")

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


def color_criticidad(dias: int | float) -> str:
    """Devuelve el color del semáforo según los días restantes al vencimiento.

    Aplica los umbrales de la spec 024 (R-07): menos de
    :data:`DIAS_CRITICO` días es crítico (rojo), entre :data:`DIAS_CRITICO` y
    :data:`DIAS_ALERTA` es alerta (ámbar) y más de :data:`DIAS_ALERTA` es normal
    (azul institucional).

    Args:
        dias: Días restantes para el vencimiento (negativos = ya vencido).

    Returns:
        El color hexadecimal correspondiente a la criticidad.
    """
    if dias < DIAS_CRITICO:
        return COLOR_CRITICO
    if dias <= DIAS_ALERTA:
        return COLOR_ALERTA
    return COLOR_PRIMARIO


def _determinacion_pendiente(valor: object) -> bool:
    """Indica si una determinación está pendiente (vacía o ``Pendiente``).

    Args:
        valor: Valor de la columna ``Determinacion`` de una reincidencia.

    Returns:
        ``True`` si el valor es ``None``, cadena vacía o ``Pendiente``.
    """
    if valor is None or pd.isna(valor):
        return True
    texto = str(valor).strip()
    return texto == "" or texto.casefold() == "pendiente"


def calcular_kpis(id_reporte: str, df: pd.DataFrame) -> list[tuple[str, int]]:
    """Calcula las métricas de negocio del reporte (prohibido sumar identificadores).

    Cada reporte expone KPIs que aportan valor de decisión: totales, conteos de
    criticidad, concesionarios involucrados, operadores únicos, vehículos o rutas.
    **Nunca** suma códigos, cédulas ni IDs, y **no** cuenta columnas.

    Args:
        id_reporte: Identificador estable del reporte.
        df: Datos del reporte ya ejecutado.

    Returns:
        Lista de pares ``(etiqueta, valor)`` listos para ``st.metric``.
    """
    if df is None or df.empty:
        return []
    if id_reporte == "utryt":
        return [("Total Operadores", len(df))]
    if id_reporte == "licencias_vencer":
        criticas = int((df["Dias Restantes"] <= DIAS_CRITICO).sum())
        concesionarios = int(df["Empresa"].nunique()) if "Empresa" in df.columns else 0
        return [
            ("Total por Vencer", len(df)),
            ("Críticas (< 30 días)", criticas),
            ("Concesionarios", concesionarios),
        ]
    if id_reporte == "certificados_vencer":
        criticos = int((df["Dias Restantes"] <= DIAS_CRITICO).sum())
        concesionarios = int(df["Empresa"].nunique()) if "Empresa" in df.columns else 0
        operadores = int(df["Codigo"].nunique())
        return [
            ("Total por Vencer", len(df)),
            ("Próximos a Vencer (< 30 días)", criticos),
            ("Concesionarios Afectados", concesionarios),
            ("Operadores Únicos", operadores),
        ]
    if id_reporte == "certificados_vencidos":
        concesionarios = int(df["Empresa"].nunique()) if "Empresa" in df.columns else 0
        operadores = int(df["Codigo"].nunique())
        return [
            ("Total Certificados Vencidos", len(df)),
            ("Concesionarios Afectados", concesionarios),
            ("Operadores Vencidos", operadores),
        ]
    if id_reporte == "operadores_empresa":
        total = int(df["Codigos"].sum()) if "Codigos" in df.columns else len(df)
        tiene_cols = "Tipologia" in df.columns and "Codigos" in df.columns
        art = int(df[df["Tipologia"] == "Articulado"]["Codigos"].sum()) if tiene_cols else 0
        pad = int(df[df["Tipologia"] == "Padrón"]["Codigos"].sum()) if tiene_cols else 0
        comp = int(df[df["Tipologia"] == "Complementario"]["Codigos"].sum()) if tiene_cols else 0
        return [
            ("Total Activos", total),
            ("Articulado", art),
            ("Padrón", pad),
            ("Complementario", comp),
        ]
    if id_reporte == "reincidencias":
        pendientes = int(df["Determinacion"].apply(_determinacion_pendiente).sum())
        graves = int((df["Impacto"] == "Grave").sum())
        return [
            ("Total Casos", len(df)),
            ("Pendientes de Determinación", pendientes),
            ("Casos Graves", graves),
        ]
    if id_reporte == "comportamientos_operador":
        operadores = int(df["Codigo"].nunique()) if "Codigo" in df.columns else 0
        rutas = int(df["Ruta"].nunique()) if "Ruta" in df.columns else 0
        vehiculos = int(df["Vehiculo"].nunique()) if "Vehiculo" in df.columns else 0
        return [
            ("Total Novedades", len(df)),
            ("Operadores con Novedad", operadores),
            ("Rutas Afectadas", rutas),
            ("Vehículos Involucrados", vehiculos),
        ]
    # Resto de reportes operacionales (p. ej. eventos por tipo): total simple.
    return [("Registros", len(df))]


def generar_gantt_vencimientos(df: pd.DataFrame) -> Figure:
    """Genera el diagrama de Gantt de vencimientos por concesionario (spec 024).

    Cada fila del resultado (licencia o certificado) se dibuja como una barra
    horizontal en el eje del concesionario al que pertenece, con longitud igual a
    sus días restantes y color según su criticidad (:func:`color_criticidad`).
    Permite ver de un vistazo el cronograma de vencimientos en el tiempo.

    Args:
        df: Datos del reporte con, al menos, las columnas ``Empresa`` y
            ``Dias Restantes``.

    Returns:
        La figura de matplotlib lista para ``st.pyplot`` (sin ejes si no hay datos).
    """
    figura = Figure(figsize=(10, 3))
    ejes = figura.subplots()
    if df is None or df.empty or "Empresa" not in df.columns or "Dias Restantes" not in df.columns:
        ejes.axis("off")
        return figura

    filas = df.copy()
    filas["Empresa"] = filas["Empresa"].fillna("Sin Concesionario").astype(str)
    empresas = list(dict.fromkeys(filas["Empresa"]))
    dias = filas["Dias Restantes"].astype(float).tolist()
    colores = [color_criticidad(dia) for dia in dias]
    posiciones = [empresas.index(empresa) for empresa in filas["Empresa"]]

    ejes.barh(posiciones, dias, height=0.5, color=colores)
    ejes.set_yticks(range(len(empresas)))
    ejes.set_yticklabels(empresas)
    ejes.set_xlabel("Días restantes para el vencimiento")
    ejes.set_title("Vencimientos por concesionario")
    ejes.invert_yaxis()
    figura.tight_layout()
    return figura


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


def _render_kpis(df: pd.DataFrame, definicion: DefinicionReporte) -> None:
    """Muestra las tarjetas métricas de negocio del reporte.

    Args:
        df: Datos del reporte ya ejecutado.
        definicion: Reporte mostrado (define qué KPIs aplican).
    """
    kpis = calcular_kpis(definicion.id, df)
    if not kpis:
        return
    columnas = st.columns(len(kpis))
    for columna, (etiqueta, valor) in zip(columnas, kpis, strict=True):
        columna.metric(etiqueta, valor)


def _render_exportacion(df: pd.DataFrame, definicion: DefinicionReporte) -> None:
    """Muestra los botones de exportación en la cabecera, sobre la tabla.

    Args:
        df: Datos del reporte ya ejecutado.
        definicion: Reporte mostrado (nombra los archivos descargados).
    """
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


def _render_gantt(df: pd.DataFrame, definicion: DefinicionReporte) -> None:
    """Dibuja el cronograma interactivo de vencimientos por quincenas y concesionario.

    Args:
        df: Datos del reporte ya ejecutado.
        definicion: Reporte mostrado (define si aplica el cronograma).
    """
    if definicion.id not in _REPORTES_GANTT:
        return
    if df is None or df.empty or "Empresa" not in df.columns or "Dias Restantes" not in df.columns:
        return

    st.markdown("#### 📅 Cronograma Interactivo de Vencimientos por Quincena")
    copia = df.copy()
    copia["Dias Restantes"] = pd.to_numeric(copia["Dias Restantes"], errors="coerce").fillna(0)

    # Agrupar en ventanas quincenales cada 15 días
    def _agrupar_quincena(dias: float) -> str:
        if dias <= 15:
            return "01. 0 a 15 días (Crítico)"
        if dias <= 30:
            return "02. 16 a 30 días (Crítico)"
        if dias <= 45:
            return "03. 31 a 45 días (Alerta)"
        if dias <= 60:
            return "04. 46 a 60 días (Alerta)"
        if dias <= 90:
            return "05. 61 a 90 días"
        return "06. Más de 90 días"

    copia["Ventana Vencimiento"] = copia["Dias Restantes"].apply(_agrupar_quincena)

    # Resumen agrupado para el gráfico
    resumen = copia.groupby(["Empresa", "Ventana Vencimiento"]).size().reset_index(name="Cantidad")

    color_scale = alt.Scale(
        domain=[
            "01. 0 a 15 días (Crítico)",
            "02. 16 a 30 días (Crítico)",
            "03. 31 a 45 días (Alerta)",
            "04. 46 a 60 días (Alerta)",
            "05. 61 a 90 días",
            "06. Más de 90 días",
        ],
        range=["#DC2626", "#EF4444", "#F59E0B", "#FBBF24", "#3B82F6", "#10B981"],
    )

    chart = (
        alt.Chart(resumen)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("Cantidad:Q", title="Cantidad de Vencimientos"),
            y=alt.Y("Empresa:N", title="Concesionario", sort="-x"),
            color=alt.Color("Ventana Vencimiento:N", scale=color_scale, title="Ventana"),
            tooltip=[
                alt.Tooltip("Empresa:N", title="Concesionario"),
                alt.Tooltip("Ventana Vencimiento:N", title="Ventana"),
                alt.Tooltip("Cantidad:Q", title="Total"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)
    with st.expander("Ver cronograma estático tradicional (Matplotlib)", expanded=False):
        st.pyplot(generar_gantt_vencimientos(df))


def _render_graficos_analiticos(df: pd.DataFrame, definicion: DefinicionReporte) -> None:
    """Muestra visualizaciones gráficas interactivas según el reporte seleccionado.

    Args:
        df: Datos del reporte ya ejecutado.
        definicion: Reporte mostrado.
    """
    if df is None or df.empty:
        return

    if definicion.id == "operadores_empresa":
        st.markdown("#### 📊 Distribución de Operadores Activos")
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("**Activos por Concesionario**")
            res_emp = df.groupby("Empresa")["Codigos"].sum().reset_index(name="Total")
            chart_emp = (
                alt.Chart(res_emp)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("Total:Q", title="Operadores Activos"),
                    y=alt.Y("Empresa:N", title="Concesionario", sort="-x"),
                    color=alt.Color(
                        "Empresa:N",
                        scale=alt.Scale(scheme="tableau10"),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("Empresa:N", title="Concesionario"),
                        alt.Tooltip("Total:Q", title="Total Activos"),
                    ],
                )
                .properties(height=240)
            )
            st.altair_chart(chart_emp, use_container_width=True)

        with col_graf2:
            st.markdown("**Activos por Tipología**")
            res_tip = df.groupby("Tipologia")["Codigos"].sum().reset_index(name="Total")
            scale_tip = alt.Scale(
                domain=["Articulado", "Padrón", "Complementario"],
                range=["#2563EB", "#0D9488", "#F59E0B"],
            )
            chart_tip = (
                alt.Chart(res_tip)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("Total:Q", title="Operadores Activos"),
                    y=alt.Y("Tipologia:N", title="Tipología", sort="-x"),
                    color=alt.Color(
                        "Tipologia:N",
                        scale=scale_tip,
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("Tipologia:N", title="Tipología"),
                        alt.Tooltip("Total:Q", title="Total Activos"),
                    ],
                )
                .properties(height=240)
            )
            st.altair_chart(chart_tip, use_container_width=True)

    elif definicion.id == "certificados_vencidos":
        st.markdown("#### 🚨 Certificados Vencidos por Concesionario")
        res_venc = df.groupby("Empresa").size().reset_index(name="Vencidos")
        chart_venc = (
            alt.Chart(res_venc)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#DC2626")
            .encode(
                x=alt.X("Vencidos:Q", title="Total Certificados Vencidos"),
                y=alt.Y("Empresa:N", title="Concesionario", sort="-x"),
                tooltip=[
                    alt.Tooltip("Empresa:N", title="Concesionario"),
                    alt.Tooltip("Vencidos:Q", title="Certificados Vencidos"),
                ],
            )
            .properties(height=240)
        )
        st.altair_chart(chart_venc, use_container_width=True)

    elif definicion.id == "comportamientos_operador":
        st.markdown("#### 📈 Analítica Dinámica de Comportamientos y Operación")
        st.caption(
            "💡 **Interactivo:** Haz clic en una barra de operador para filtrar "
            "automáticamente sus causales y rutas asociadas (tipo Power BI). "
            "Haz clic fuera o presiona Shift+clic para restablecer."
        )

        copia_comp = df.copy()

        # Extraer la causal raíz o nivel clave después de ::
        def _extraer_causal(desc: str) -> str:
            partes = [p.strip() for p in str(desc).split("::") if p.strip()]
            return partes[-1].capitalize() if partes else "Sin causal"

        copia_comp["Causal"] = copia_comp["Descripcion"].apply(_extraer_causal)
        copia_comp["Operador"] = (
            copia_comp["Codigo"].astype(str) + " - " + copia_comp["Nombre"].astype(str)
        )
        copia_comp["Ruta"] = copia_comp["Ruta"].fillna("Sin Ruta").astype(str)

        # Selector interactivo sobre el Operador
        selector_operador = alt.selection_point(
            name="filtro_operador",
            fields=["Operador"],
            empty=True,
        )

        # Fuente común de datos
        base = alt.Chart(copia_comp)

        # 1. Gráfico Top 10 Operadores con control de opacidad según selección
        chart_ops = (
            base.transform_aggregate(Novedades="count()", groupby=["Operador"])
            .transform_window(
                rank="rank()",
                sort=[alt.SortField("Novedades", order="descending")],
            )
            .transform_filter(alt.datum.rank <= 10)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Novedades:Q", title="Total Novedades"),
                y=alt.Y("Operador:N", title="Operador", sort="-x"),
                color=alt.condition(
                    selector_operador,
                    alt.value("#D97706"),
                    alt.value("#FDE68A"),
                ),
                tooltip=[
                    alt.Tooltip("Operador:N", title="Operador"),
                    alt.Tooltip("Novedades:Q", title="Novedades"),
                ],
            )
            .add_params(selector_operador)
            .properties(width=340, height=300, title="Top 10 Operadores (Clic para filtrar)")
        )

        # 2. Gráfico Causales filtrado dinámicamente por el operador seleccionado
        chart_causas = (
            base.transform_filter(selector_operador)
            .transform_aggregate(Casos="count()", groupby=["Causal"])
            .transform_window(
                rank="rank()",
                sort=[alt.SortField("Casos", order="descending")],
            )
            .transform_filter(alt.datum.rank <= 8)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#4F46E5")
            .encode(
                x=alt.X("Casos:Q", title="Frecuencia"),
                y=alt.Y("Causal:N", title="Causal", sort="-x"),
                tooltip=[
                    alt.Tooltip("Causal:N", title="Causal"),
                    alt.Tooltip("Casos:Q", title="Casos"),
                ],
            )
            .properties(width=320, height=300, title="Causales del Operador")
        )

        # 3. Gráfico Rutas filtrado dinámicamente por el operador seleccionado
        chart_rutas = (
            base.transform_filter(selector_operador)
            .transform_filter(alt.datum.Ruta != "Sin Ruta")
            .transform_aggregate(Eventos="count()", groupby=["Ruta"])
            .transform_window(
                rank="rank()",
                sort=[alt.SortField("Eventos", order="descending")],
            )
            .transform_filter(alt.datum.rank <= 10)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#059669")
            .encode(
                x=alt.X("Eventos:Q", title="Eventos"),
                y=alt.Y("Ruta:N", title="Ruta", sort="-x"),
                tooltip=[
                    alt.Tooltip("Ruta:N", title="Ruta"),
                    alt.Tooltip("Eventos:Q", title="Eventos"),
                ],
            )
            .properties(width=320, height=300, title="Rutas del Operador")
        )

        dashboard_interactivo = alt.hconcat(chart_ops, chart_causas, chart_rutas).resolve_scale(
            x="independent", y="independent"
        )
        st.altair_chart(dashboard_interactivo, use_container_width=True)


def _render_resultado(
    df: pd.DataFrame | None,
    definicion: DefinicionReporte,
    repositorio: ReportesRepository,
    usuario: str,
) -> None:
    """Muestra KPIs, botones de exportación, tabla y Gantt del reporte.

    El orden respeta la spec 024: los botones de exportación quedan en la
    cabecera, directamente encima de la tabla, para que el usuario no tenga que
    desplazarse. No se renderizan gráficos de barras por código individual.

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
    _render_kpis(df, definicion)
    _render_graficos_analiticos(df, definicion)
    _render_gantt(df, definicion)
    _render_exportacion(df, definicion)
    st.dataframe(df, use_container_width=True, hide_index=True)
    repositorio.registrar_exportacion(usuario, definicion.nombre, len(df))


def render_reportes(repositorio: ReportesRepository | None = None) -> None:
    """Renderiza la vista completa de reportes y exportaciones (specs 010, 023 y 024).

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
    "COLOR_ALERTA",
    "COLOR_CRITICO",
    "DIAS_ALERTA",
    "DIAS_CRITICO",
    "MENSAJE_SIN_RESULTADOS",
    "OPCION_TODAS",
    "OPCION_TODOS",
    "PROPORCIONES_TOOLBAR",
    "TITULO",
    "USUARIO_POR_DEFECTO",
    "calcular_kpis",
    "color_criticidad",
    "generar_gantt_vencimientos",
    "parsear_entero",
    "pesos_toolbar",
    "render_reportes",
]
