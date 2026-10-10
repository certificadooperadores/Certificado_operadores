"""Repositorio de reportes y exportaciones (capa de infraestructura, spec 010).

Encapsula **todo** el acceso a datos de la vista de reportes: los catálogos que
alimentan los filtros (empresas, tipologías, tipos de evento e impactos), las
consultas consolidadas (UTRYT, certificados, reincidencias, etc.) con sus filtros
dinámicos y el registro de auditoría de las exportaciones. También construye los
archivos Excel y CSV en memoria.

La interfaz de usuario no conoce el esquema ni el motor: solo consume los DTOs y
el ``DataFrame`` que devuelve este repositorio. Las columnas de los filtros viven
aquí, nunca en la UI, y las consultas usan parámetros enlazados.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd
from sqlalchemy import text

from certificado_operadores.domain.models import (
    ANIOS_VIGENCIA_CERTIFICADO,
    TIPO_EVENTO_CANCELACION,
    TIPOS_EVENTO_CERTIFICADO,
    VIGENCIA_ACTIVA,
    VIGENCIA_ANULADA,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# --- Constantes de la vista --------------------------------------------------
TIPO_MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
"""Tipo MIME de un archivo ``.xlsx``."""

TIPO_MIME_CSV = "text/csv"
"""Tipo MIME de un archivo ``.csv``."""

ACCION_EXPORTAR_REPORTE = "Exportar Reporte"
"""Acción de auditoría al mostrar/exportar un reporte con resultados."""

OPCIONES_ESTADO: tuple[str, ...] = ("Vigente", "Inactivo", "Todos")
"""Etiquetas del filtro de estado del certificado."""

OPCIONES_ESTADO_ACTIVO: tuple[str, ...] = ("Activos", "Cancelados", "Todos")
"""Etiquetas del filtro de actividad (según evento de cancelación)."""

ESTADO_A_VIGENCIA: dict[str, int] = {
    "Vigente": VIGENCIA_ACTIVA,
    "Inactivo": VIGENCIA_ANULADA,
}
"""Traducción de la etiqueta de estado al identificador de vigencia."""

DIAS_VENCIMIENTO_DEFECTO = 90
"""Días por defecto de los filtros de vencimiento (heredado)."""

DIAS_VENCIMIENTO_MINIMO = 1
"""Límite inferior del control de días para vencimiento."""

DIAS_VENCIMIENTO_MAXIMO = 365
"""Límite superior del control de días para vencimiento."""

# --- Expresiones de fecha compatibles con SQLite (spec 022) ------------------
# La sintaxis nativa de PostgreSQL se sustituye por funciones propias de SQLite
# (normalización de fechas, aritmética de fechas y numeración de filas) para que
# todos los reportes se ejecuten sin errores sobre el motor embebido.
_MODIFICADOR_VIGENCIA = f"+{ANIOS_VIGENCIA_CERTIFICADO} years"
"""Modificador de SQLite que suma los años de vigencia a una fecha ISO."""

_LISTA_TIPOS_CERTIFICADO = ", ".join(str(tipo) for tipo in TIPOS_EVENTO_CERTIFICADO)
"""Tipos de evento de certificación como lista literal para el ``IN``."""

_COL_VENCIMIENTO_LICENCIA = "DATE(l.vencimiento)"
"""Vencimiento de la licencia normalizado como fecha."""

_COL_FECHA_EVENTOS = (
    "DATE(COALESCE(e.fecha_certificado, e.fecha_retiro, e.fecha_suspension, "
    "e.fecha_observacion, e.fecha_registro))"
)
"""Fecha efectiva de un evento normalizada con la función ``DATE`` de SQLite."""

_COL_VENCIMIENTO_CERTIFICADO = f"DATE(e.fecha_certificado, '{_MODIFICADOR_VIGENCIA}')"
"""Vencimiento del certificado: fecha de certificación más los años de vigencia."""

_SUBCONSULTA_ULTIMO_CERTIFICADO = f"""
    SELECT id_codigo, id_tipo_evento, fecha_certificado,
           ROW_NUMBER() OVER (
               PARTITION BY id_codigo ORDER BY DATE(fecha_certificado) DESC
           ) AS rn
    FROM fact_eventos_operador
    WHERE id_tipo_evento IN ({_LISTA_TIPOS_CERTIFICADO})
      AND fecha_certificado IS NOT NULL AND fecha_certificado <> ''
