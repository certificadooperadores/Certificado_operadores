"""Repositorio de comportamientos y reincidencia (capa de infraestructura, spec 009).

Encapsula **todo** el acceso a datos del reporte de comportamientos: búsqueda del
operador por cédula o código, catálogo de detalles de comportamiento, registro
individual y masivo en ``fact_comportamiento`` con su auditoría y el cálculo y
consulta de la reincidencia (``fact_reincidencia``/``reincidencia_detalle`` y su
impacto en ``fact_eventos_operador``).

La interfaz de usuario no conoce el esquema ni el motor: solo consume los DTOs
que devuelve este repositorio. Todas las consultas usan parámetros enlazados
(nunca SQL construido con datos del usuario). La ventana temporal de reincidencia
se conserva en :data:`MESES_VENTANA_REINCIDENCIA` (mismos umbrales heredados).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

from certificado_operadores.domain.models import VIGENCIA_ACTIVA

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from sqlalchemy.engine import Connection, Engine, RowMapping

# --- Umbrales y constantes de negocio (heredadas, sin cambios) ----------------
MESES_VENTANA_REINCIDENCIA = 7
"""Meses hacia atrás que cubre el análisis de reincidencia."""

VENTANA_REINCIDENCIA_SQL = f"-{MESES_VENTANA_REINCIDENCIA} months"
"""Modificador de fecha de SQLite con la ventana de reincidencia."""

NOMBRE_IMPACTO_GRAVE = "grave"
"""Nombre del impacto que genera un caso por cada hecho (sin emparejar)."""

TIPO_EVENTO_CANCELACION = 7
"""Tipo de evento que cancela el certificado del operador."""

# --- Acciones de auditoría ---------------------------------------------------
ACCION_REGISTRO_COMPORTAMIENTO = "Registro Comportamiento Manual"
"""Acción de auditoría al registrar un comportamiento individual."""

ACCION_CARGA_MASIVA_COMPORTAMIENTOS = "Carga Masiva Comportamientos"
"""Acción de auditoría al cargar comportamientos de forma masiva."""

ACCION_DETERMINAR_REINCIDENCIA = "Determinar Reincidencia"
"""Acción de auditoría al fijar la determinación de un caso de reincidencia."""

ACCION_REGISTRAR_ACCION_REINCIDENCIA = "Registrar Accion Reincidencia"
"""Acción de auditoría al registrar una acción de reincidencia en el historial."""

ACCION_ACTUALIZAR_ACCION_REINCIDENCIA = "Actualizar Accion Reincidencia"
"""Acción de auditoría al actualizar una acción de reincidencia ya registrada."""

ACCION_IMPORTAR_ACCIONES_REINCIDENCIA = "Importar Acciones Reincidencia"
"""Acción de auditoría al importar acciones de reincidencia desde Excel."""


# --- DTOs de infraestructura -------------------------------------------------
@dataclass(frozen=True)
class OperadorComportamientoInfo:
    """Operador con un código activo para el reporte de comportamientos.

    Attributes:
        id_codigo: Código de operación activo (``dim_codigo.id_codigo``).
        cedula: Documento del operador (``dim_persona.id_persona``).
        nombres: Nombres del operador.
        primer_apellido: Primer apellido del operador.
    """

    id_codigo: int
    cedula: int
    nombres: str
    primer_apellido: str

    def nombre_completo(self) -> str:
        """Devuelve el nombre y primer apellido del operador en una sola cadena."""
        return f"{self.nombres} {self.primer_apellido}".strip()


@dataclass(frozen=True)
class DetalleComportamientoInfo:
    """Jerarquía de comportamiento seleccionable para un evento.

    Attributes:
        id_jerarquia: Identificador de la jerarquía (``dim_detalle_comportamiento``).
        descripcion: Descripción legible del comportamiento.
    """

    id_jerarquia: int
    descripcion: str


@dataclass(frozen=True)
class DatosComportamiento:
    """Datos de entrada para registrar un comportamiento.

    Sirve tanto al registro individual como a la carga masiva. Cuando
    ``id_existente`` trae un valor, el repositorio actualiza ese registro en lugar
    de insertar uno nuevo (mismo ``caso_bitacora_ticket``).

    Attributes:
        id_jerarquia: Jerarquía de comportamiento aplicada.
        id_codigo: Código de operación del operador.
        fecha_evento: Fecha del evento.
        hora_evento: Hora del evento en texto (formato de la fuente).
        caso_bitacora_ticket: Caso, bitácora o ticket asociado.
        nota: Nota o descripción libre.
        vehiculo: Número del vehículo (MC).
        viaje: Número de viaje.
        tarea: Número de tarea.
        ruta: Ruta.
        sitio_salida: Sitio de salida.
        sitio_novedad: Sitio de novedad.
        numero_lesionados: Número de lesionados.
        observacion_concesionario: Observación del concesionario.
        respuesta_mc: Respuesta de Metrocali.
        responsable_pqrs_cot: Responsable de PQRS/COT.
        direccion_infraccion: Dirección de la infracción.
        clase_servicio: Clase de servicio.
        tipo_servicio: Tipo de servicio.
        fuente_infraccion: Fuente de la infracción.
        placa: Placa del vehículo.
        id_existente: Identificador de un registro previo a actualizar, si aplica.
    """

    id_jerarquia: int
    id_codigo: int
    fecha_evento: date | None = None
    hora_evento: str | None = None
    caso_bitacora_ticket: str | None = None
    nota: str | None = None
    vehiculo: int | None = None
    viaje: int | None = None
    tarea: int | None = None
    ruta: str | None = None
    sitio_salida: str | None = None
    sitio_novedad: str | None = None
    numero_lesionados: int | None = None
    observacion_concesionario: str | None = None
    respuesta_mc: str | None = None
    responsable_pqrs_cot: str | None = None
    direccion_infraccion: str | None = None
    clase_servicio: str | None = None
    tipo_servicio: str | None = None
    fuente_infraccion: str | None = None
    placa: str | None = None
    id_existente: int | None = None


@dataclass(frozen=True)
class ImpactoInfo:
    """Nivel de impacto de reincidencia con umbrales configurados.

    Attributes:
        id_impacto: Identificador del impacto.
        impacto: Nombre del impacto (por ejemplo ``Grave``).
        maximo: Máximo de casos permitidos; solo interesan los ``> 0``.
        dias_maximo: Ventana en días para emparejar hechos del mismo impacto.
    """

    id_impacto: int
    impacto: str
    maximo: int
    dias_maximo: int


@dataclass(frozen=True)
class ComportamientoReincidenciaInfo:
    """Comportamiento asociado a un impacto.

    Attributes:
        id_comportamiento: Identificador del comportamiento.
        comportamiento: Descripción legible del comportamiento.
    """

    id_comportamiento: int
    comportamiento: str


@dataclass(frozen=True)
class HechoComportamientoInfo:
    """Hecho de comportamiento candidato a reincidencia.

    Attributes:
        id_hecho_comportamiento: Identificador del hecho.
        fecha_evento: Fecha del evento.
        caso_bitacora_ticket: Caso asociado.
        hora_evento: Hora del evento.
        vehiculo: Vehículo implicado.
        fuente_infraccion: Fuente de la infracción.
        responsable_pqrs_cot: Responsable de PQRS/COT.
        id_jerarquia: Jerarquía del comportamiento.
    """

    id_hecho_comportamiento: int
    fecha_evento: object
    caso_bitacora_ticket: object
    hora_evento: object
    vehiculo: object
    fuente_infraccion: object
    responsable_pqrs_cot: object
    id_jerarquia: int


@dataclass(frozen=True)
class EmpresaInfo:
    """Empresa transportadora para los filtros del reporte.

    Attributes:
        id_empresa: Identificador de la empresa.
        nombre_empresa: Nombre de la empresa.
    """

    id_empresa: int
    nombre_empresa: str


@dataclass(frozen=True)
class ReincidenciaInfo:
    """Caso de reincidencia para el listado del reporte.

    Attributes:
        id_reincidencia: Identificador del caso.
        id_codigo: Código del operador.
        nombre_empresa: Empresa del operador.
        impacto: Impacto asociado.
        comportamiento: Comportamiento asociado.
        fecha_inicio: Fecha inicial del caso.
        fecha_fin: Fecha final del caso.
        cantidad: Número de hechos del caso.
        determinacion_mc: Determinación registrada por Metrocali.
        estado: Estado del caso.
        id_hecho_evento: Evento del historial del operador asociado, si existe.
        usuario_registra: Usuario que generó el caso.
    """

    id_reincidencia: int
    id_codigo: object
    nombre_empresa: object
    impacto: object
    comportamiento: object
    fecha_inicio: object
    fecha_fin: object
    cantidad: object
    determinacion_mc: object
    estado: object
    id_hecho_evento: object
    usuario_registra: object


@dataclass(frozen=True)
class DetalleReincidenciaInfo:
    """Detalle de un hecho asociado a un caso de reincidencia.

    Attributes:
        id_reincidencia: Identificador del caso.
        id_codigo: Código del operador.
        nombre_empresa: Empresa del operador.
        impacto: Impacto asociado.
        comportamiento: Comportamiento asociado.
        fecha_inicio: Fecha inicial del caso.
        fecha_fin: Fecha final del caso.
        determinacion_mc: Determinación de Metrocali.
        descripcion_comportamiento: Descripción del detalle de comportamiento.
        caso_bitacora_ticket: Caso del hecho.
        fecha_evento: Fecha del hecho.
        vehiculo: Vehículo del hecho.
        viaje: Viaje del hecho.
        tarea: Tarea del hecho.
        hora_evento: Hora del hecho.
        ruta: Ruta del hecho.
        clase_servicio: Clase de servicio del hecho.
        tipo_servicio: Tipo de servicio del hecho.
        fuente_infraccion: Fuente de la infracción del hecho.
        placa: Placa del hecho.
    """

    id_reincidencia: int
    id_codigo: object
    nombre_empresa: object
    impacto: object
    comportamiento: object
    fecha_inicio: object
    fecha_fin: object
    determinacion_mc: object
    descripcion_comportamiento: object
    caso_bitacora_ticket: object
    fecha_evento: object
    vehiculo: object
    viaje: object
    tarea: object
    hora_evento: object
    ruta: object
    clase_servicio: object
    tipo_servicio: object
    fuente_infraccion: object
    placa: object


@dataclass(frozen=True)
class ReincidenciaAccionInfo:
    """Datos mínimos de un caso para validar una acción importada.

    Attributes:
        id_codigo: Código del operador del caso.
        id_hecho_evento: Evento del historial asociado, si existe.
    """

    id_codigo: int
    id_hecho_evento: int | None


@dataclass(frozen=True)
class AccionReincidencia:
    """Acción de reincidencia a registrar en el historial del operador.

    Attributes:
        id_reincidencia: Caso de reincidencia al que corresponde la acción.
        id_codigo: Código del operador.
        id_tipo_evento: Tipo de evento del historial a registrar.
        fecha_observacion: Fecha de la acción.
        observacion: Descripción de la acción.
        id_hecho_evento: Evento existente a actualizar; ``None`` para insertar.
    """

    id_reincidencia: int
    id_codigo: int
    id_tipo_evento: int
    fecha_observacion: date
    observacion: str
    id_hecho_evento: int | None = None


# --- Sentencias SQL (parámetros enlazados, sin concatenar datos) -------------
_SQL_OPERADOR_POR_CODIGO = text(
    """
    SELECT c.id_codigo, c.id_persona AS cedula, p.nombres, p.primer_apellido
    FROM dim_codigo AS c
    LEFT JOIN dim_persona AS p ON c.id_persona = p.id_persona
    WHERE c.id_codigo = :n AND c.id_vigencia = :vigencia
    LIMIT 1
    """
)

_SQL_OPERADOR_POR_CEDULA = text(
    """
    SELECT c.id_codigo, c.id_persona AS cedula, p.nombres, p.primer_apellido
    FROM dim_codigo AS c
    LEFT JOIN dim_persona AS p ON c.id_persona = p.id_persona
    WHERE c.id_persona = :n AND c.id_vigencia = :vigencia
    ORDER BY c.fecha_registro DESC
    LIMIT 1
    """
)

_SQL_DETALLES_COMPORTAMIENTO = text(
    "SELECT id_jerarquia, descripcion_comportamiento "
    "FROM dim_detalle_comportamiento ORDER BY descripcion_comportamiento"
)

_SQL_CODIGO_ACTIVO = text(
    "SELECT id_codigo FROM dim_codigo WHERE id_codigo = :c AND id_vigencia = :vigencia LIMIT 1"
)

_SQL_JERARQUIA_POR_DESCRIPCION = text(
    "SELECT id_jerarquia FROM dim_detalle_comportamiento "
    "WHERE descripcion_comportamiento = :d LIMIT 1"
)

_SQL_COMPORTAMIENTO_POR_CASO = text(
    "SELECT id_hecho_comportamiento FROM fact_comportamiento "
    "WHERE caso_bitacora_ticket = :c LIMIT 1"
)

_SQL_SIGUIENTE_ID_COMPORTAMIENTO = text(
    "SELECT COALESCE(MAX(id_hecho_comportamiento), 0) + 1 FROM fact_comportamiento"
)

_SQL_INSERT_COMPORTAMIENTO = text(
    """
    INSERT INTO fact_comportamiento
        (id_hecho_comportamiento, id_jerarquia, id_codigo, fecha_evento, hora_evento,
         nota, vehiculo, viaje, tarea, caso_bitacora_ticket, ruta,
         sitio_salida, sitio_novedad, numero_lesionados, observacion_concesionario,
         respuesta_mc, responsable_pqrs_cot, direccion_infraccion, clase_servicio,
         tipo_servicio, fuente_infraccion, placa,
         id_vigencia, usuario_registra, fecha_registro)
    VALUES (:id, :j, :cod, :f, :h, :n, :v, :vi, :ta, :caso, :r,
            :ss, :sn, :nl, :oc, :rmc, :rpqrs, :dir, :cs, :ts, :fi, :pl,
            :vigencia, :usuario, CURRENT_TIMESTAMP)
    """
)

_SQL_UPDATE_COMPORTAMIENTO = text(
    """
    UPDATE fact_comportamiento SET
        id_jerarquia = :j, id_codigo = :cod, fecha_evento = :f, hora_evento = :h,
        nota = :n, vehiculo = :v, viaje = :vi, tarea = :ta,
        caso_bitacora_ticket = :caso, ruta = :r, sitio_salida = :ss,
        sitio_novedad = :sn, numero_lesionados = :nl,
        observacion_concesionario = :oc, respuesta_mc = :rmc,
        responsable_pqrs_cot = :rpqrs, direccion_infraccion = :dir,
        clase_servicio = :cs, tipo_servicio = :ts, fuente_infraccion = :fi,
        placa = :pl, usuario_registra = :usuario
    WHERE id_hecho_comportamiento = :id
    """
)

_SQL_IMPACTOS = text(
    "SELECT id_impacto, impacto, maximo, dias_maximo FROM dim_impacto "
    "WHERE maximo > 0 ORDER BY id_impacto"
)

_SQL_COMPORTAMIENTOS_POR_IMPACTO = text(
    "SELECT id_comportamiento, comportamiento FROM dim_comportamiento WHERE id_impacto = :i"
)

_SQL_CODIGOS_PENDIENTES = text(
    """
    SELECT DISTINCT f.id_codigo
    FROM fact_comportamiento AS f
    JOIN dim_detalle_comportamiento AS d ON f.id_jerarquia = d.id_jerarquia
    WHERE d.id_comportamiento = :c
      AND f.fecha_evento IS NOT NULL
      AND date(f.fecha_evento) >= date('now', :ventana)
      AND f.id_codigo IS NOT NULL
      AND f.id_codigo NOT IN (
          SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = :cancelacion
      )
      AND f.id_hecho_comportamiento NOT IN (
          SELECT id_hecho_comportamiento FROM reincidencia_detalle
      )
    """
)

_SQL_HECHOS_PENDIENTES = text(
    """
    SELECT f.id_hecho_comportamiento, f.fecha_evento, f.caso_bitacora_ticket,
           f.hora_evento, f.vehiculo, f.fuente_infraccion, f.responsable_pqrs_cot,
           f.id_jerarquia
    FROM fact_comportamiento AS f
    JOIN dim_detalle_comportamiento AS d ON f.id_jerarquia = d.id_jerarquia
    WHERE d.id_comportamiento = :c AND f.id_codigo = :cod
      AND f.fecha_evento IS NOT NULL
      AND date(f.fecha_evento) >= date('now', :ventana)
      AND f.id_hecho_comportamiento NOT IN (
          SELECT id_hecho_comportamiento FROM reincidencia_detalle
      )
    ORDER BY f.fecha_evento
    """
)

_SQL_SIGUIENTE_ID_REINCIDENCIA = text(
    "SELECT COALESCE(MAX(id_reincidencia), 0) + 1 FROM fact_reincidencia"
)

_SQL_INSERT_REINCIDENCIA = text(
    """
    INSERT INTO fact_reincidencia
        (id_reincidencia, id_impacto, id_comportamiento, id_codigo, fecha_inicio,
         fecha_fin, cantidad, resumen, usuario_registra)
    VALUES (:id, :i, :c, :co, :fi, :ff, :cant, :r, :u)
    """
)

_SQL_INSERT_REINCIDENCIA_DETALLE = text(
    "INSERT INTO reincidencia_detalle (id_reincidencia, id_hecho_comportamiento) VALUES (:r, :h)"
)

_SQL_DETALLE_REINCIDENCIA_IDS = text(
    "SELECT id_reincidencia, id_hecho_comportamiento FROM reincidencia_detalle "
    "ORDER BY id_reincidencia, id_hecho_comportamiento"
)

_SQL_EMPRESAS = text("SELECT id_empresa, nombre_empresa FROM dim_empresa ORDER BY nombre_empresa")

_SQL_REINCIDENCIAS = text(
    """
    SELECT r.id_reincidencia, r.id_codigo, e.nombre_empresa, i.impacto, c.comportamiento,
           r.fecha_inicio, r.fecha_fin, r.cantidad, r.determinacion_mc, r.estado,
           r.id_hecho_evento, r.usuario_registra
    FROM fact_reincidencia AS r
    LEFT JOIN dim_impacto AS i ON r.id_impacto = i.id_impacto
    LEFT JOIN dim_comportamiento AS c ON r.id_comportamiento = c.id_comportamiento
    LEFT JOIN dim_codigo AS dc ON r.id_codigo = dc.id_codigo
    LEFT JOIN dim_empresa AS e ON dc.id_empresa = e.id_empresa
    ORDER BY r.id_reincidencia DESC
    """
)

_SQL_DETALLE_REINCIDENCIAS = text(
    """
    SELECT r.id_reincidencia, r.id_codigo, e.nombre_empresa, i.impacto, c.comportamiento,
           r.fecha_inicio, r.fecha_fin, r.determinacion_mc,
           d.descripcion_comportamiento, f.caso_bitacora_ticket, f.fecha_evento,
           f.vehiculo, f.viaje, f.tarea, f.hora_evento, f.ruta,
           f.clase_servicio, f.tipo_servicio, f.fuente_infraccion, f.placa
    FROM reincidencia_detalle AS rd
    JOIN fact_reincidencia AS r ON rd.id_reincidencia = r.id_reincidencia
    JOIN fact_comportamiento AS f ON rd.id_hecho_comportamiento = f.id_hecho_comportamiento
    JOIN dim_detalle_comportamiento AS d ON f.id_jerarquia = d.id_jerarquia
    LEFT JOIN dim_impacto AS i ON r.id_impacto = i.id_impacto
    LEFT JOIN dim_comportamiento AS c ON r.id_comportamiento = c.id_comportamiento
    LEFT JOIN dim_codigo AS dc ON r.id_codigo = dc.id_codigo
    LEFT JOIN dim_empresa AS e ON dc.id_empresa = e.id_empresa
    ORDER BY r.id_reincidencia DESC
    """
)

_SQL_ACTUALIZAR_DETERMINACION = text(
    "UPDATE fact_reincidencia SET determinacion_mc = :d WHERE id_reincidencia = :r"
)

_SQL_REINCIDENCIA_ACCION = text(
    "SELECT id_codigo, id_hecho_evento FROM fact_reincidencia WHERE id_reincidencia = :r"
)

_SQL_SIGUIENTE_ID_EVENTO = text(
    "SELECT COALESCE(MAX(id_hecho_evento), 0) + 1 FROM fact_eventos_operador"
)

_SQL_INSERT_EVENTO = text(
    """
    INSERT INTO fact_eventos_operador
        (id_hecho_evento, id_codigo, id_tipo_evento, fecha_observacion, observacion,
         id_vigencia, usuario_registra, fecha_registro)
    VALUES (:id, :cod, :tip, :f, :o, :vigencia, :u, CURRENT_TIMESTAMP)
    """
)

_SQL_UPDATE_EVENTO = text(
    "UPDATE fact_eventos_operador SET id_tipo_evento = :tip, "
    "fecha_observacion = :f, observacion = :o WHERE id_hecho_evento = :e"
)

_SQL_ACTUALIZAR_EVENTO_REINCIDENCIA = text(
    "UPDATE fact_reincidencia SET id_hecho_evento = :e WHERE id_reincidencia = :r"
)

_SQL_AUDITORIA = text(
    "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:usuario, :accion, :detalles)"
)


# --- Normalización de valores ------------------------------------------------
def _texto(valor: object) -> str | None:
    """Normaliza un valor de celda a texto sin espacios sobrantes.

    Args:
        valor: Valor leído de la base de datos o de Excel.

    Returns:
        El texto limpio, o ``None`` si el valor está vacío o es ``NaN``.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    return texto


