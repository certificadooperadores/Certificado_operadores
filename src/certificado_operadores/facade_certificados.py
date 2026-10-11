"""Fachada de casos de uso de certificados (patrón Facade, spec 025).

Expone el registro de eventos, el listado de catálogos auxiliares, la búsqueda
del operador activo y la validación (alertas) del certificado de idoneidad,
delegando toda la persistencia en los repositorios de infraestructura. La UI de
gestión de certificados consume **exclusivamente** esta fachada:

    UI → Facade → Dominio → Infraestructura

La fachada no ejecuta SQL ni contiene reglas de negocio: solo orquesta y
reexporta los DTOs y constantes que necesita la vista.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from certificado_operadores.infra.catalogos_repository import VehiculoInfo
from certificado_operadores.infra.certificados_repository import (
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
    OperadorActivoInfo,
)
from certificado_operadores.infra.eventos_repository import TipoEventoInfo
from certificado_operadores.infra.repository import OperadoresRepository

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from certificado_operadores.domain.models import EstadoCertificado

__all__ = [
    "ACCION_CARGA_MASIVA",
    "TIPO_EVENTO_ADVERTENCIA",
    "TIPO_EVENTO_CANCELACION",
    "TIPO_EVENTO_CERTIFICACION",
    "TIPO_EVENTO_CONDICIONAMIENTO",
    "TIPO_EVENTO_OBSERVACION",
    "TIPO_EVENTO_REACTIVACION",
    "TIPO_EVENTO_RENOVACION",
    "TIPO_EVENTO_RESTRICCION_MEDICA",
    "TIPO_EVENTO_SUSPENSION",
    "CertificadosFacade",
    "DatosEvento",
    "OperadorActivoInfo",
    "TipoEventoInfo",
    "VehiculoInfo",
]


class CertificadosFacade:
    """Fachada única de los casos de uso de certificados.

    Encapsula :class:`CertificadosRepository` —catálogos, operador activo y
    registro de eventos— y :class:`OperadoresRepository` para el cálculo del
    estado (alertas) del certificado. El motor se inyecta (por defecto se toma
    del configurado en ``db``) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa la fachada con los repositorios que orquesta.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._certificados = CertificadosRepository(engine)
        self._operadores = OperadoresRepository(engine)

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        return self._certificados.motor

    def listar_tipos_evento(self) -> list[TipoEventoInfo]:
        """Lista los tipos de evento disponibles para el registro."""
        return self._certificados.listar_tipos_evento()

    def listar_vehiculos(self) -> list[VehiculoInfo]:
        """Lista los vehículos evaluables del catálogo."""
        return self._certificados.listar_vehiculos()

    def listar_evaluadores(self) -> list[str]:
        """Lista los evaluadores históricos para el formulario."""
        return self._certificados.listar_evaluadores()

    def buscar_operador_activo_por_codigo(self, codigo: int) -> OperadorActivoInfo | None:
        """Busca el operador activo por su código de operación."""
        return self._certificados.buscar_operador_activo_por_codigo(codigo)

    def buscar_operador_activo_por_cedula(self, cedula: int) -> OperadorActivoInfo | None:
        """Busca el operador activo por su número de cédula."""
        return self._certificados.buscar_operador_activo_por_cedula(cedula)

    def registrar_evento(self, datos: DatosEvento, usuario: str) -> int:
        """Registra un evento individual en el historial del operador."""
        return self._certificados.registrar_evento(datos, usuario)

    def registrar_eventos(
        self,
        eventos: list[DatosEvento],
        usuario: str,
        accion: str = ACCION_CARGA_MASIVA,
        detalles: str = "",
    ) -> int:
        """Registra de forma masiva una lista de eventos con auditoría."""
        return self._certificados.registrar_eventos(eventos, usuario, accion, detalles)

    def validar_certificado(self, codigo: int) -> EstadoCertificado:
        """Calcula el estado (alerta) del certificado de un operador.

        Args:
            codigo: Código de operación del operador.

        Returns:
            El estado calculado: ``VIGENTE``, ``POR_VENCER``, ``VENCIDO``,
            ``SIN_CERTIFICADO`` o ``CANCELADO``.
        """
        return self._operadores.validar_certificado(codigo)