"""
"""Último certificado por código, numerado para conservar solo la fila reciente."""

_SUBCONSULTA_CANCELACION = (
    "SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = :cancelacion"
)


# --- DTOs públicos -----------------------------------------------------------
@dataclass(frozen=True)
class EmpresaInfo:
    """Empresa transportadora para el filtro de reportes.

    Attributes:
        id_empresa: Identificador de la empresa.
        nombre_empresa: Nombre de la empresa.
    """

    id_empresa: int
    nombre_empresa: str


@dataclass(frozen=True)
class TipologiaInfo:
    """Tipología de operador con su descripción legible.

    Attributes:
        id_perfil_tipologia: Identificador de la tipología.
        descripcion: Descripción construida a partir de las autorizaciones.
    """

    id_perfil_tipologia: int
    descripcion: str


@dataclass(frozen=True)
class TipoEventoInfo:
    """Tipo de evento del historial del operador.

    Attributes:
        id_tipo_evento: Identificador del tipo de evento.
        nombre_evento: Nombre del tipo de evento.
    """

    id_tipo_evento: int
    nombre_evento: str


@dataclass(frozen=True)
class ImpactoInfo:
    """Nivel de impacto de un comportamiento.

    Attributes:
        id_impacto: Identificador del impacto.
        impacto: Nombre del impacto.
    """

    id_impacto: int
    impacto: str


@dataclass(frozen=True)
class DefinicionFiltro:
    """Filtro seleccionable de un reporte (metadatos para la vista).

    Attributes:
        tipo: Clase de filtro (``empresa``, ``estado``, ``fecha``, etc.).
        etiqueta: Texto del control en la interfaz.
        defecto: Valor por defecto para los controles numéricos, si aplica.
    """

    tipo: str
    etiqueta: str
    defecto: int | None = None


@dataclass(frozen=True)
class DefinicionReporte:
    """Reporte disponible con sus metadatos (sin la consulta SQL).

    Attributes:
        id: Identificador estable del reporte.
        nombre: Nombre legible del reporte.
        descripcion: Descripción para la interfaz.
        columnas: Columnas esperadas del reporte (formato de exportación).
        filtros: Filtros que acepta el reporte.
    """

    id: str
    nombre: str
    descripcion: str
    columnas: tuple[str, ...]
    filtros: tuple[DefinicionFiltro, ...]


@dataclass(frozen=True)
class SeleccionFiltros:
    """Valores ya tipados que la UI capturó para los filtros de un reporte.

    Todos los campos son opcionales: ``None`` significa "sin restricción". El
    repositorio traduce cada valor a su condición SQL y sus parámetros.

    Attributes:
        empresa: Identificador de empresa seleccionado.
        estado: Etiqueta de estado (``Vigente``/``Inactivo``).
        estado_activo: Etiqueta de actividad (``Activos``/``Cancelados``).
        tipologia: Identificador de tipología seleccionado.
        dias_vencer: Días de ventana para vencimientos.
        fecha_desde: Fecha inicial del rango.
        fecha_hasta: Fecha final del rango.
        tipo_evento: Identificador del tipo de evento seleccionado.
        impacto: Identificador del impacto seleccionado.
        codigo: Código de operador seleccionado.
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


# --- Definición interna de reportes (incluye la consulta SQL) ----------------
@dataclass(frozen=True)
class _FiltroReporte:
    """Filtro de un reporte con su columna SQL y su etiqueta.

    Attributes:
        tipo: Clase de filtro.
        columna: Columna o expresión SQL sobre la que aplica.
        etiqueta: Texto del control en la interfaz.
        defecto: Valor por defecto para los controles numéricos.
    """

    tipo: str
    columna: str
    etiqueta: str
    defecto: int | None = None


