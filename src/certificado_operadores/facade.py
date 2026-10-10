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

from sqlalchemy.exc import SQLAlchemyError

from certificado_operadores.domain.models import (
    MENSAJE_OPERADOR_CAMPOS_OBLIGATORIOS,
    MENSAJE_OPERADOR_CREADO,
    MENSAJE_OPERADOR_DUPLICADO,
    MENSAJE_OPERADOR_ERROR,
    ResultadoOperador,
)
from certificado_operadores.infra.repository import OperadoresRepository

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from certificado_operadores.domain.models import (
        EstadisticasBasicas,
        EstadoCertificado,
        OperadorInfo,
        RegistroOperador,
    )
    from certificado_operadores.infra.reportes_repository import EmpresaInfo, TipologiaInfo


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

    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas concesionarias oficiales.

        Returns:
            Las empresas disponibles para el desplegable del formulario.
        """
        return self._repositorio.listar_empresas()

    def listar_tipologias(self) -> list[TipologiaInfo]:
        """Lista las tipologías de bus oficiales con su descripción.

        Returns:
            Las tipologías disponibles para el desplegable del formulario.
        """
        return self._repositorio.listar_tipologias()

    def guardar_operador(self, registro: RegistroOperador, usuario: str = "") -> ResultadoOperador:
        """Persiste un operador validando duplicados y campos obligatorios.

        Caso de uso de la spec 023: valida que los datos obligatorios estén
        presentes, impide registrar una segunda vigencia para una cédula que ya
        tiene un código vigente y delega la escritura en el repositorio. Devuelve
        un resultado con mensaje listo para la interfaz en lugar de propagar la
        excepción de persistencia.

        Args:
            registro: Datos del operador capturados por el formulario.
            usuario: Usuario que realiza el guardado (para auditoría).

        Returns:
            El resultado del guardado con el código asignado cuando tiene éxito.
        """
        if not self._campos_obligatorios(registro):
            return ResultadoOperador(False, MENSAJE_OPERADOR_CAMPOS_OBLIGATORIOS)
        try:
            if self._repositorio.existe_operador_vigente(registro.cedula):
                return ResultadoOperador(False, MENSAJE_OPERADOR_DUPLICADO)
            codigo = self._repositorio.crear_operador(registro, usuario)
        except SQLAlchemyError:
            return ResultadoOperador(False, MENSAJE_OPERADOR_ERROR)
        return ResultadoOperador(True, MENSAJE_OPERADOR_CREADO, codigo)

    @staticmethod
    def _campos_obligatorios(registro: RegistroOperador) -> bool:
        """Indica si el registro trae todos los datos obligatorios.

        Args:
            registro: Datos del operador.

        Returns:
            ``True`` si la cédula, los nombres, los apellidos, la empresa y la
            tipología están informados.
        """
        return bool(
            registro.cedula
            and registro.nombres.strip()
            and registro.primer_apellido.strip()
            and registro.id_empresa
            and registro.id_perfil_tipologia
        )
