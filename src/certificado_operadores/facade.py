"""Fachada de acceso a datos de operadores (patrón Facade).

Expone los casos de uso del sistema —consultas de operadores, validación de
certificados y estadísticas básicas— delegando toda la persistencia en el
repositorio de infraestructura. La UI (incluida Streamlit) debe invocar
**únicamente** esta fachada:

    UI → Facade → Dominio → Infraestructura

La fachada no ejecuta SQLAlchemy ni contiene reglas de negocio: solo orquesta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from certificado_operadores.infra.repository import OperadoresRepository

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from certificado_operadores.domain.models import (
        EstadisticasBasicas,
        EstadoCertificado,
        OperadorInfo,
    )


class OperadoresFacade:
    """Fachada única de consulta de operadores.

    Agrupa las operaciones de lectura que la UI necesita, de modo que ninguna
    vista conozca el motor, el SQL ni el esquema. Delega la totalidad del acceso
    a datos en :class:`OperadoresRepository`. El motor se inyecta (por defecto se
    toma de :func:`certificado_operadores.db.get_engine`) para facilitar las
    pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa la fachada.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._repositorio = OperadoresRepository(engine)

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        return self._repositorio.motor

    def verificar_conexion(self) -> bool:
        """Verifica el estado de la conexión a la base de datos.

        Returns:
            ``True`` si se puede abrir una conexión y ejecutar una consulta
            trivial; ``False`` ante cualquier error de SQLAlchemy.
        """
        return self._repositorio.verificar_conexion()

    def obtener_operador_por_cedula(self, cedula: int) -> OperadorInfo | None:
        """Consulta un operador por su número de cédula.

        Args:
            cedula: Número de documento (``dim_persona.id_persona``).

        Returns:
            El operador vigente de menor código, o ``None`` si no existe.
        """
        return self._repositorio.obtener_operador_por_cedula(cedula)

    def obtener_operador_por_codigo(self, codigo: int) -> OperadorInfo | None:
        """Consulta un operador por su código de operación.

        Args:
            codigo: Código de operación (``dim_codigo.id_codigo``).

        Returns:
            El operador asociado, o ``None`` si no existe.
        """
        return self._repositorio.obtener_operador_por_codigo(codigo)

    def validar_certificado(self, codigo: int) -> EstadoCertificado:
        """Valida el certificado de idoneidad de un operador.

        Args:
            codigo: Código de operación del operador.

        Returns:
            El estado calculado: ``VIGENTE``, ``POR_VENCER``, ``VENCIDO``,
            ``SIN_CERTIFICADO`` o ``CANCELADO``.
        """
        return self._repositorio.validar_certificado(codigo)

    def estadisticas_basicas(self) -> EstadisticasBasicas:
        """Calcula conteos generales de operadores, empresas y licencias.

        Returns:
            Las estadísticas básicas. Si el esquema aún no está cargado devuelve
            conteos en cero, en lugar de propagar el error, para no romper los
            tableros.
        """
        return self._repositorio.estadisticas_basicas()
