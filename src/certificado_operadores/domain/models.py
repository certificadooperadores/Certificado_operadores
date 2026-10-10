"""Modelos y reglas de negocio del dominio de operadores.

Capa de **dominio**: define los DTOs (``dataclasses`` inmutables), las constantes
de negocio y las funciones puras de fechas y estados. No conoce SQLAlchemy, la
base de datos ni la interfaz gráfica; es el núcleo independiente del sistema:

    UI → Facade → Dominio → Infraestructura
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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

ESTADO_VIGENTE = "VIGENTE"
"""Estado de un certificado dentro del periodo de vigencia."""

ESTADO_POR_VENCER = "POR_VENCER"
"""Estado de un certificado próximo a vencer (dentro del umbral de alerta)."""

ESTADO_VENCIDO = "VENCIDO"
"""Estado de un certificado cuyo periodo de vigencia ya expiró."""

ESTADO_SIN_CERTIFICADO = "SIN_CERTIFICADO"
"""Estado de un operador sin eventos de certificación."""

ESTADO_CANCELADO = "CANCELADO"
"""Estado de un operador con un evento de cancelación."""


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


def _parsear_fecha(valor: object) -> date | None:
    """Convierte un valor de fecha almacenado como texto a ``datetime.date``.

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
        return ESTADO_VENCIDO
    if dias_restantes <= DIAS_ALERTA_VENCIMIENTO:
        return ESTADO_POR_VENCER
    return ESTADO_VIGENTE


def calcular_estado_certificado(
    codigo: int, ultima_certificacion: object, cancelado: bool
) -> EstadoCertificado:
    """Calcula el estado del certificado a partir de los datos crudos.

    Aplica la regla de negocio: el certificado dura
    :data:`ANIOS_VIGENCIA_CERTIFICADO` años desde la última certificación,
    reactivación o renovación; un evento de cancelación lo deja sin efecto.

    Args:
        codigo: Código de operación del operador.
        ultima_certificacion: Fecha cruda del último evento que certifica.
        cancelado: ``True`` si el operador tiene un evento de cancelación.

    Returns:
        El estado calculado: ``VIGENTE``, ``POR_VENCER``, ``VENCIDO``,
        ``SIN_CERTIFICADO`` o ``CANCELADO``.
    """
    fecha_certificado = _parsear_fecha(ultima_certificacion)

    if cancelado:
        return EstadoCertificado(codigo, fecha_certificado, None, None, ESTADO_CANCELADO, True)
    if fecha_certificado is None:
        return EstadoCertificado(codigo, None, None, None, ESTADO_SIN_CERTIFICADO, False)

    vencimiento = _sumar_anios(fecha_certificado, ANIOS_VIGENCIA_CERTIFICADO)
    dias_restantes = (vencimiento - date.today()).days
    estado = _clasificar_estado(dias_restantes)
    return EstadoCertificado(codigo, fecha_certificado, vencimiento, dias_restantes, estado, False)