def _entero(valor: object) -> int | None:
    """Convierte un valor de celda en entero, admitiendo decimales de Excel.

    Args:
        valor: Valor leído de la base de datos o de Excel.

    Returns:
        El entero resultante, o ``None`` si el valor está vacío o es inválido.
    """
    if valor is None:
        return None
    try:
        if str(valor).strip().lower() in ("", "nan"):
            return None
        return int(float(str(valor)))
    except (TypeError, ValueError):
        return None


def _como_fecha(valor: object) -> date | None:
    """Convierte un valor de fecha a ``datetime.date`` de forma robusta.

    Args:
        valor: Fecha almacenada como texto, ``datetime``, ``date`` o ``None``.

    Returns:
        La fecha interpretada, o ``None`` si el valor está vacío o es inválido.
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def _formatear_fecha(valor: date | None) -> str | None:
    """Formatea una fecha como texto ISO para los parámetros enlazados.

    Args:
        valor: Fecha a formatear, o ``None``.

    Returns:
        La fecha en formato ``YYYY-MM-DD``, o ``None`` si no hay valor.
    """
    return valor.isoformat() if valor is not None else None


def _formatear_caso(valor: object) -> str:
    """Normaliza el número de caso de un hecho para el resumen de reincidencia.

    Args:
        valor: Valor crudo del caso (``caso_bitacora_ticket``).

    Returns:
        El caso como entero sin decimales cuando es numérico; el texto original
        recortado cuando no lo es; ``"N/A"`` cuando está vacío.
    """
    texto = _texto(valor)
    if texto is None:
        return "N/A"
    candidato = texto.replace(".", "").replace("-", "")
    if candidato.isdigit():
        return str(int(float(texto)))
    return texto


class ComportamientosRepository:
    """Repositorio de comportamientos y reincidencia sobre la base de datos.

    Concentra toda la ejecución de SQLAlchemy del reporte de comportamientos. El
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

    # --- RF-01: registro individual ------------------------------------------
    def buscar_operador_por_codigo(self, codigo: int) -> OperadorComportamientoInfo | None:
        """Busca un operador por su código de operación activo.

        Args:
            codigo: Código de operación (``dim_codigo.id_codigo``).

        Returns:
            El operador si el código está vigente; ``None`` en caso contrario.
        """
        parametros = {"n": codigo, "vigencia": VIGENCIA_ACTIVA}
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_OPERADOR_POR_CODIGO, parametros).mappings().first()
        return self._mapear_operador(fila) if fila is not None else None

    def buscar_operador_por_cedula(self, cedula: int) -> OperadorComportamientoInfo | None:
        """Busca un operador por cédula y devuelve su código activo más reciente.

        Args:
            cedula: Documento del operador (``dim_persona.id_persona``).

        Returns:
            El operador si tiene un código vigente; ``None`` en caso contrario.
        """
        parametros = {"n": cedula, "vigencia": VIGENCIA_ACTIVA}
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_OPERADOR_POR_CEDULA, parametros).mappings().first()
        return self._mapear_operador(fila) if fila is not None else None

    def listar_detalles_comportamiento(self) -> list[DetalleComportamientoInfo]:
        """Lista las jerarquías de comportamiento ordenadas por descripción.

        Returns:
            Los detalles de comportamiento disponibles.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_DETALLES_COMPORTAMIENTO).mappings().all()
        return [
            DetalleComportamientoInfo(
                id_jerarquia=int(fila["id_jerarquia"]),
                descripcion=str(fila["descripcion_comportamiento"] or ""),
            )
            for fila in filas
        ]

    def registrar_comportamiento(self, datos: DatosComportamiento, usuario: str) -> int:
        """Registra un comportamiento individual y su auditoría en una transacción.

        Args:
            datos: Datos del comportamiento a registrar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            El identificador del comportamiento creado.
        """
        with self.motor.begin() as conexion:
            nuevo_id = self._siguiente_id_comportamiento(conexion)
            conexion.execute(_SQL_INSERT_COMPORTAMIENTO, self._parametros(datos, nuevo_id, usuario))
            detalles = f"Codigo: {datos.id_codigo}, Jerarquia: {datos.id_jerarquia}"
            self._auditar(conexion, usuario, ACCION_REGISTRO_COMPORTAMIENTO, detalles)
        return nuevo_id

    # --- RF-02: carga masiva --------------------------------------------------
    def resolver_codigo_activo(self, codigo: int) -> int | None:
        """Devuelve el código si está activo en ``dim_codigo``.

        Args:
            codigo: Código de operación a validar.

        Returns:
            El código vigente, o ``None`` si no existe o está inactivo.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(
                _SQL_CODIGO_ACTIVO, {"c": codigo, "vigencia": VIGENCIA_ACTIVA}
            ).first()
        return int(fila[0]) if fila is not None else None

    def resolver_jerarquia_por_descripcion(self, descripcion: str) -> int | None:
        """Resuelve la jerarquía de comportamiento por su descripción exacta.

        Args:
            descripcion: Texto exacto de la jerarquía.

        Returns:
            El identificador de la jerarquía, o ``None`` si no existe.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_JERARQUIA_POR_DESCRIPCION, {"d": descripcion}).first()
        return int(fila[0]) if fila is not None else None

    def buscar_comportamiento_por_caso(self, caso: str) -> int | None:
        """Busca el comportamiento existente con un ``caso_bitacora_ticket``.

        Args:
            caso: Caso, bitácora o ticket.

        Returns:
            El identificador del comportamiento, o ``None`` si no existe.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_COMPORTAMIENTO_POR_CASO, {"c": caso}).first()
        return int(fila[0]) if fila is not None else None

    def guardar_comportamientos(
        self, filas: Sequence[DatosComportamiento], usuario: str
    ) -> tuple[int, int]:
        """Inserta y actualiza comportamientos y registra una única auditoría.

        Args:
            filas: Comportamientos a procesar; los que traen ``id_existente`` se
                actualizan y el resto se insertan.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Una tupla ``(nuevos, actualizados)`` con los conteos procesados.
        """
        nuevos = 0
        actualizados = 0
        with self.motor.begin() as conexion:
            siguiente = self._siguiente_id_comportamiento(conexion)
            for datos in filas:
                if datos.id_existente is not None:
                    conexion.execute(
                        _SQL_UPDATE_COMPORTAMIENTO,
                        self._parametros(datos, datos.id_existente, usuario),
                    )
                    actualizados += 1
                else:
                    conexion.execute(
                        _SQL_INSERT_COMPORTAMIENTO, self._parametros(datos, siguiente, usuario)
                    )
                    siguiente += 1
                    nuevos += 1
            detalles = f"Nuevos: {nuevos}, Actualizados: {actualizados}"
            self._auditar(conexion, usuario, ACCION_CARGA_MASIVA_COMPORTAMIENTOS, detalles)
        return nuevos, actualizados

    # --- RF-03: reincidencia --------------------------------------------------
    def listar_impactos(self) -> list[ImpactoInfo]:
        """Lista los impactos con máximo mayor que cero.

        Returns:
            Los impactos configurados para reincidencia.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_IMPACTOS).mappings().all()
        return [
            ImpactoInfo(
                id_impacto=int(fila["id_impacto"]),
                impacto=str(fila["impacto"] or ""),
                maximo=int(fila["maximo"]),
                dias_maximo=int(fila["dias_maximo"]),
            )
            for fila in filas
        ]

    def listar_comportamientos_por_impacto(
        self, id_impacto: int
    ) -> list[ComportamientoReincidenciaInfo]:
        """Lista los comportamientos asociados a un impacto.

        Args:
            id_impacto: Identificador del impacto.

        Returns:
            Los comportamientos del impacto.
        """
        with self.motor.connect() as conexion:
            filas = (
                conexion.execute(_SQL_COMPORTAMIENTOS_POR_IMPACTO, {"i": id_impacto})
                .mappings()
                .all()
            )
        return [
            ComportamientoReincidenciaInfo(
                id_comportamiento=int(fila["id_comportamiento"]),
                comportamiento=str(fila["comportamiento"] or ""),
            )
            for fila in filas
        ]

    def listar_codigos_pendientes(self, id_comportamiento: int) -> list[int]:
        """Lista los códigos con hechos pendientes para un comportamiento.

        Args:
            id_comportamiento: Identificador del comportamiento.

        Returns:
            Los códigos de operación con hechos aún no evaluados en la ventana.
        """
        parametros = {
            "c": id_comportamiento,
            "ventana": VENTANA_REINCIDENCIA_SQL,
            "cancelacion": TIPO_EVENTO_CANCELACION,
        }
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_CODIGOS_PENDIENTES, parametros).all()
        return [int(fila[0]) for fila in filas if fila[0] is not None]

    def listar_hechos_pendientes(
        self, id_comportamiento: int, id_codigo: int
    ) -> list[HechoComportamientoInfo]:
        """Lista los hechos pendientes de un comportamiento y código.

        Args:
            id_comportamiento: Identificador del comportamiento.
            id_codigo: Código del operador.

        Returns:
            Los hechos ordenados por fecha.
        """
        parametros = {
            "c": id_comportamiento,
            "cod": id_codigo,
            "ventana": VENTANA_REINCIDENCIA_SQL,
        }
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_HECHOS_PENDIENTES, parametros).mappings().all()
        return [
            HechoComportamientoInfo(
                id_hecho_comportamiento=int(fila["id_hecho_comportamiento"]),
                fecha_evento=fila["fecha_evento"],
                caso_bitacora_ticket=fila["caso_bitacora_ticket"],
                hora_evento=fila["hora_evento"],
                vehiculo=fila["vehiculo"],
                fuente_infraccion=fila["fuente_infraccion"],
                responsable_pqrs_cot=fila["responsable_pqrs_cot"],
                id_jerarquia=int(fila["id_jerarquia"]),
            )
            for fila in filas
        ]

    def listar_pares_reincidencia(self) -> set[tuple[int, int]]:
        """Lista las combinaciones de hechos ya vinculadas a un caso.

        Returns:
            Conjunto de tuplas ``(hecho_1, hecho_2)`` por cada caso registrado.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_DETALLE_REINCIDENCIA_IDS).all()
        agrupados: dict[int, list[int]] = {}
        for id_reincidencia, id_hecho in filas:
            agrupados.setdefault(int(id_reincidencia), []).append(int(id_hecho))
        pares: set[tuple[int, int]] = set()
        for hechos in agrupados.values():
            if len(hechos) == 2:
                primero, segundo = hechos
                pares.add((min(primero, segundo), max(primero, segundo)))
        return pares

    def generar_reincidencias(self, usuario: str = "") -> int:
        """Analiza los hechos y genera los casos de reincidencia nuevos.

        Conserva la lógica heredada: un impacto ``grave`` genera un caso por cada
        hecho; el resto genera un caso por cada par de hechos dentro de la ventana
        de días del impacto, evitando pares ya registrados.

        Args:
            usuario: Usuario que ejecuta la acción (se guarda en cada caso).

        Returns:
            El número de casos de reincidencia creados.
        """
        nuevos = 0
        for impacto in self.listar_impactos():
            for comportamiento in self.listar_comportamientos_por_impacto(impacto.id_impacto):
                for id_codigo in self.listar_codigos_pendientes(comportamiento.id_comportamiento):
                    hechos = self.listar_hechos_pendientes(
                        comportamiento.id_comportamiento, id_codigo
                    )
                    if not hechos:
                        continue
                    if impacto.impacto.lower() == NOMBRE_IMPACTO_GRAVE:
                        for hecho in hechos:
                            nuevos += self._crear_caso_individual(
                                impacto, comportamiento, id_codigo, hecho, usuario
                            )
                    else:
                        nuevos += self._crear_casos_pareja(
                            impacto, comportamiento, id_codigo, hechos, usuario
                        )
        return nuevos

    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas ordenadas por nombre.

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

    def listar_reincidencias(self) -> list[ReincidenciaInfo]:
        """Lista los casos de reincidencia ordenados del más reciente al más antiguo.

        Returns:
            Los casos de reincidencia.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_REINCIDENCIAS).mappings().all()
        return [self._mapear_reincidencia(fila) for fila in filas]

    def listar_detalle_reincidencias(self) -> list[DetalleReincidenciaInfo]:
        """Lista el detalle de hechos de todos los casos de reincidencia.

        Returns:
            El detalle de los hechos asociados a los casos.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_DETALLE_REINCIDENCIAS).mappings().all()
        return [self._mapear_detalle_reincidencia(fila) for fila in filas]

    def obtener_reincidencia_accion(self, id_reincidencia: int) -> ReincidenciaAccionInfo | None:
        """Obtiene el código y el evento asociado de un caso de reincidencia.

        Args:
            id_reincidencia: Identificador del caso.

        Returns:
            Los datos mínimos del caso, o ``None`` si no existe.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_REINCIDENCIA_ACCION, {"r": id_reincidencia}).first()
        if fila is None:
            return None
        return ReincidenciaAccionInfo(
            id_codigo=int(fila[0]),
            id_hecho_evento=int(fila[1]) if fila[1] is not None else None,
        )

    def actualizar_determinacion(
        self, id_reincidencia: int, determinacion: str, usuario: str
    ) -> None:
        """Actualiza la determinación de un caso y registra la auditoría.

        Args:
            id_reincidencia: Identificador del caso.
            determinacion: Nueva determinación de Metrocali.
            usuario: Usuario que ejecuta la acción.
        """
        with self.motor.begin() as conexion:
            conexion.execute(
                _SQL_ACTUALIZAR_DETERMINACION, {"d": determinacion, "r": id_reincidencia}
            )
            detalles = f"ID: {id_reincidencia}, Decision: {determinacion}"
            self._auditar(conexion, usuario, ACCION_DETERMINAR_REINCIDENCIA, detalles)

    def registrar_accion_reincidencia(
        self,
        accion: AccionReincidencia,
        usuario: str,
    ) -> int:
        """Registra o actualiza una acción de reincidencia en el historial.

        Args:
            accion: Acción a registrar; si trae ``id_hecho_evento`` se actualiza el
                evento existente, y si no, se inserta uno nuevo y se vincula al caso.
            usuario: Usuario que ejecuta la acción.

        Returns:
            El identificador del evento registrado o actualizado.
        """
        with self.motor.begin() as conexion:
            if accion.id_hecho_evento is not None:
                conexion.execute(
                    _SQL_UPDATE_EVENTO,
                    {
                        "tip": accion.id_tipo_evento,
                        "f": _formatear_fecha(accion.fecha_observacion),
                        "o": accion.observacion,
                        "e": accion.id_hecho_evento,
                    },
                )
                id_evento = accion.id_hecho_evento
                accion_aud = ACCION_ACTUALIZAR_ACCION_REINCIDENCIA
            else:
                id_evento = int(conexion.execute(_SQL_SIGUIENTE_ID_EVENTO).scalar_one())
                conexion.execute(
                    _SQL_INSERT_EVENTO,
                    {
                        "id": id_evento,
                        "cod": accion.id_codigo,
                        "tip": accion.id_tipo_evento,
                        "f": _formatear_fecha(accion.fecha_observacion),
                        "o": accion.observacion,
                        "vigencia": VIGENCIA_ACTIVA,
                        "u": usuario,
                    },
                )
                conexion.execute(
                    _SQL_ACTUALIZAR_EVENTO_REINCIDENCIA,
                    {"e": id_evento, "r": accion.id_reincidencia},
                )
                accion_aud = ACCION_REGISTRAR_ACCION_REINCIDENCIA
            detalles = (
                f"Reinc #{accion.id_reincidencia}, Cod: {accion.id_codigo}, "
                f"Tipo: {accion.id_tipo_evento}"
            )
            self._auditar(conexion, usuario, accion_aud, detalles)
        return id_evento

    def importar_acciones_reincidencia(
        self, acciones: Sequence[AccionReincidencia], usuario: str
    ) -> tuple[int, int]:
        """Importa acciones de reincidencia y registra una única auditoría.

        Args:
            acciones: Acciones a registrar o actualizar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Una tupla ``(insertados, actualizados)`` con los conteos procesados.
        """
        insertados = 0
        actualizados = 0
        with self.motor.begin() as conexion:
            for accion in acciones:
                if accion.id_hecho_evento is not None:
                    conexion.execute(
                        _SQL_UPDATE_EVENTO,
                        {
                            "tip": accion.id_tipo_evento,
                            "f": _formatear_fecha(accion.fecha_observacion),
                            "o": accion.observacion,
                            "e": accion.id_hecho_evento,
                        },
                    )
                    actualizados += 1
                else:
                    id_evento = int(conexion.execute(_SQL_SIGUIENTE_ID_EVENTO).scalar_one())
                    conexion.execute(
                        _SQL_INSERT_EVENTO,
                        {
                            "id": id_evento,
                            "cod": accion.id_codigo,
                            "tip": accion.id_tipo_evento,
                            "f": _formatear_fecha(accion.fecha_observacion),
                            "o": accion.observacion,
                            "vigencia": VIGENCIA_ACTIVA,
                            "u": usuario,
                        },
                    )
                    conexion.execute(
                        _SQL_ACTUALIZAR_EVENTO_REINCIDENCIA,
                        {"e": id_evento, "r": accion.id_reincidencia},
                    )
                    insertados += 1
            detalles = f"Nuevos: {insertados}, Actualizados: {actualizados}"
            self._auditar(conexion, usuario, ACCION_IMPORTAR_ACCIONES_REINCIDENCIA, detalles)
        return insertados, actualizados

    # --- Auxiliares internos --------------------------------------------------
    def _siguiente_id_comportamiento(self, conexion: Connection) -> int:
        """Calcula el siguiente identificador de ``fact_comportamiento``.

        Args:
            conexion: Conexión activa dentro de la transacción.

        Returns:
            ``MAX(id_hecho_comportamiento) + 1`` o ``1`` si la tabla está vacía.
        """
        return int(conexion.execute(_SQL_SIGUIENTE_ID_COMPORTAMIENTO).scalar_one())

    def _crear_caso_individual(
        self,
        impacto: ImpactoInfo,
        comportamiento: ComportamientoReincidenciaInfo,
        id_codigo: int,
        hecho: HechoComportamientoInfo,
        usuario: str,
    ) -> int:
        """Crea el caso de un impacto grave para un único hecho.

        Args:
            impacto: Impacto del caso.
            comportamiento: Comportamiento del hecho.
            id_codigo: Código del operador.
            hecho: Hecho que origina el caso.
            usuario: Usuario que genera el caso.

        Returns:
            ``1`` si se creó el caso.
        """
        caso = _formatear_caso(hecho.caso_bitacora_ticket)
        resumen = f"Caso: {caso} | Fecha: {hecho.fecha_evento} | Hora: {hecho.hora_evento or 'N/A'}"
        fecha = _como_fecha(hecho.fecha_evento)
        self.registrar_reincidencia(
            id_impacto=impacto.id_impacto,
            id_comportamiento=comportamiento.id_comportamiento,
            id_codigo=id_codigo,
            fecha_inicio=fecha,
            fecha_fin=fecha,
            cantidad=1,
            resumen=resumen,
            usuario=usuario,
            hechos=[hecho.id_hecho_comportamiento],
        )
        return 1

    def _crear_casos_pareja(
        self,
        impacto: ImpactoInfo,
        comportamiento: ComportamientoReincidenciaInfo,
        id_codigo: int,
        hechos: list[HechoComportamientoInfo],
        usuario: str,
    ) -> int:
        """Crea los casos por pares de un impacto no grave.

        Args:
            impacto: Impacto del caso.
            comportamiento: Comportamiento de los hechos.
            id_codigo: Código del operador.
            hechos: Hechos pendientes ordenados por fecha.
            usuario: Usuario que genera los casos.

        Returns:
            El número de casos nuevos creados.
        """
        existentes = self.listar_pares_reincidencia()
        creados = 0
        for indice_a in range(len(hechos) - 1):
            for indice_b in range(indice_a + 1, len(hechos)):
                hecho_a = hechos[indice_a]
                hecho_b = hechos[indice_b]
                fecha_a = _como_fecha(hecho_a.fecha_evento)
                fecha_b = _como_fecha(hecho_b.fecha_evento)
                if fecha_a is None or fecha_b is None:
                    continue
                if (fecha_b - fecha_a).days > impacto.dias_maximo:
                    continue
                par = tuple(
                    sorted((hecho_a.id_hecho_comportamiento, hecho_b.id_hecho_comportamiento))
                )
                if par in existentes:
                    continue
                resumen = (
                    f"1) Caso:{_formatear_caso(hecho_a.caso_bitacora_ticket)} "
                    f"Fecha:{hecho_a.fecha_evento} | "
                    f"2) Caso:{_formatear_caso(hecho_b.caso_bitacora_ticket)} "
                    f"Fecha:{hecho_b.fecha_evento}"
                )
                self.registrar_reincidencia(
                    id_impacto=impacto.id_impacto,
                    id_comportamiento=comportamiento.id_comportamiento,
                    id_codigo=id_codigo,
                    fecha_inicio=fecha_a,
                    fecha_fin=fecha_b,
                    cantidad=2,
                    resumen=resumen,
                    usuario=usuario,
                    hechos=[hecho_a.id_hecho_comportamiento, hecho_b.id_hecho_comportamiento],
                )
                creados += 1
        return creados

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
        """Registra un caso de reincidencia y sus hechos en una transacción.

        Args:
            id_impacto: Impacto del caso.
            id_comportamiento: Comportamiento del caso.
            id_codigo: Código del operador.
            fecha_inicio: Fecha inicial del caso.
            fecha_fin: Fecha final del caso.
            cantidad: Número de hechos del caso.
            resumen: Resumen textual del caso.
            usuario: Usuario que registra (heredado; puede venir vacío).
            hechos: Identificadores de los hechos que originan el caso.

        Returns:
            El identificador del caso creado.
        """
        with self.motor.begin() as conexion:
            nuevo_id = int(conexion.execute(_SQL_SIGUIENTE_ID_REINCIDENCIA).scalar_one())
            conexion.execute(
                _SQL_INSERT_REINCIDENCIA,
                {
                    "id": nuevo_id,
                    "i": id_impacto,
                    "c": id_comportamiento,
                    "co": id_codigo,
                    "fi": _formatear_fecha(fecha_inicio),
                    "ff": _formatear_fecha(fecha_fin),
                    "cant": cantidad,
                    "r": resumen,
                    "u": usuario,
                },
            )
            for id_hecho in hechos:
                conexion.execute(
                    _SQL_INSERT_REINCIDENCIA_DETALLE, {"r": nuevo_id, "h": int(id_hecho)}
                )
        return nuevo_id

    @staticmethod
    def _mapear_operador(fila: RowMapping) -> OperadorComportamientoInfo:
        """Mapea una fila de operador al DTO de infraestructura.

        Args:
            fila: Fila devuelta por SQLAlchemy.

        Returns:
            El operador construido a partir de la fila.
        """
        return OperadorComportamientoInfo(
            id_codigo=int(fila["id_codigo"]),
            cedula=int(fila["cedula"]),
            nombres=str(fila["nombres"] or "").strip(),
            primer_apellido=str(fila["primer_apellido"] or "").strip(),
        )

    @staticmethod
    def _mapear_reincidencia(fila: RowMapping) -> ReincidenciaInfo:
        """Mapea una fila de caso de reincidencia a su DTO.

        Args:
            fila: Fila devuelta por SQLAlchemy.

        Returns:
            El caso de reincidencia construido a partir de la fila.
        """
        return ReincidenciaInfo(
            id_reincidencia=int(fila["id_reincidencia"]),
            id_codigo=fila["id_codigo"],
            nombre_empresa=fila["nombre_empresa"],
            impacto=fila["impacto"],
            comportamiento=fila["comportamiento"],
            fecha_inicio=fila["fecha_inicio"],
            fecha_fin=fila["fecha_fin"],
            cantidad=fila["cantidad"],
            determinacion_mc=fila["determinacion_mc"],
            estado=fila["estado"],
            id_hecho_evento=fila["id_hecho_evento"],
            usuario_registra=fila["usuario_registra"],
        )

    @staticmethod
    def _mapear_detalle_reincidencia(fila: RowMapping) -> DetalleReincidenciaInfo:
        """Mapea una fila de detalle de reincidencia a su DTO.

        Args:
            fila: Fila devuelta por SQLAlchemy.

        Returns:
            El detalle del hecho construido a partir de la fila.
        """
        return DetalleReincidenciaInfo(
            id_reincidencia=int(fila["id_reincidencia"]),
            id_codigo=fila["id_codigo"],
            nombre_empresa=fila["nombre_empresa"],
            impacto=fila["impacto"],
            comportamiento=fila["comportamiento"],
            fecha_inicio=fila["fecha_inicio"],
            fecha_fin=fila["fecha_fin"],
            determinacion_mc=fila["determinacion_mc"],
            descripcion_comportamiento=fila["descripcion_comportamiento"],
            caso_bitacora_ticket=fila["caso_bitacora_ticket"],
            fecha_evento=fila["fecha_evento"],
            vehiculo=fila["vehiculo"],
            viaje=fila["viaje"],
            tarea=fila["tarea"],
            hora_evento=fila["hora_evento"],
            ruta=fila["ruta"],
            clase_servicio=fila["clase_servicio"],
            tipo_servicio=fila["tipo_servicio"],
            fuente_infraccion=fila["fuente_infraccion"],
            placa=fila["placa"],
        )

    @staticmethod
    def _parametros(datos: DatosComportamiento, id_hecho: int, usuario: str) -> dict[str, object]:
        """Traduce los datos de un comportamiento a parámetros enlazados.

        Args:
            datos: Datos del comportamiento.
            id_hecho: Identificador a asignar al registro.
            usuario: Usuario que registra el comportamiento.

        Returns:
            El diccionario de parámetros para las sentencias de inserción/edición.
        """
        return {
            "id": id_hecho,
            "j": datos.id_jerarquia,
            "cod": datos.id_codigo,
            "f": _formatear_fecha(datos.fecha_evento),
            "h": datos.hora_evento,
            "n": datos.nota,
            "v": datos.vehiculo,
            "vi": datos.viaje,
            "ta": datos.tarea,
            "caso": datos.caso_bitacora_ticket,
            "r": datos.ruta,
            "ss": datos.sitio_salida,
            "sn": datos.sitio_novedad,
            "nl": datos.numero_lesionados,
            "oc": datos.observacion_concesionario,
            "rmc": datos.respuesta_mc,
            "rpqrs": datos.responsable_pqrs_cot,
            "dir": datos.direccion_infraccion,
            "cs": datos.clase_servicio,
            "ts": datos.tipo_servicio,
            "fi": datos.fuente_infraccion,
            "pl": datos.placa,
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
            _SQL_AUDITORIA, {"usuario": usuario, "accion": accion, "detalles": detalles}
        )


__all__ = [
    "ACCION_ACTUALIZAR_ACCION_REINCIDENCIA",
    "ACCION_CARGA_MASIVA_COMPORTAMIENTOS",
    "ACCION_DETERMINAR_REINCIDENCIA",
    "ACCION_IMPORTAR_ACCIONES_REINCIDENCIA",
    "ACCION_REGISTRAR_ACCION_REINCIDENCIA",
    "ACCION_REGISTRO_COMPORTAMIENTO",
    "MESES_VENTANA_REINCIDENCIA",
    "NOMBRE_IMPACTO_GRAVE",
    "TIPO_EVENTO_CANCELACION",
    "VENTANA_REINCIDENCIA_SQL",
    "AccionReincidencia",
    "ComportamientoReincidenciaInfo",
    "ComportamientosRepository",
    "DatosComportamiento",
    "DetalleComportamientoInfo",
    "DetalleReincidenciaInfo",
    "EmpresaInfo",
    "HechoComportamientoInfo",
    "ImpactoInfo",
    "OperadorComportamientoInfo",
    "ReincidenciaAccionInfo",
    "ReincidenciaInfo",
]
