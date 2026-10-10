"""Fachada de acceso a datos de operadores (patrón Facade).

Expone los casos de uso del sistema —consultas de operadores, validación de
certificados y estadísticas básicas— aislando a la interfaz del acceso directo
a la base de datos. La UI (incluida Streamlit) debe invocar **únicamente** esta
fachada:

    UI → Facade → Dominio → Infraestructura

Todas las consultas usan conexiones administradas por contexto y parámetros
enlazados (nunca SQL construido con datos del usuario).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import TextClause, bindparam, text
from sqlalchemy.exc import SQLAlchemyError

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


# --- Constantes del dominio -------------------------------------------------
VIGENCIA_ACTIVA = 1
"""Identificador de la vigencia "vigente" en ``dim_vigencia_registro``."""

VIGENCIA_ANULADA = 2
"""Identificador de la vigencia "anulado" en ``dim_vigencia_registro``."""

ANIOS_VIGENCIA_CERTIFICADO = 3
"""Años de validez de un certificado de idoneidad."""

DIAS_ALERTA_VENCIMIENTO = 90
"""Umbral de días para marcar un certificado como "por vencer"."""

TIPOS_EVENTO_CERTIFICADO = (1, 2, 3)
"""Tipos de evento que otorgan/renuevan el certificado: certificación,
reactivación y renovación."""

TIPO_EVENTO_CANCELACION = 7
"""Tipo de evento que cancela el certificado del operador."""


@dataclass(frozen=True)
class OperadorInfo:
    """Datos consolidados de un operador y su código de operación."""

    codigo: int
    cedula: int
    nombres: str
    primer_apellido: str
    segundo_apellido: str
    genero: str
    id_empresa: int
    nombre_empresa: str
    id_perfil_tipologia: int
    id_vigencia: int

    def nombre_completo(self) -> str:
        """Devuelve el nombre completo del operador en una sola cadena."""
        partes = (self.nombres, self.primer_apellido, self.segundo_apellido)
        return " ".join(parte for parte in partes if parte).strip()


@dataclass(frozen=True)
class EstadoCertificado:
    """Resultado de la validación del certificado de un operador."""

    codigo: int
    fecha_certificado: date | None
    fecha_vencimiento: date | None
    dias_restantes: int | None
    estado: str
    cancelado: bool


@dataclass(frozen=True)
class EstadisticasBasicas:
    """Conteos generales del sistema para tableros y resúmenes."""

    total_operadores: int
    operadores_vigentes: int
    operadores_anulados: int
    total_empresas: int
    total_licencias: int


# --- Consultas SQL (parámetros enlazados, sin concatenar datos) -------------
_SQL_OPERADOR_BASE = """
    SELECT c.id_codigo, c.id_persona, p.nombres, p.primer_apellido,
           p.segundo_apellido, p.genero, c.id_empresa, e.nombre_empresa,
           c.id_perfil_tipologia, c.id_vigencia
    FROM dim_codigo AS c
    LEFT JOIN dim_persona AS p ON p.id_persona = c.id_persona
    LEFT JOIN dim_empresa AS e ON e.id_empresa = c.id_empresa
    WHERE {condicion}
    ORDER BY c.id_vigencia ASC, c.id_codigo ASC
    LIMIT 1