@dataclass(frozen=True)
class _Reporte:
    """Definición completa de un reporte, con su consulta SQL.

    Attributes:
        id: Identificador estable del reporte.
        nombre: Nombre legible.
        descripcion: Descripción para la interfaz.
        columnas: Columnas esperadas del reporte.
        consulta: Consulta base con el marcador ``WHERE 1=1``.
        filtros: Filtros que acepta el reporte.
    """

    id: str
    nombre: str
    descripcion: str
    columnas: tuple[str, ...]
    consulta: str
    filtros: tuple[_FiltroReporte, ...]


_COLUMNAS_UTRYT: tuple[str, ...] = (
    "METROCALI ID",
    "DOCUMENTTYPEID",
    "DOCUMENTNUMBER",
    "DRIVERNAME",
    "LASTNAME",
    "LASTNAME2",
    "STATEID",
    "TRANSPORTCONTRATISTID",
    "REGISTERDATE",
    "TIPOLOGY",
)
"""Columnas exigidas por el formato UTRYT (no se alteran)."""

_REPORTES: tuple[_Reporte, ...] = (
    _Reporte(
        id="utryt",
        nombre="Consolidado UTRYT",
        descripcion=(
            "Exportación de operadores con código, documento, nombre, estado, "
            "empresa y tipología (formato UTRYT)."
        ),
        columnas=_COLUMNAS_UTRYT,
        consulta="""
            SELECT dc.id_codigo AS "METROCALI ID", 1 AS "DOCUMENTTYPEID",
                   dc.id_persona AS "DOCUMENTNUMBER",
                   p.nombres AS "DRIVERNAME", p.primer_apellido AS "LASTNAME",
                   p.segundo_apellido AS "LASTNAME2",
                   CASE WHEN dc.id_vigencia = 1 THEN 1 ELSE 2 END AS "STATEID",
                   dc.id_empresa AS "TRANSPORTCONTRATISTID",
                   DATE(dc.fecha_registro) AS "REGISTERDATE",
                   dc.id_perfil_tipologia AS "TIPOLOGY"
            FROM dim_codigo dc
            LEFT JOIN dim_persona p ON dc.id_persona = p.id_persona
            WHERE 1=1
        """,
        filtros=(
            _FiltroReporte("empresa", "dc.id_empresa", "Empresa"),
            _FiltroReporte("estado", "dc.id_vigencia", "Estado"),
            _FiltroReporte("tipologia", "dc.id_perfil_tipologia", "Tipología"),
        ),
    ),
    _Reporte(
        id="operadores_empresa",
        nombre="Operadores por Empresa y Tipología",
        descripcion="Conteo de operadores agrupados por empresa y tipología con totales.",
        columnas=("Empresa", "Tipologia", "Codigos"),
        consulta="""
            SELECT e.nombre_empresa AS "Empresa", t.id_perfil_tipologia AS "Tipologia",
                   COUNT(*) AS "Codigos"
            FROM dim_codigo dc
            LEFT JOIN dim_empresa e ON dc.id_empresa = e.id_empresa
            LEFT JOIN dim_perfil_tipologia t
                ON dc.id_perfil_tipologia = t.id_perfil_tipologia
            WHERE 1=1
            GROUP BY e.nombre_empresa, t.id_perfil_tipologia
            ORDER BY e.nombre_empresa, t.id_perfil_tipologia
        """,
        filtros=(
            _FiltroReporte("empresa", "dc.id_empresa", "Empresa"),
            _FiltroReporte(
                "estado_activo",
                "dc.id_codigo",
                "Estado (Activo = sin cancelación)",
            ),
        ),
    ),
    _Reporte(
        id="licencias_vencer",
        nombre="Licencias por Vencer",
        descripcion="Licencias de conducción que vencen en los próximos N días.",
        columnas=(
            "Codigo",
            "Cedula",
            "Nombre",
            "Tipo Licencia",
            "Vencimiento",
            "Dias Restantes",
        ),
        consulta="""
            SELECT l.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   l.tipo AS "Tipo Licencia", DATE(l.vencimiento) AS "Vencimiento",
                   CAST(ROUND(JULIANDAY(l.vencimiento) - JULIANDAY('now')) AS INTEGER)
                       AS "Dias Restantes"
            FROM fact_licencias l
            LEFT JOIN dim_codigo c ON l.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            WHERE 1=1 AND l.vencimiento IS NOT NULL
        """,
        filtros=(
            _FiltroReporte(
                "dias_vencer",
                _COL_VENCIMIENTO_LICENCIA,
                "Días para vencimiento",
                DIAS_VENCIMIENTO_DEFECTO,
            ),
        ),
    ),
    _Reporte(
        id="eventos_tipo",
        nombre="Eventos por Tipo y Rango de Fechas",
        descripcion="Eventos de operadores por tipo en un rango de fechas.",
        columnas=("Codigo", "Cedula", "Nombre", "Evento", "Fecha", "Observacion"),
        consulta="""
            SELECT e.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   te.nombre_evento AS "Evento",
                   COALESCE(e.fecha_certificado, e.fecha_retiro, e.fecha_suspension,
                            e.fecha_observacion, e.fecha_registro) AS "Fecha",
                   e.observacion AS "Observacion"
            FROM fact_eventos_operador e
            LEFT JOIN dim_codigo c ON e.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            LEFT JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
            WHERE 1=1
        """,
        filtros=(
            _FiltroReporte("fecha", _COL_FECHA_EVENTOS, "Rango de fechas"),
            _FiltroReporte("tipo_evento", "e.id_tipo_evento", "Tipo de Evento"),
        ),
    ),
    _Reporte(
        id="reincidencias",
        nombre="Reincidencias con Determinación",
        descripcion="Casos de reincidencia con su determinación Metrocali.",
        columnas=(
            "Reincidencia",
            "Codigo",
            "Empresa",
            "Impacto",
            "Comportamiento",
            "Inicio",
            "Fin",
            "Determinacion",
        ),
        consulta="""
            SELECT r.id_reincidencia AS "Reincidencia", r.id_codigo AS "Codigo",
                   e.nombre_empresa AS "Empresa", i.impacto AS "Impacto",
                   c.comportamiento AS "Comportamiento", r.fecha_inicio AS "Inicio",
                   r.fecha_fin AS "Fin", r.determinacion_mc AS "Determinacion"
            FROM fact_reincidencia r
            LEFT JOIN dim_impacto i ON r.id_impacto = i.id_impacto
            LEFT JOIN dim_comportamiento c
                ON r.id_comportamiento = c.id_comportamiento
            LEFT JOIN dim_codigo dc ON r.id_codigo = dc.id_codigo
            LEFT JOIN dim_empresa e ON dc.id_empresa = e.id_empresa
            WHERE 1=1
        """,
        filtros=(
            _FiltroReporte("empresa", "dc.id_empresa", "Empresa"),
            _FiltroReporte("impacto", "r.id_impacto", "Impacto"),
        ),
    ),
    _Reporte(
        id="comportamientos_operador",
        nombre="Comportamientos por Operador",
        descripcion="Comportamientos registrados por operador en un rango de fechas.",
        columnas=(
            "Codigo",
            "Cedula",
            "Nombre",
            "Descripcion",
            "Caso",
            "Fecha",
            "Vehiculo",
            "Ruta",
        ),
        consulta="""
            SELECT f.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   d.descripcion_comportamiento AS "Descripcion",
                   f.caso_bitacora_ticket AS "Caso", f.fecha_evento AS "Fecha",
                   f.vehiculo AS "Vehiculo", f.ruta AS "Ruta"
            FROM fact_comportamiento f
            LEFT JOIN dim_detalle_comportamiento d ON f.id_jerarquia = d.id_jerarquia
            LEFT JOIN dim_codigo c ON f.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            WHERE 1=1
        """,
        filtros=(
            _FiltroReporte("codigo", "f.id_codigo", "Código de Operador"),
            _FiltroReporte("fecha", "DATE(f.fecha_evento)", "Rango de fechas"),
        ),
    ),
    _Reporte(
        id="certificados_vencer",
        nombre="Certificados por Vencer",
        descripcion=(
            "Certificados de operadores (eventos certificación, reactivación y "
            "renovación) que vencen en los próximos N días (vigencia 3 años)."
        ),
        columnas=(
            "Codigo",
            "Cedula",
            "Nombre",
            "Ultimo Evento",
            "Fecha Certificado",
            "Vencimiento",
            "Dias Restantes",
        ),
        consulta=f"""
            SELECT e.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   te.nombre_evento AS "Ultimo Evento",
                   DATE(e.fecha_certificado) AS "Fecha Certificado",
                   {_COL_VENCIMIENTO_CERTIFICADO} AS "Vencimiento",
                   CAST(ROUND(JULIANDAY({_COL_VENCIMIENTO_CERTIFICADO})
                       - JULIANDAY('now')) AS INTEGER) AS "Dias Restantes"
            FROM ({_SUBCONSULTA_ULTIMO_CERTIFICADO}) e
            LEFT JOIN dim_codigo c ON e.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            LEFT JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
            WHERE 1=1 AND e.rn = 1 AND c.id_codigo NOT IN (
                SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)
        """,
        filtros=(
            _FiltroReporte(
                "dias_vencer",
                _COL_VENCIMIENTO_CERTIFICADO,
                "Días para vencimiento",
                DIAS_VENCIMIENTO_DEFECTO,
            ),
        ),
    ),
    _Reporte(
        id="certificados_vencidos",
        nombre="Certificados Vencidos",
        descripcion=(
            "Operadores con certificado (eventos certificación, reactivación o "
            "renovación) vencido hace más de 3 años."
        ),
        columnas=(
            "Codigo",
            "Cedula",
            "Nombre",
            "Ultimo Evento",
            "Fecha Certificado",
            "Vencimiento",
            "Dias Vencido",
        ),
        consulta=f"""
            SELECT e.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   te.nombre_evento AS "Ultimo Evento",
                   DATE(e.fecha_certificado) AS "Fecha Certificado",
                   {_COL_VENCIMIENTO_CERTIFICADO} AS "Vencimiento",
                   CAST(ROUND(JULIANDAY('now')
                       - JULIANDAY({_COL_VENCIMIENTO_CERTIFICADO})) AS INTEGER)
                       AS "Dias Vencido"
            FROM ({_SUBCONSULTA_ULTIMO_CERTIFICADO}) e
            LEFT JOIN dim_codigo c ON e.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            LEFT JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
            WHERE 1=1 AND e.rn = 1 AND {_COL_VENCIMIENTO_CERTIFICADO} < DATE('now')
              AND c.id_codigo NOT IN (
                SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)
        """,
        filtros=(),
    ),
)

