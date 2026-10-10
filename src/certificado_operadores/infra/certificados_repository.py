"""Repositorio de gestión de certificados (capa de infraestructura, spec 008).

Encapsula **todo** el acceso a datos del registro manual y masivo de eventos e
historial de certificaciones de operadores: carga de catálogos auxiliares
(tipos de evento, vehículos y evaluadores), búsqueda del operador activo por
cédula o código de operación y la inserción de eventos en
``fact_eventos_operador`` con su registro de auditoría en la misma transacción.

La interfaz de usuario no conoce el esquema ni el motor: solo consume los DTOs
que devuelve este repositorio. Todas las consultas usan parámetros enlazados
(nunca SQL construido con datos del usuario).

Reutiliza los DTOs :class:`TipoEventoInfo` (eventos) y :class:`VehiculoInfo`
(catálogos) para no duplicar el contrato entre repositorios de infraestructura.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import text

from certificado_operadores.domain.models import VIGENCIA_ACTIVA
from certificado_operadores.infra.catalogos_repository import VehiculoInfo
from certificado_operadores.infra.eventos_repository import TipoEventoInfo

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine, RowMapping

# --- Tipos de evento (identificadores de ``dim_tipo_evento``) ----------------
TIPO_EVENTO_CERTIFICACION = 1
"""Evento de certificación inicial."""

TIPO_EVENTO_REACTIVACION = 2
"""Evento de reactivación del certificado."""

TIPO_EVENTO_RENOVACION = 3
"""Evento de renovación del certificado."""

TIPO_EVENTO_OBSERVACION = 4
"""Evento de observación."""

TIPO_EVENTO_RESTRICCION_MEDICA = 5
"""Evento de restricción médica."""

TIPO_EVENTO_SUSPENSION = 6
"""Evento de suspensión."""

TIPO_EVENTO_CANCELACION = 7
"""Evento de cancelación o notificación de retiro."""

TIPO_EVENTO_ADVERTENCIA = 8
"""Evento de advertencia."""

TIPO_EVENTO_CONDICIONAMIENTO = 9
"""Evento de condicionamiento."""

# --- Acciones de auditoría ---------------------------------------------------
ACCION_REGISTRO_EVENTO = "Registro Evento Manual"
"""Acción de auditoría al registrar un evento individual."""

ACCION_CARGA_MASIVA = "Carga Masiva de Eventos"
"""Acción de auditoría al cargar eventos de forma masiva."""


@dataclass(frozen=True)
class OperadorActivoInfo:
    """Operador con al menos un código de operación activo.

    Attributes:
        id_codigo: Código de operación activo del operador.
        cedula: Documento del operador (``dim_persona.id_persona``).
        nombres: Nombres del operador.
        primer_apellido: Primer apellido del operador.
        segundo_apellido: Segundo apellido del operador (puede ser vacío).
    """

    id_codigo: int
    cedula: int
    nombres: str
    primer_apellido: str
    segundo_apellido: str = ""

    def nombre_completo(self) -> str:
        """Devuelve el nombre completo del operador en una sola cadena."""
        partes = (self.nombres, self.primer_apellido, self.segundo_apellido)
        return " ".join(parte for parte in partes if parte).strip()


@dataclass(frozen=True)
class DatosEvento:
    """Datos de entrada para registrar un evento de certificación.

    Todos los campos salvo ``id_codigo`` e ``id_tipo_evento`` son opcionales:
    cada tipo de evento usa un subconjunto distinto (validado en la UI antes de
    invocar el repositorio).

    Attributes:
        id_codigo: Código de operación al que se asocia el evento.
        id_tipo_evento: Tipo de evento a registrar.
        id_vehiculo_evaluado: Vehículo evaluado (evento de certificación).
        evaluador: Nombre del evaluador.
        fecha_prueba: Fecha de la prueba.
        fecha_certificado: Fecha del certificado.
        fecha_retiro: Fecha de retiro o cancelación.
        fecha_notificacion_retiro: Fecha de notificación de retiro.
        fecha_suspension: Fecha de suspensión.
        restriccion_medica: Descripción de la restricción médica.
        elemento_de_proteccion: Elemento de protección asociado.
        inicio_restriccion_medica: Inicio de la restricción médica.
        fin_restriccion_medica: Fin de la restricción médica.
        fecha_observacion: Fecha de la novedad u observación.
        observacion: Descripción libre de la observación.
    """

    id_codigo: int
    id_tipo_evento: int
    id_vehiculo_evaluado: int | None = None
    evaluador: str | None = None
    fecha_prueba: date | None = None
    fecha_certificado: date | None = None
    fecha_retiro: date | None = None
    fecha_notificacion_retiro: date | None = None
    fecha_suspension: date | None = None
    restriccion_medica: str | None = None
    elemento_de_proteccion: str | None = None
    inicio_restriccion_medica: date | None = None
    fin_restriccion_medica: date | None = None
    fecha_observacion: date | None = None
    observacion: str | None = None


# --- Sentencias SQL (parámetros enlazados, sin concatenar datos) -------------
_SQL_TIPOS_EVENTO = text(
    "SELECT id_tipo_evento, nombre_evento FROM dim_tipo_evento ORDER BY id_tipo_evento"
)

_SQL_VEHICULOS = text("SELECT id_vehiculo, nombre_vehiculo FROM dim_vehiculo ORDER BY id_vehiculo")

_SQL_EVALUADORES = text(
    "SELECT DISTINCT evaluador FROM fact_eventos_operador "
    "WHERE evaluador IS NOT NULL AND evaluador <> '' ORDER BY evaluador"
)

_COLUMNAS_OPERADOR = """
    c.id_codigo, c.id_persona AS cedula,
    p.nombres, p.primer_apellido, p.segundo_apellido
