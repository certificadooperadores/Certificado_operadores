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
    if id_reporte in ("certificados_vencer", "certificados_vencidos"):
        columna_dias = "Dias Restantes" if id_reporte == "certificados_vencer" else "Dias Vencido"
        etiqueta = (
            "Próximos a Vencer (< 30 días)" if id_reporte == "certificados_vencer" else "Críticos"
        )
        criticos = int((df[columna_dias] <= DIAS_CRITICO).sum())
        operadores = int(df["Codigo"].nunique())
        return [
            ("Total Certificados", len(df)),
            (etiqueta, criticos),
            ("Operadores Únicos", operadores),
        ]
    if id_reporte == "operadores_empresa":
        total = int(df["Codigos"].sum())
        concesionarios = int(df["Empresa"].nunique())
        return [
            ("Total Operadores Activos", total),
            ("Concesionarios Activos", concesionarios),
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
        vehiculos = int(df["Vehiculo"].nunique()) if "Vehiculo" in df.columns else 0
        rutas = int(df["Ruta"].nunique()) if "Ruta" in df.columns else 0
        return [
            ("Total Novedades", len(df)),
            ("Vehículos Involucrados", vehiculos),
            ("Rutas Afectadas", rutas),
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
    """Dibuja el diagrama de Gantt de vencimientos, solo para reportes de vencimiento.

    Args:
        df: Datos del reporte ya ejecutado.
        definicion: Reporte mostrado (define si aplica el Gantt).
    """
    if definicion.id not in _REPORTES_GANTT:
        return
    st.pyplot(generar_gantt_vencimientos(df))


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
    _render_exportacion(df, definicion)
    st.dataframe(df, use_container_width=True, hide_index=True)
    _render_gantt(df, definicion)
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