_CONSULTAS: dict[str, str] = {reporte.id: reporte.consulta for reporte in _REPORTES}
_FILTROS: dict[str, tuple[_FiltroReporte, ...]] = {
    reporte.id: reporte.filtros for reporte in _REPORTES
}


# --- Consultas de catálogos (parámetros enlazados) ---------------------------
_SQL_EMPRESAS = text("SELECT id_empresa, nombre_empresa FROM dim_empresa ORDER BY id_empresa")

_SQL_TIPOLOGIAS = text(
    "SELECT id_perfil_tipologia, autoriza_articulado, autoriza_padron, "
    "autoriza_complementario, autoriza_auxiliar "
    "FROM dim_perfil_tipologia ORDER BY id_perfil_tipologia"
)

_SQL_TIPOS_EVENTO = text(
    "SELECT id_tipo_evento, nombre_evento FROM dim_tipo_evento ORDER BY id_tipo_evento"
)

_SQL_IMPACTOS = text("SELECT id_impacto, impacto FROM dim_impacto ORDER BY id_impacto")

_SQL_AUDITORIA = text(
    "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:usuario, :accion, :detalles)"
)


# --- Funciones puras ---------------------------------------------------------
def construir_descripcion_tipologia(
    id_perfil_tipologia: int,
    articulado: bool,
    padron: bool,
    complementario: bool,
    auxiliar: bool,
) -> str:
    """Construye la descripción legible de una tipología de operador.

    Conserva el formato heredado: el identificador seguido de las
    autorizaciones habilitadas; si no hay ninguna, solo el identificador.

    Args:
        id_perfil_tipologia: Identificador de la tipología.
        articulado: Si autoriza la operación articulada.
        padron: Si autoriza el padrón.
        complementario: Si autoriza el servicio complementario.
        auxiliar: Si autoriza el servicio auxiliar.

    Returns:
        La descripción legible de la tipología.
    """
    partes: list[str] = []
    if articulado:
        partes.append("Articulado")
    if padron:
        partes.append("Padron")
    if complementario:
        partes.append("Complementario")
    if auxiliar:
        partes.append("Auxiliar")
    if not partes:
        return str(id_perfil_tipologia)
    return f"{id_perfil_tipologia} - {', '.join(partes)}"


