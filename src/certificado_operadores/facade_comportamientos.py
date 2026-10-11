"""Fachada de casos de uso de comportamientos (patrón Facade, spec 025).

Expone el registro individual y masivo de comportamientos, la evaluación de
reincidencias y el registro de acciones de Metrocali, delegando toda la
persistencia en :class:`ComportamientosRepository`. La UI del reporte de
comportamientos consume **exclusivamente** esta fachada:

    UI → Facade → Dominio → Infraestructura

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import TYPE_CHECKING

from certificado_operadores.infra.comportamientos_repository import (
    AccionReincidencia,
    ComportamientoReincidenciaInfo,
    ComportamientosRepository,
    DatosComportamiento,
    DetalleComportamientoInfo,
    DetalleReincidenciaInfo,
    EmpresaInfo,
    HechoComportamientoInfo,
    ImpactoInfo,
    OperadorComportamientoInfo,
    ReincidenciaAccionInfo,
    ReincidenciaInfo,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

__all__ = [
    "AccionReincidencia",
    "ComportamientosFacade",
    "DatosComportamiento",
    "DetalleComportamientoInfo",
    "DetalleReincidenciaInfo",
    "ReincidenciaInfo",
]


class ComportamientosFacade:
    """Fachada única de los casos de uso de comportamientos y reincidencias.

    Encapsula :class:`ComportamientosRepository` para que la vista nunca
    conozca el motor ni el esquema. El motor se inyecta (por defecto se toma del
    configurado en ``db``) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa la fachada sobre el repositorio de comportamientos.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._repositorio = ComportamientosRepository(engine)

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        return self._repositorio.motor

    def buscar_operador_por_codigo(self, codigo: int) -> OperadorComportamientoInfo | None:
        """Busca un operador por su código de operación activo."""
        return self._repositorio.buscar_operador_por_codigo(codigo)

    def buscar_operador_por_cedula(self, cedula: int) -> OperadorComportamientoInfo | None:
        """Busca un operador por cédula y devuelve su código activo más reciente."""
        return self._repositorio.buscar_operador_por_cedula(cedula)

    def listar_detalles_comportamiento(self) -> list[DetalleComportamientoInfo]:
        """Lista las jerarquías de comportamiento ordenadas por descripción."""
        return self._repositorio.listar_detalles_comportamiento()

    def registrar_comportamiento(self, datos: DatosComportamiento, usuario: str) -> int:
        """Registra un comportamiento individual y su auditoría."""
        return self._repositorio.registrar_comportamiento(datos, usuario)

    def resolver_codigo_activo(self, codigo: int) -> int | None:
        """Devuelve el código si está activo en ``dim_codigo``."""
        return self._repositorio.resolver_codigo_activo(codigo)

    def resolver_jerarquia_por_descripcion(self, descripcion: str) -> int | None:
        """Resuelve la jerarquía de comportamiento por su descripción exacta."""
        return self._repositorio.resolver_jerarquia_por_descripcion(descripcion)

    def buscar_comportamiento_por_caso(self, caso: str) -> int | None:
        """Busca el comportamiento existente con un ``caso_bitacora_ticket``."""
        return self._repositorio.buscar_comportamiento_por_caso(caso)

    def guardar_comportamientos(
        self, filas: Sequence[DatosComportamiento], usuario: str
    ) -> tuple[int, int]:
        """Valida y guarda la carga masiva de comportamientos desde Excel."""
        return self._repositorio.guardar_comportamientos(filas, usuario)

    def listar_impactos(self) -> list[ImpactoInfo]:
        """Lista los impactos con máximo mayor que cero."""
        return self._repositorio.listar_impactos()

    def listar_comportamientos_por_impacto(
        self, id_impacto: int
    ) -> list[ComportamientoReincidenciaInfo]:
        """Lista los comportamientos asociados a un impacto."""
        return self._repositorio.listar_comportamientos_por_impacto(id_impacto)

    def listar_codigos_pendientes(self, id_comportamiento: int) -> list[int]:
        """Lista los códigos con hechos pendientes para un comportamiento."""
        return self._repositorio.listar_codigos_pendientes(id_comportamiento)

    def listar_hechos_pendientes(
        self, id_comportamiento: int, id_codigo: int
    ) -> list[HechoComportamientoInfo]:
        """Lista los hechos pendientes de vincular a un caso de reincidencia."""
        return self._repositorio.listar_hechos_pendientes(id_comportamiento, id_codigo)

    def listar_pares_reincidencia(self) -> set[tuple[int, int]]:
        """Lista las combinaciones de hechos ya vinculadas a un caso."""
        return self._repositorio.listar_pares_reincidencia()

    def generar_reincidencias(self, usuario: str = "") -> int:
        """Analiza los hechos y genera los casos de reincidencia nuevos."""
        return self._repositorio.generar_reincidencias(usuario)

    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas ordenadas por nombre."""
        return self._repositorio.listar_empresas()

    def listar_reincidencias(self) -> list[ReincidenciaInfo]:
        """Lista los casos de reincidencia del más reciente al más antiguo."""
        return self._repositorio.listar_reincidencias()

    def listar_detalle_reincidencias(self) -> list[DetalleReincidenciaInfo]:
        """Lista el detalle de hechos de todos los casos de reincidencia."""
        return self._repositorio.listar_detalle_reincidencias()

    def obtener_reincidencia_accion(self, id_reincidencia: int) -> ReincidenciaAccionInfo | None:
        """Obtiene el código y el evento asociado de un caso de reincidencia."""
        return self._repositorio.obtener_reincidencia_accion(id_reincidencia)

    def actualizar_determinacion(
        self, id_reincidencia: int, determinacion: str, usuario: str
    ) -> None:
        """Actualiza la determinación de Metrocali de un caso de reincidencia."""
        return self._repositorio.actualizar_determinacion(id_reincidencia, determinacion, usuario)

    def registrar_accion_reincidencia(self, accion: AccionReincidencia, usuario: str) -> int:
        """Registra la acción de Metrocali derivada de un caso de reincidencia."""
        return self._repositorio.registrar_accion_reincidencia(accion, usuario)

    def importar_acciones_reincidencia(
        self, acciones: Sequence[AccionReincidencia], usuario: str
    ) -> tuple[int, int]:
        """Importa masivamente las acciones de reincidencia desde Excel."""
        return self._repositorio.importar_acciones_reincidencia(acciones, usuario)

    def registrar_reincidencia(
        self,
        id_impacto: int,
        id_comportamiento: int,
        id_codigo: int,
        fecha_inicio: date | None,
        fecha_fin: date | None,
        cantidad: int,
        resumen: str,
        usuario: str,
        hechos: Iterable[int],
    ) -> int:
        """Registra un caso de reincidencia con los hechos que lo componen."""
        return self._repositorio.registrar_reincidencia(
            id_impacto,
            id_comportamiento,
            id_codigo,
            fecha_inicio,
            fecha_fin,
            cantidad,
            resumen,
            usuario,
            hechos,
        )