"""

_FROM_OPERADOR = """
    FROM dim_codigo AS c
    JOIN dim_persona AS p ON c.id_persona = p.id_persona
"""

# El código no debe estar cancelado (tipo de evento 7) ni inactivo.
_CONDICION_OPERADOR_ACTIVO = """
    c.id_vigencia = :vigencia
    AND c.id_codigo NOT IN (
        SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = :cancelacion
    )
"""

_SQL_OPERADOR_POR_CODIGO = text(
    f"SELECT {_COLUMNAS_OPERADOR} {_FROM_OPERADOR} "
    f"WHERE c.id_codigo = :codigo AND {_CONDICION_OPERADOR_ACTIVO} LIMIT 1"
)

_SQL_OPERADOR_POR_CEDULA = text(
    f"SELECT {_COLUMNAS_OPERADOR} {_FROM_OPERADOR} "
    f"WHERE c.id_persona = :cedula AND {_CONDICION_OPERADOR_ACTIVO} "
    f"ORDER BY c.fecha_registro DESC LIMIT 1"
)

_SQL_SIGUIENTE_ID = text("SELECT COALESCE(MAX(id_hecho_evento), 0) + 1 FROM fact_eventos_operador")

_SQL_INSERT_EVENTO = text(
    """
    INSERT INTO fact_eventos_operador
        (id_hecho_evento, id_codigo, id_tipo_evento, id_vehiculo_evaluado, evaluador,
         fecha_prueba, fecha_certificado, fecha_retiro, fecha_notificacion_retiro,
         fecha_suspension, restriccion_medica, elemento_de_proteccion,
         inicio_restriccion_medica, fin_restriccion_medica, fecha_observacion,
         observacion, id_vigencia, usuario_registra, fecha_registro)
    VALUES
        (:id, :cod, :tip, :veh, :eva, :fp, :fc, :fr, :fn, :fs, :rm, :ep,
         :ir, :fir, :fo, :obs, :vigencia, :usuario, CURRENT_TIMESTAMP)
    """
)

_SQL_AUDITORIA = text(
    "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:usuario, :accion, :detalles)"
)


def _formatear_fecha(valor: date | None) -> str | None:
    """Convierte una fecha a texto ISO para los parámetros enlazados.

    Args:
        valor: Fecha a formatear, o ``None``.

    Returns:
        La fecha en formato ``YYYY-MM-DD``, o ``None`` si no hay valor.
    """
    return valor.isoformat() if valor is not None else None


def _mapear_operador(fila: RowMapping) -> OperadorActivoInfo:
    """Mapea una fila de operador activo al DTO de infraestructura.

    Args:
        fila: Fila devuelta por SQLAlchemy.

    Returns:
        El :class:`OperadorActivoInfo` construido a partir de la fila.
    """
    return OperadorActivoInfo(
        id_codigo=int(fila["id_codigo"]),
        cedula=int(fila["cedula"]),
        nombres=str(fila["nombres"] or "").strip(),
        primer_apellido=str(fila["primer_apellido"] or "").strip(),
        segundo_apellido=str(fila["segundo_apellido"] or "").strip(),
    )


class CertificadosRepository:
    """Repositorio de eventos de certificación sobre la base de datos.

    Concentra toda la ejecución de SQLAlchemy del registro de certificados. El
    motor se inyecta (por defecto se resuelve de forma perezosa desde
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

    def listar_tipos_evento(self) -> list[TipoEventoInfo]:
        """Lista los tipos de evento disponibles, ordenados por identificador.

        Returns:
            Los tipos de evento del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_TIPOS_EVENTO).mappings().all()
        return [
            TipoEventoInfo(
                id_tipo_evento=int(fila["id_tipo_evento"]),
                nombre_evento=str(fila["nombre_evento"]),
            )
            for fila in filas
        ]

    def listar_vehiculos(self) -> list[VehiculoInfo]:
        """Lista los vehículos evaluables, ordenados por identificador.

        Returns:
            Los vehículos del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_VEHICULOS).mappings().all()
        return [
            VehiculoInfo(
                id_vehiculo=int(fila["id_vehiculo"]),
                nombre_vehiculo=str(fila["nombre_vehiculo"] or ""),
            )
            for fila in filas
        ]

    def listar_evaluadores(self) -> list[str]:
        """Lista los evaluadores históricos distintos, ordenados alfabéticamente.

        Returns:
            Los nombres de evaluador registrados en eventos previos.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_EVALUADORES).mappings().all()
        return [str(fila["evaluador"]) for fila in filas]

    def buscar_operador_activo_por_codigo(self, codigo: int) -> OperadorActivoInfo | None:
        """Busca un operador por su código de operación activo.

        Args:
            codigo: Código de operación (``dim_codigo.id_codigo``).

        Returns:
            El :class:`OperadorActivoInfo` si el código existe, está vigente y no
            está cancelado; ``None`` en caso contrario.
        """
        parametros = {
            "codigo": codigo,
            "vigencia": VIGENCIA_ACTIVA,
            "cancelacion": TIPO_EVENTO_CANCELACION,
        }
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_OPERADOR_POR_CODIGO, parametros).mappings().first()
        return _mapear_operador(fila) if fila is not None else None

    def buscar_operador_activo_por_cedula(self, cedula: int) -> OperadorActivoInfo | None:
        """Busca un operador por su cédula y devuelve su código activo más reciente.

        Args:
            cedula: Documento del operador (``dim_persona.id_persona``).

        Returns:
            El :class:`OperadorActivoInfo` si el operador tiene un código vigente
            y no cancelado; ``None`` en caso contrario.
        """
        parametros = {
            "cedula": cedula,
            "vigencia": VIGENCIA_ACTIVA,
            "cancelacion": TIPO_EVENTO_CANCELACION,
        }
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_OPERADOR_POR_CEDULA, parametros).mappings().first()
        return _mapear_operador(fila) if fila is not None else None

    def registrar_evento(self, datos: DatosEvento, usuario: str) -> int:
        """Registra un evento individual y su auditoría en una transacción.

        Args:
            datos: Datos del evento a registrar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            El identificador del evento creado.
        """
        nuevo_id = self._siguiente_id()
        detalles = f"Codigo: {datos.id_codigo}, Evento ID: {datos.id_tipo_evento}"
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_INSERT_EVENTO, self._parametros_evento(datos, nuevo_id, usuario))
            self._auditar(conexion, usuario, ACCION_REGISTRO_EVENTO, detalles)
        return nuevo_id

    def registrar_eventos(
        self,
        eventos: list[DatosEvento],
        usuario: str,
        accion: str = ACCION_CARGA_MASIVA,
        detalles: str = "",
    ) -> int:
        """Registra varios eventos y una única auditoría en una transacción.

        Args:
            eventos: Datos de los eventos a registrar.
            usuario: Usuario que ejecuta la acción.
            accion: Acción de auditoría a registrar.
            detalles: Detalle libre de la auditoría.

        Returns:
            Número de eventos registrados; ``0`` si la lista está vacía.
        """
        if not eventos:
            return 0
        siguiente = self._siguiente_id()
        with self.motor.begin() as conexion:
            for desplazamiento, datos in enumerate(eventos):
                parametros = self._parametros_evento(datos, siguiente + desplazamiento, usuario)
                conexion.execute(_SQL_INSERT_EVENTO, parametros)
            self._auditar(conexion, usuario, accion, detalles)
        return len(eventos)

    def _siguiente_id(self) -> int:
        """Calcula el siguiente identificador disponible de ``fact_eventos_operador``.

        Returns:
            ``MAX(id_hecho_evento) + 1`` o ``1`` si la tabla está vacía.
        """
        with self.motor.connect() as conexion:
            return int(conexion.execute(_SQL_SIGUIENTE_ID).scalar_one())

    @staticmethod
    def _parametros_evento(
        datos: DatosEvento, id_hecho_evento: int, usuario: str
    ) -> dict[str, object]:
        """Traduce los datos del evento a los parámetros enlazados de la inserción.

        Args:
            datos: Datos del evento.
            id_hecho_evento: Identificador a asignar al evento.
            usuario: Usuario que registra el evento.

        Returns:
            El diccionario de parámetros para la sentencia de inserción.
        """
        return {
            "id": id_hecho_evento,
            "cod": datos.id_codigo,
            "tip": datos.id_tipo_evento,
            "veh": datos.id_vehiculo_evaluado,
            "eva": datos.evaluador,
            "fp": _formatear_fecha(datos.fecha_prueba),
            "fc": _formatear_fecha(datos.fecha_certificado),
            "fr": _formatear_fecha(datos.fecha_retiro),
            "fn": _formatear_fecha(datos.fecha_notificacion_retiro),
            "fs": _formatear_fecha(datos.fecha_suspension),
            "rm": datos.restriccion_medica,
            "ep": datos.elemento_de_proteccion,
            "ir": _formatear_fecha(datos.inicio_restriccion_medica),
            "fir": _formatear_fecha(datos.fin_restriccion_medica),
            "fo": _formatear_fecha(datos.fecha_observacion),
            "obs": datos.observacion,
            "vigencia": VIGENCIA_ACTIVA,
            "usuario": usuario,
        }

    @staticmethod
    def _auditar(conexion: Connection, usuario: str, accion: str, detalles: str) -> None:
        """Inserta una fila de auditoría usando la conexión de la transacción.

        Args:
            conexion: Conexión activa dentro de la transacción.
            usuario: Usuario que ejecuta la acción.
            accion: Nombre de la acción realizada.
            detalles: Detalle libre de la acción.
        """
        conexion.execute(
            _SQL_AUDITORIA,
            {"usuario": usuario, "accion": accion, "detalles": detalles},
        )


__all__ = [
    "ACCION_CARGA_MASIVA",
    "ACCION_REGISTRO_EVENTO",
    "TIPO_EVENTO_ADVERTENCIA",
    "TIPO_EVENTO_CANCELACION",
    "TIPO_EVENTO_CERTIFICACION",
    "TIPO_EVENTO_CONDICIONAMIENTO",
    "TIPO_EVENTO_OBSERVACION",
    "TIPO_EVENTO_REACTIVACION",
    "TIPO_EVENTO_RENOVACION",
    "TIPO_EVENTO_RESTRICCION_MEDICA",
    "TIPO_EVENTO_SUSPENSION",
    "CertificadosRepository",
    "DatosEvento",
    "OperadorActivoInfo",
]
