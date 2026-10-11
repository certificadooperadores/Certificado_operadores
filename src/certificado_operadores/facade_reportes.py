"""Fachada de casos de uso de reportes y exportaciones (patrón Facade, spec 025).

Expone las métricas analíticas, los filtros tridireccionales y los reportes de
vencimiento de licencias y certificados, delegando toda la consulta en
:class:`ReportesRepository` y la generación de archivos en las funciones puras
``generar_excel``/``generar_csv``. La UI de reportes consume **exclusivamente**
esta fachada:

    UI → Facade → Dominio → Infraestructura

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from certificado_operadores.infra.reportes_repository import (
    DIAS_VENCIMIENTO_DEFECTO,
    DIAS_VENCIMIENTO_MAXIMO,
    DIAS_VENCIMIENTO_MINIMO,
    OPCIONES_ESTADO,
    OPCIONES_ESTADO_ACTIVO,
    TIPO_MIME_CSV,
    TIPO_MIME_EXCEL,
    DefinicionReporte,
    EmpresaInfo,
    ImpactoInfo,
    ReportesRepository,
    SeleccionFiltros,
    TipoEventoInfo,
    TipologiaInfo,
    generar_csv,
    generar_excel,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

__all__ = [
    "DIAS_VENCIMIENTO_DEFECTO",
    "DIAS_VENCIMIENTO_MAXIMO",
    "DIAS_VENCIMIENTO_MINIMO",
    "OPCIONES_ESTADO",
    "OPCIONES_ESTADO_ACTIVO",
    "TIPO_MIME_CSV",
    "TIPO_MIME_EXCEL",
    "DefinicionReporte",
    "ReportesFacade",
    "SeleccionFiltros",
    "generar_csv",
    "generar_excel",
]


class ReportesFacade:
    """Fachada única de los casos de uso de reportes y exportaciones.

    Encapsula :class:`ReportesRepository` para que la vista nunca conozca el
    motor ni el esquema. El motor se inyecta (por defecto se toma del
    configurado en ``db``) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa la fachada sobre el repositorio de reportes.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._repositorio = ReportesRepository(engine)

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        return self._repositorio.motor

    def listar_reportes(self) -> tuple[DefinicionReporte, ...]:
        """Lista las definiciones de los reportes disponibles."""
        return self._repositorio.listar_reportes()

    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas para el filtro tridireccional."""
        return self._repositorio.listar_empresas()

    def listar_tipologias(self) -> list[TipologiaInfo]:
        """Lista las tipologías para el filtro tridireccional."""
        return self._repositorio.listar_tipologias()

    def listar_estados(self) -> list[str]:
        """Lista los estados de vigencia para el filtro."""
        return self._repositorio.listar_estados()

    def listar_tipos_evento(self) -> list[TipoEventoInfo]:
        """Lista los tipos de evento para el filtro."""
        return self._repositorio.listar_tipos_evento()

    def listar_impactos(self) -> list[ImpactoInfo]:
        """Lista los impactos para el filtro."""
        return self._repositorio.listar_impactos()

    def construir_condiciones(
        self, id_reporte: str, seleccion: SeleccionFiltros
    ) -> tuple[list[str], dict[str, object]]:
        """Construye las condiciones SQL y sus parámetros para un reporte."""
        return self._repositorio.construir_condiciones(id_reporte, seleccion)

    def ejecutar_reporte(self, id_reporte: str, seleccion: SeleccionFiltros) -> pd.DataFrame:
        """Ejecuta un reporte consolidado con los filtros seleccionados."""
        return self._repositorio.ejecutar_reporte(id_reporte, seleccion)

    def registrar_exportacion(self, usuario: str, nombre_reporte: str, total: int) -> None:
        """Registra en auditoría la exportación de un reporte."""
        return self._repositorio.registrar_exportacion(usuario, nombre_reporte, total)
