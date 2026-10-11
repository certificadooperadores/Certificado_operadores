"""Fachada de casos de uso de configuración (patrón Facade, spec 025).

Encapsula :class:`CatalogosRepository` —los catálogos maestros— y
:class:`EventosRepository` —la corrección segura de registros y lotes con
integridad referencial y auditoría— de modo que la UI de configuración nunca
importe un repositorio:

    UI → Facade → Dominio → Infraestructura

Reexporta además los DTOs, constantes, catálogos y excepciones que consume la
vista de corrección.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from certificado_operadores.infra.catalogos_repository import (
    LIMITE_DETALLES,
    CatalogosRepository,
    ComportamientoInfo,
    DatosDetalleComportamiento,
    DetalleComportamientoInfo,
    EmpresaInfo,
    ImpactoInfo,
    VehiculoInfo,
)
from certificado_operadores.infra.eventos_repository import (
    CLAVE_TABLA_EVENTOS,
    ETIQUETA_ESTADO,
    ETIQUETA_EVENTO,
    GENEROS_VALIDOS,
    LIMITE_POR_DEFECTO,
    OPCION_ANULADO,
    OPCION_VIGENTE,
    OPCIONES_ESTADO,
    OPCIONES_LICENCIA,
    TABLAS_CORRECCION,
    TIPO_EDICION_CODIGO,
    TIPO_EDICION_DESCRIPCION,
    TIPO_EDICION_ENTERO,
    TIPO_EDICION_EVENTO,
    TIPO_EDICION_FECHA,
    TIPO_EDICION_FUENTE,
    TIPO_EDICION_GENERO,
    TIPO_EDICION_LICENCIA,
    CambioRegistro,
    CampoIncompatibleError,
    CodigoInexistenteError,
    ColumnaEditable,
    ColumnaProtegidaError,
    DefinicionTabla,
    DependenciaRegistroError,
    EventoInfo,
    EventosRepository,
    FiltroEventos,
    LoteInfo,
    RegistroInfo,
    TipoEventoInfo,
    ValorInvalidoError,
    campos_permitidos_evento,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

__all__ = [
    "CLAVE_TABLA_EVENTOS",
    "ETIQUETA_ESTADO",
    "ETIQUETA_EVENTO",
    "GENEROS_VALIDOS",
    "OPCIONES_ESTADO",
    "OPCIONES_LICENCIA",
    "OPCION_ANULADO",
    "OPCION_VIGENTE",
    "TABLAS_CORRECCION",
    "TIPO_EDICION_CODIGO",
    "TIPO_EDICION_DESCRIPCION",
    "TIPO_EDICION_ENTERO",
    "TIPO_EDICION_EVENTO",
    "TIPO_EDICION_FECHA",
    "TIPO_EDICION_FUENTE",
    "TIPO_EDICION_GENERO",
    "TIPO_EDICION_LICENCIA",
    "CambioRegistro",
    "CampoIncompatibleError",
    "CodigoInexistenteError",
    "ColumnaEditable",
    "ColumnaProtegidaError",
    "ConfiguracionFacade",
    "DefinicionTabla",
    "DependenciaRegistroError",
    "RegistroInfo",
    "ValorInvalidoError",
    "campos_permitidos_evento",
]


class ConfiguracionFacade:
    """Fachada única de los catálogos maestros y la corrección de registros.

    Encapsula :class:`CatalogosRepository` y :class:`EventosRepository` para que
    la UI de catálogos y la de corrección de registros consuman una sola puerta.
    El motor se inyecta (por defecto se toma del configurado en ``db``) para
    facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa la fachada con los repositorios que orquesta.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._catalogos = CatalogosRepository(engine)
        self._eventos = EventosRepository(engine)

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        return self._catalogos.motor

    # --- Catálogos maestros (CatalogosRepository) ---------------------------
    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas de transporte."""

        return self._catalogos.listar_empresas()

    def crear_empresa(self, nombre: str, usuario: str) -> int:
        """Crea una empresa y registra la auditoría."""

        return self._catalogos.crear_empresa(nombre, usuario)

    def cambiar_vigencia_empresa(self, id_empresa: int, vigencia: int) -> None:
        """Cambia la vigencia (estado) de una empresa."""

        return self._catalogos.cambiar_vigencia_empresa(id_empresa, vigencia)

    def renombrar_empresa(self, id_empresa: int, nombre: str) -> None:
        """Renombra una empresa existente."""

        return self._catalogos.renombrar_empresa(id_empresa, nombre)

    def listar_vehiculos(self) -> list[VehiculoInfo]:
        """Lista los vehículos del catálogo."""

        return self._catalogos.listar_vehiculos()

    def crear_vehiculo(self, nombre: str, usuario: str) -> int:
        """Crea un vehículo y registra la auditoría."""

        return self._catalogos.crear_vehiculo(nombre, usuario)

    def renombrar_vehiculo(self, id_vehiculo: int, nombre: str) -> None:
        """Renombra un vehículo existente."""

        return self._catalogos.renombrar_vehiculo(id_vehiculo, nombre)

    def listar_impactos(self) -> list[ImpactoInfo]:
        """Lista los impactos del catálogo."""

        return self._catalogos.listar_impactos()

    def crear_impacto(self, nombre: str, maximo: int, dias_maximo: int, usuario: str) -> int:
        """Crea un impacto y registra la auditoría."""

        return self._catalogos.crear_impacto(nombre, maximo, dias_maximo, usuario)

    def actualizar_impacto(
        self, id_impacto: int, nombre: str, maximo: int, dias_maximo: int, usuario: str
    ) -> None:
        """Actualiza un impacto y registra la auditoría."""

        return self._catalogos.actualizar_impacto(id_impacto, nombre, maximo, dias_maximo, usuario)

    def listar_comportamientos(self) -> list[ComportamientoInfo]:
        """Lista los comportamientos cruzados con su impacto."""

        return self._catalogos.listar_comportamientos()

    def crear_comportamiento(self, descripcion: str, id_impacto: int, usuario: str) -> int:
        """Crea un comportamiento y registra la auditoría."""

        return self._catalogos.crear_comportamiento(descripcion, id_impacto, usuario)

    def actualizar_comportamiento(
        self, id_comportamiento: int, descripcion: str, id_impacto: int, usuario: str
    ) -> None:
        """Actualiza un comportamiento y registra la auditoría."""

        return self._catalogos.actualizar_comportamiento(
            id_comportamiento, descripcion, id_impacto, usuario
        )

    def listar_detalles(
        self, fuente: str | None = None, limite: int = LIMITE_DETALLES
    ) -> list[DetalleComportamientoInfo]:
        """Lista los detalles de comportamiento, filtrando por fuente."""

        return self._catalogos.listar_detalles(fuente=fuente, limite=limite)

    def crear_detalle(self, datos: DatosDetalleComportamiento, usuario: str) -> int:
        """Crea un detalle de comportamiento y registra la auditoría."""

        return self._catalogos.crear_detalle(datos, usuario)

    def actualizar_detalle(
        self, id_jerarquia: int, datos: DatosDetalleComportamiento, usuario: str
    ) -> None:
        """Actualiza un detalle de comportamiento y registra la auditoría."""

        return self._catalogos.actualizar_detalle(id_jerarquia, datos, usuario)

    # --- Corrección de registros (EventosRepository) ------------------------
    def listar_tipos_evento(self) -> list[TipoEventoInfo]:
        """Lista los tipos de evento disponibles para los editores."""

        return self._eventos.listar_tipos_evento()

    def listar_fuentes_comportamiento(self) -> list[str]:
        """Lista las fuentes oficiales de los comportamientos."""

        return self._eventos.listar_fuentes_comportamiento()

    def listar_descripciones_comportamiento(self) -> list[str]:
        """Lista las descripciones oficiales de los comportamientos."""

        return self._eventos.listar_descripciones_comportamiento()

    def buscar_eventos(self, filtro: FiltroEventos | None = None) -> list[EventoInfo]:
        """Busca eventos del historial con filtros opcionales."""

        return self._eventos.buscar_eventos(filtro)

    def listar_lotes(self) -> list[LoteInfo]:
        """Lista los lotes de carga masiva disponibles."""

        return self._eventos.listar_lotes()

    def listar_eventos_de_lote(self, lote: str) -> list[EventoInfo]:
        """Lista los eventos que pertenecen a un lote."""

        return self._eventos.listar_eventos_de_lote(lote)

    def reactivar_registros(self, ids: list[int], usuario: str) -> int:
        """Reactiva (marca vigente) un lote de registros por identificadores."""

        return self._eventos.reactivar_registros(ids, usuario)

    def anular_registros(self, ids: list[int], usuario: str) -> int:
        """Anula un lote de registros por identificadores."""

        return self._eventos.anular_registros(ids, usuario)

    def eliminar_registros(self, ids: list[int], usuario: str) -> int:
        """Elimina registros por identificadores con auditoría."""

        return self._eventos.eliminar_registros(ids, usuario)

    def reactivar_lote(self, lote: str, usuario: str) -> int:
        """Reactiva todos los registros de un lote."""

        return self._eventos.reactivar_lote(lote, usuario)

    def anular_lote(self, lote: str, usuario: str) -> int:
        """Anula todos los registros de un lote."""

        return self._eventos.anular_lote(lote, usuario)

    def eliminar_lote(self, lote: str, usuario: str) -> int:
        """Elimina todos los registros de un lote con auditoría."""

        return self._eventos.eliminar_lote(lote, usuario)

    def registrar_auditoria(self, usuario: str, accion: str, detalles: str) -> None:
        """Registra un evento de auditoría en ``log_auditoria``."""

        return self._eventos.registrar_auditoria(usuario, accion, detalles)

    def listar_registros(
        self,
        clave: str,
        limite: int = LIMITE_POR_DEFECTO,
        id_tipo_evento: int | None = None,
    ) -> list[RegistroInfo]:
        """Lista los registros de una tabla del catálogo de corrección."""

        return self._eventos.listar_registros(clave, limite=limite, id_tipo_evento=id_tipo_evento)

    def mutar_vigencia(self, clave: str, ids: list[int], vigencia: int, usuario: str) -> int:
        """Cambia la vigencia de un conjunto de registros de una tabla."""

        return self._eventos.mutar_vigencia(clave, ids, vigencia, usuario)

    def eliminar_registros_tabla(self, clave: str, ids: list[int], usuario: str) -> int:
        """Elimina registros de una tabla del catálogo de corrección."""

        return self._eventos.eliminar_registros_tabla(clave, ids, usuario)

    def contar_dependencias_operador(
        self, id_persona: int, id_codigo: int | None = None
    ) -> dict[str, int]:
        """Cuenta las dependencias de un operador antes de borrarlo."""

        return self._eventos.contar_dependencias_operador(id_persona, id_codigo)

    def validar_codigo_existe(self, id_codigo: int) -> bool:
        """Indica si un código de operación existe en ``dim_codigo``."""

        return self._eventos.validar_codigo_existe(id_codigo)

    def actualizar_registros_seguros(
        self, clave: str, cambios: list[CambioRegistro], usuario: str
    ) -> int:
        """Aplica cambios validados de forma atómica sobre una tabla."""

        return self._eventos.actualizar_registros_seguros(clave, cambios, usuario)