"""

_SQL_OPERADOR_POR_CEDULA = text(_SQL_OPERADOR_BASE.format(condicion="c.id_persona = :cedula"))
_SQL_OPERADOR_POR_CODIGO = text(_SQL_OPERADOR_BASE.format(condicion="c.id_codigo = :codigo"))

_SQL_ULTIMO_CERTIFICADO = text(
    """
    SELECT MAX(fecha_certificado) AS ultima
    FROM fact_eventos_operador
    WHERE id_codigo = :codigo
      AND id_tipo_evento IN :tipos
      AND fecha_certificado IS NOT NULL
      AND fecha_certificado <> ''
    """
).bindparams(bindparam("tipos", expanding=True))

_SQL_TIENE_CANCELACION = text(
    """
    SELECT COUNT(*) AS total
    FROM fact_eventos_operador
    WHERE id_codigo = :codigo AND id_tipo_evento = :tipo_cancelacion
    """
)


class OperadoresFacade:
    """Fachada única de consulta de operadores sobre SQLite.

    Agrupa las operaciones de lectura que la UI necesita, de modo que ninguna
    vista conozca el motor ni el SQL. El motor se inyecta (por defecto se toma
    de :func:`certificado_operadores.db.get_engine`) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa la fachada.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._engine = engine

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        if self._engine is None:
            # Import perezoso: evita cargar Streamlit cuando las pruebas inyectan motor.
            from certificado_operadores.db import get_engine

            self._engine = get_engine()
        return self._engine

    def verificar_conexion(self) -> bool:
        """Verifica el estado de la conexión a la base de datos.

        Returns:
            ``True`` si se puede abrir una conexión y ejecutar una consulta
            trivial; ``False`` ante cualquier error de SQLAlchemy.
        """
        try:
            with self.motor.connect() as conexion:
                conexion.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def obtener_operador_por_cedula(self, cedula: int) -> OperadorInfo | None:
        """Consulta un operador por su número de cédula.

        Args:
            cedula: Número de documento (``dim_persona.id_persona``).

        Returns:
            El operador vigente de menor código, o ``None`` si no existe.
        """
        fila = self._consultar_operador(_SQL_OPERADOR_POR_CEDULA, {"cedula": cedula})
        return fila

    def obtener_operador_por_codigo(self, codigo: int) -> OperadorInfo | None:
        """Consulta un operador por su código de operación.

        Args:
            codigo: Código de operación (``dim_codigo.id_codigo``).

        Returns:
            El operador asociado, o ``None`` si no existe.
        """
        return self._consultar_operador(_SQL_OPERADOR_POR_CODIGO, {"codigo": codigo})

    def validar_certificado(self, codigo: int) -> EstadoCertificado:
        """Valida el certificado de idoneidad de un operador.

        Aplica la regla de negocio: el certificado dura
        :data:`ANIOS_VIGENCIA_CERTIFICADO` años desde el último evento de
        certificación, reactivación o renovación; un evento de cancelación lo
        deja sin efecto.

        Args:
            codigo: Código de operación del operador.

        Returns:
            El estado calculado: ``VIGENTE``, ``POR_VENCER``, ``VENCIDO``,
            ``SIN_CERTIFICADO`` o ``CANCELADO``.
        """
        with self.motor.connect() as conexion:
            ultima = conexion.execute(
                _SQL_ULTIMO_CERTIFICADO, {"codigo": codigo, "tipos": list(TIPOS_EVENTO_CERTIFICADO)}
            ).scalar_one()
            cancelaciones = conexion.execute(
                _SQL_TIENE_CANCELACION,
                {"codigo": codigo, "tipo_cancelacion": TIPO_EVENTO_CANCELACION},
            ).scalar_one()

        cancelado = int(cancelaciones) > 0
        fecha_certificado = _parsear_fecha(ultima)

        if cancelado:
            return EstadoCertificado(codigo, fecha_certificado, None, None, "CANCELADO", True)
        if fecha_certificado is None:
            return EstadoCertificado(codigo, None, None, None, "SIN_CERTIFICADO", False)

        vencimiento = _sumar_anios(fecha_certificado, ANIOS_VIGENCIA_CERTIFICADO)
        dias_restantes = (vencimiento - date.today()).days
        estado = _clasificar_estado(dias_restantes)
        return EstadoCertificado(
            codigo, fecha_certificado, vencimiento, dias_restantes, estado, False
        )

    def estadisticas_basicas(self) -> EstadisticasBasicas:
        """Calcula conteos generales de operadores, empresas y licencias.

        Returns:
            Las estadísticas básicas. Si el esquema aún no está cargado devuelve
            conteos en cero, en lugar de propagar el error, para no romper los
            tableros.
        """
        try:
            with self.motor.connect() as conexion:
                total = _contar(conexion, "SELECT COUNT(*) FROM dim_codigo")
                vigentes = _contar(
                    conexion,
                    "SELECT COUNT(*) FROM dim_codigo WHERE id_vigencia = :vigencia",
                    {"vigencia": VIGENCIA_ACTIVA},
                )
                anulados = _contar(
                    conexion,
                    "SELECT COUNT(*) FROM dim_codigo WHERE id_vigencia = :vigencia",
                    {"vigencia": VIGENCIA_ANULADA},
                )
                empresas = _contar(conexion, "SELECT COUNT(*) FROM dim_empresa")
                licencias = _contar(conexion, "SELECT COUNT(*) FROM fact_licencias")
        except SQLAlchemyError:
            return EstadisticasBasicas(0, 0, 0, 0, 0)
        return EstadisticasBasicas(total, vigentes, anulados, empresas, licencias)

    def _consultar_operador(
        self, sentencia: TextClause, parametros: dict[str, int]
    ) -> OperadorInfo | None:
        """Ejecuta una consulta de operador y mapea la fila al DTO.

        Args:
            sentencia: Sentencia SQLAlchemy parametrizada.
            parametros: Valores enlazados a la sentencia.

        Returns:
            El operador mapeado o ``None`` si no hay filas.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(sentencia, parametros).mappings().first()
        if fila is None:
            return None
        return OperadorInfo(
            codigo=int(fila["id_codigo"]),
            cedula=int(fila["id_persona"]),
            nombres=str(fila["nombres"] or ""),
            primer_apellido=str(fila["primer_apellido"] or ""),
            segundo_apellido=str(fila["segundo_apellido"] or ""),
            genero=str(fila["genero"] or ""),
            id_empresa=int(fila["id_empresa"]),
            nombre_empresa=str(fila["nombre_empresa"] or ""),
            id_perfil_tipologia=int(fila["id_perfil_tipologia"]),
            id_vigencia=int(fila["id_vigencia"]),
        )


def _parsear_fecha(valor: object) -> date | None:
    """Convierte un valor de fecha de SQLite a ``datetime.date``.

    Args:
        valor: Cadena ISO (``YYYY-MM-DD`` o marca de tiempo) o ``None``.

    Returns:
        La fecha interpretada, o ``None`` si el valor está vacío o es inválido.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def _sumar_anios(fecha: date, anios: int) -> date:
    """Suma años a una fecha ajustando el 29 de febrero cuando aplica.

    Args:
        fecha: Fecha base.
        anios: Años a sumar.

    Returns:
        La fecha resultante.
    """
    try:
        return fecha.replace(year=fecha.year + anios)
    except ValueError:
        # 29 de febrero en un año no bisiesto: se ajusta al 28 de febrero.
        return fecha.replace(year=fecha.year + anios, day=28)


def _clasificar_estado(dias_restantes: int) -> str:
    """Clasifica el estado del certificado según los días restantes.

    Args:
        dias_restantes: Días que faltan para el vencimiento (negativos = vencido).

    Returns:
        Uno de ``VIGENTE``, ``POR_VENCER`` o ``VENCIDO``.
    """
    if dias_restantes < 0:
        return "VENCIDO"
    if dias_restantes <= DIAS_ALERTA_VENCIMIENTO:
        return "POR_VENCER"
    return "VIGENTE"


def _contar(conexion: Connection, sentencia: str, parametros: dict[str, int] | None = None) -> int:
    """Ejecuta un ``COUNT(*)`` y devuelve el entero resultante.

    Args:
        conexion: Conexión SQLAlchemy activa.
        sentencia: Consulta ``COUNT`` parametrizable.
        parametros: Valores enlazados opcionales.

    Returns:
        El conteo como entero.
    """
    resultado = conexion.execute(text(sentencia), parametros or {}).scalar_one()
    return int(resultado)