def construir_consulta(consulta_base: str, condiciones: list[str]) -> str:
    """Inyecta las condiciones en la consulta base de un reporte.

    Las condiciones se agregaron con AND sobre el marcador ``WHERE 1=1`` que
    todas las consultas de reportes conservan.

    Args:
        consulta_base: Consulta base del reporte con el marcador ``WHERE 1=1``.
        condiciones: Condiciones SQL ya construidas (sin datos del usuario).

    Returns:
        La consulta lista para ejecutarse.
    """
    if not condiciones:
        return consulta_base
    where = " AND ".join(condiciones)
    return consulta_base.replace("WHERE 1=1", f"WHERE 1=1 AND {where}")


def generar_excel(df: pd.DataFrame, nombre: str) -> bytes:
    """Convierte un ``DataFrame`` en un libro de Excel en memoria.

    Args:
        df: Datos del reporte.
        nombre: Nombre del reporte; se usa como nombre de la hoja (máx. 30).

    Returns:
        El contenido binario del archivo ``.xlsx``.
    """
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        df.to_excel(escritor, index=False, sheet_name=nombre[:30])
        if not df.empty:
            resumen = pd.DataFrame({"Total Registros": [len(df)]})
            resumen.to_excel(escritor, index=False, sheet_name="Resumen", startrow=0)
    return salida.getvalue()


def generar_csv(df: pd.DataFrame) -> bytes:
    """Convierte un ``DataFrame`` en un archivo CSV en memoria.

    Args:
        df: Datos del reporte.

    Returns:
        El contenido binario del archivo ``.csv`` (UTF-8 con BOM).
    """
    return df.to_csv(index=False).encode("utf-8-sig")


# --- Repositorio -------------------------------------------------------------
class ReportesRepository:
    """Repositorio de reportes y exportaciones sobre la base de datos.

    Concentra toda la ejecución SQL de la vista de reportes. El motor se inyecta
    (por defecto se resuelve de forma perezosa desde
    :func:`certificado_operadores.db.get_engine`) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa el repositorio.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._engine = engine

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado al repositorio (inyectado o por defecto)."""
        if self._engine is None:
            # Import perezoso: evita cargar Streamlit cuando las pruebas inyectan motor.
            from certificado_operadores.db import get_engine

            self._engine = get_engine()
        return self._engine

    # --- RF-01: catálogos de filtros -----------------------------------------
    def listar_reportes(self) -> tuple[DefinicionReporte, ...]:
        """Lista los reportes disponibles con sus metadatos (sin la consulta SQL).

        Returns:
            Las definiciones públicas de los reportes.
        """
        return tuple(
            DefinicionReporte(
                id=reporte.id,
                nombre=reporte.nombre,
                descripcion=reporte.descripcion,
                columnas=reporte.columnas,
                filtros=tuple(
                    DefinicionFiltro(filtro.tipo, filtro.etiqueta, filtro.defecto)
                    for filtro in reporte.filtros
                ),
            )
            for reporte in _REPORTES
        )

    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas ordenadas por identificador.

        Returns:
            Las empresas del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_EMPRESAS).mappings().all()
        return [
            EmpresaInfo(
                id_empresa=int(fila["id_empresa"]),
                nombre_empresa=str(fila["nombre_empresa"] or ""),
            )
            for fila in filas
        ]

    def listar_tipologias(self) -> list[TipologiaInfo]:
        """Lista las tipologías de operador ordenadas por identificador.

        Returns:
            Las tipologías con su descripción legible.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_TIPOLOGIAS).mappings().all()
        return [
            TipologiaInfo(
                id_perfil_tipologia=int(fila["id_perfil_tipologia"]),
                descripcion=construir_descripcion_tipologia(
                    int(fila["id_perfil_tipologia"]),
                    bool(fila["autoriza_articulado"]),
                    bool(fila["autoriza_padron"]),
                    bool(fila["autoriza_complementario"]),
                    bool(fila["autoriza_auxiliar"]),
                ),
            )
            for fila in filas
        ]

    def listar_estados(self) -> list[str]:
        """Lista las etiquetas del filtro de estado.

        Returns:
            Las opciones de estado disponibles.
        """
        return list(OPCIONES_ESTADO)

    def listar_tipos_evento(self) -> list[TipoEventoInfo]:
        """Lista los tipos de evento ordenados por identificador.

        Returns:
            Los tipos de evento del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_TIPOS_EVENTO).mappings().all()
        return [
            TipoEventoInfo(
                id_tipo_evento=int(fila["id_tipo_evento"]),
                nombre_evento=str(fila["nombre_evento"] or ""),
            )
            for fila in filas
        ]

    def listar_impactos(self) -> list[ImpactoInfo]:
        """Lista los impactos ordenados por identificador.

        Returns:
            Los impactos del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_IMPACTOS).mappings().all()
        return [
            ImpactoInfo(
                id_impacto=int(fila["id_impacto"]),
                impacto=str(fila["impacto"] or ""),
            )
            for fila in filas
        ]

    # --- RF-02: consultas de reportes ----------------------------------------
    def construir_condiciones(
        self, id_reporte: str, seleccion: SeleccionFiltros
    ) -> tuple[list[str], dict[str, object]]:
        """Traduce la selección de filtros a condiciones y parámetros SQL.

        Args:
            id_reporte: Identificador del reporte.
            seleccion: Valores tipados capturados por la interfaz.

        Returns:
            Una tupla ``(condiciones, parametros)`` con los fragmentos SQL (sin
            datos del usuario) y los valores enlazados.

        Raises:
            ValueError: Si el identificador del reporte no existe.
        """
        filtros = _FILTROS.get(id_reporte)
        if filtros is None:
            raise ValueError(f"Reporte desconocido: {id_reporte}")
        condiciones: list[str] = []
        parametros: dict[str, object] = {}
        for filtro in filtros:
            tipo = filtro.tipo
            if tipo == "empresa" and seleccion.empresa is not None:
                condiciones.append(f"{filtro.columna} = :emp")
                parametros["emp"] = seleccion.empresa
            elif tipo == "estado" and seleccion.estado in ESTADO_A_VIGENCIA:
                condiciones.append(f"{filtro.columna} = :est")
                parametros["est"] = ESTADO_A_VIGENCIA[seleccion.estado]
            elif tipo == "estado_activo" and seleccion.estado_activo:
                operador = "NOT IN" if seleccion.estado_activo == "Activos" else "IN"
                condiciones.append(f"{filtro.columna} {operador} ({_SUBCONSULTA_CANCELACION})")
                parametros["cancelacion"] = TIPO_EVENTO_CANCELACION
            elif tipo == "tipologia" and seleccion.tipologia is not None:
                condiciones.append(f"{filtro.columna} = :tip")
                parametros["tip"] = seleccion.tipologia
            elif tipo == "dias_vencer" and seleccion.dias_vencer is not None:
                # Ventana de vencimiento con la aritmética de fechas de SQLite:
                # se concatenan los días enlazados para formar el modificador.
                fragmento = (
                    f"{filtro.columna} BETWEEN DATE('now') AND DATE('now', '+' || :dias || ' days')"
                )
                condiciones.append(fragmento)
                parametros["dias"] = int(seleccion.dias_vencer)
            elif tipo == "fecha" and seleccion.fecha_desde and seleccion.fecha_hasta:
                condiciones.append(f"{filtro.columna} BETWEEN :fdesde AND :fhasta")
                parametros["fdesde"] = seleccion.fecha_desde.strftime("%Y-%m-%d")
                parametros["fhasta"] = seleccion.fecha_hasta.strftime("%Y-%m-%d")
            elif tipo == "tipo_evento" and seleccion.tipo_evento is not None:
                condiciones.append(f"{filtro.columna} = :tev")
                parametros["tev"] = seleccion.tipo_evento
            elif tipo == "impacto" and seleccion.impacto is not None:
                condiciones.append(f"{filtro.columna} = :imp")
                parametros["imp"] = seleccion.impacto
            elif tipo == "codigo" and seleccion.codigo is not None:
                condiciones.append(f"{filtro.columna} = :cod")
                parametros["cod"] = seleccion.codigo
        return condiciones, parametros

    def ejecutar_reporte(self, id_reporte: str, seleccion: SeleccionFiltros) -> pd.DataFrame:
        """Ejecuta un reporte con sus filtros y devuelve los datos.

        Args:
            id_reporte: Identificador del reporte.
            seleccion: Valores tipados capturados por la interfaz.

        Returns:
            Los datos del reporte.

        Raises:
            ValueError: Si el identificador del reporte no existe.
        """
        condiciones, parametros = self.construir_condiciones(id_reporte, seleccion)
        consulta = construir_consulta(_CONSULTAS[id_reporte], condiciones)
        with self.motor.connect() as conexion:
            return pd.read_sql(text(consulta), conexion, params=parametros or None)

    # --- RF-03: auditoría de exportaciones -----------------------------------
    def registrar_exportacion(self, usuario: str, nombre_reporte: str, total: int) -> None:
        """Registra en la auditoría la exportación de un reporte.

        Args:
            usuario: Usuario que exporta.
            nombre_reporte: Nombre del reporte exportado.
            total: Número de registros exportados.
        """
        with self.motor.begin() as conexion:
            conexion.execute(
                _SQL_AUDITORIA,
                {
                    "usuario": usuario,
                    "accion": ACCION_EXPORTAR_REPORTE,
                    "detalles": f"{nombre_reporte} - {total} registros",
                },
            )


__all__ = [
    "ACCION_EXPORTAR_REPORTE",
    "DIAS_VENCIMIENTO_DEFECTO",
    "DIAS_VENCIMIENTO_MAXIMO",
    "DIAS_VENCIMIENTO_MINIMO",
    "OPCIONES_ESTADO",
    "OPCIONES_ESTADO_ACTIVO",
    "TIPO_MIME_CSV",
    "TIPO_MIME_EXCEL",
    "DefinicionFiltro",
    "DefinicionReporte",
    "EmpresaInfo",
    "ImpactoInfo",
    "ReportesRepository",
    "SeleccionFiltros",
    "TipoEventoInfo",
    "TipologiaInfo",
    "construir_consulta",
    "construir_descripcion_tipologia",
    "generar_csv",
    "generar_excel",
]
