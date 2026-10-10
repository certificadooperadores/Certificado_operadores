"""Repositorio de eventos de operadores (capa de infraestructura).

Encapsula **todo** el acceso a datos de la tabla ``fact_eventos_operador`` y sus
dimensiones asociadas: la búsqueda de eventos, el listado de tipos de evento, el
agrupamiento por lote (minuto de cargue) y las mutaciones de reactivación,
anulación y eliminación de registros individuales o de lotes completos. Cada
mutación registra su acción en ``log_auditoria`` dentro de la misma transacción.

La interfaz de usuario no conoce el esquema ni el motor: solo consume los DTOs
que devuelve este repositorio. Todas las consultas usan parámetros enlazados
(nunca SQL construido con datos del usuario) y la cláusula ``IN`` se expande con
``bindparam(expanding=True)``.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import bindparam, text

from certificado_operadores.domain.models import VIGENCIA_ACTIVA, VIGENCIA_ANULADA

if TYPE_CHECKING:
    from sqlalchemy import TextClause
    from sqlalchemy.engine import Connection, Engine, RowMapping

LIMITE_POR_DEFECTO = 500
"""Número máximo de eventos que devuelve una búsqueda con filtros."""

FORMATO_LOTE = "%Y-%m-%d %H:%M"
"""Formato de fecha y minuto con el que se agrupan los eventos en un lote."""

ESTADO_VIGENTE_TEXTO = "Vigente"
"""Etiqueta legible de un evento vigente."""

ESTADO_ANULADO_TEXTO = "Anulado"
"""Etiqueta legible de un evento anulado."""

ACCION_REACTIVAR_REGISTROS = "Reactivar Registros"
"""Acción de auditoría al reactivar registros individuales."""

ACCION_ANULAR_REGISTROS = "Anular Registros"
"""Acción de auditoría al anular registros individuales."""

ACCION_ELIMINAR_REGISTROS = "Eliminar Registros"
"""Acción de auditoría al eliminar registros individuales."""

ACCION_REACTIVAR_LOTE = "Reactivar Lote"
"""Acción de auditoría al reactivar un lote completo."""

ACCION_ANULAR_LOTE = "Anular Lote"
"""Acción de auditoría al anular un lote completo."""

ACCION_ELIMINAR_LOTE = "Borrar Lote"
"""Acción de auditoría al eliminar un lote completo."""

ACCION_REACTIVAR_TABLA = "Reactivar"
"""Prefijo de auditoría al reactivar registros de una tabla de corrección."""

ACCION_ANULAR_TABLA = "Anular"
"""Prefijo de auditoría al anular registros de una tabla de corrección."""

ACCION_ELIMINAR_TABLA = "Eliminar"
"""Prefijo de auditoría al eliminar registros de una tabla de corrección."""


@dataclass(frozen=True)
class TipoEventoInfo:
    """Tipo de evento disponible para filtrar la búsqueda.

    Attributes:
        id_tipo_evento: Identificador del tipo de evento.
        nombre_evento: Nombre legible del tipo de evento.
    """

    id_tipo_evento: int
    nombre_evento: str


@dataclass(frozen=True)
class EventoInfo:
    """Evento de operador con los datos necesarios para la tabla de la UI.

    Attributes:
        id_hecho_evento: Identificador del hecho (clave primaria).
        id_codigo: Código de operación asociado al evento.
        cedula: Documento del operador (``dim_persona.id_persona``).
        nombre: Nombre completo del operador.
        nombre_evento: Nombre del tipo de evento.
        fecha: Fecha de registro del evento tal como la devuelve el motor.
        id_vigencia: Vigencia del evento (activa o anulada).
    """

    id_hecho_evento: int
    id_codigo: int
    cedula: int
    nombre: str
    nombre_evento: str
    fecha: str
    id_vigencia: int

    @property
    def estado(self) -> str:
        """Etiqueta legible de la vigencia (``Vigente`` o ``Anulado``)."""
        if self.id_vigencia == VIGENCIA_ACTIVA:
            return ESTADO_VIGENTE_TEXTO
        return ESTADO_ANULADO_TEXTO


@dataclass(frozen=True)
class LoteInfo:
    """Lote de eventos agrupados por el minuto de cargue.

    Attributes:
        lote: Marca temporal ``YYYY-MM-DD HH:MM`` que identifica el lote.
        total: Número de eventos del lote.
    """

    lote: str
    total: int


@dataclass(frozen=True)
class FiltroEventos:
    """Criterios de búsqueda de eventos.

    Todos los campos son opcionales: un valor ``None`` desactiva ese criterio.

    Attributes:
        codigo: Código de operación (``dim_codigo.id_codigo``).
        cedula: Documento del operador (``dim_persona.id_persona``).
        id_tipo_evento: Identificador del tipo de evento.
        vigencia: Vigencia deseada (activa o anulada).
        fecha_desde: Fecha mínima de registro (inclusive).
        fecha_hasta: Fecha máxima de registro (inclusive).
        limite: Número máximo de filas a devolver.
    """

    codigo: int | None = None
    cedula: int | None = None
    id_tipo_evento: int | None = None
    vigencia: int | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    limite: int = LIMITE_POR_DEFECTO


@dataclass(frozen=True)
class ColumnaTabla:
    """Columna visible de una tabla de corrección.

    Attributes:
        etiqueta: Encabezado legible que se muestra en la tabla de la UI.
        expresion: Expresión SQL que produce el valor de la columna.
    """

    etiqueta: str
    expresion: str


@dataclass(frozen=True)
class DefinicionTabla:
    """Metadatos de una tabla soportada por la corrección de registros.

    Concentra, como configuración declarativa, el nombre de la tabla, su clave
    primaria, la columna de vigencia y las columnas visibles. La UI y el
    repositorio la consumen para listar y mutar registros sin conocer el esquema.

    Attributes:
        clave: Identificador corto y estable de la tabla (p. ej. ``eventos``).
        etiqueta: Nombre legible de la sub-pestaña (p. ej. ``Eventos``).
        tabla: Nombre físico de la tabla en la base de datos.
        alias: Alias SQL de la tabla base empleado en las expresiones.
        columna_id: Nombre de la columna clave primaria.
        columna_vigencia: Expresión SQL que devuelve la vigencia del registro.
        columnas: Columnas visibles, en el orden en que se muestran.
        desde: Clausura ``FROM`` con las uniones necesarias para las columnas.
        orden: Clausura ``ORDER BY`` con la que se listan los registros.
    """

    clave: str
    etiqueta: str
    tabla: str
    alias: str
    columna_id: str
    columna_vigencia: str
    columnas: tuple[ColumnaTabla, ...]
    desde: str
    orden: str


@dataclass(frozen=True)
class RegistroInfo:
    """Fila genérica de una tabla de corrección.

    Attributes:
        id_registro: Valor de la clave primaria de la fila.
        id_vigencia: Vigencia de la fila (activa o anulada).
        datos: Mapa ``etiqueta de columna -> valor`` con lo que se muestra.
    """

    id_registro: int
    id_vigencia: int
    datos: dict[str, object]

    @property
    def estado(self) -> str:
        """Etiqueta legible de la vigencia (``Vigente`` o ``Inactivo``)."""
        if self.id_vigencia == VIGENCIA_ACTIVA:
            return ESTADO_VIGENTE_TEXTO
        return ESTADO_ANULADO_TEXTO


_NOMBRE_OPERADOR = "COALESCE(p.nombres, '') || ' ' || COALESCE(p.primer_apellido, '')"
"""Expresión SQL del nombre completo del operador en las tablas de corrección."""

TABLAS_CORRECCION: tuple[DefinicionTabla, ...] = (
    DefinicionTabla(
        clave="eventos",
        etiqueta="Eventos",
        tabla="fact_eventos_operador",
        alias="e",
        columna_id="id_hecho_evento",
        columna_vigencia="e.id_vigencia",
        columnas=(
            ColumnaTabla("Código", "e.id_codigo"),
            ColumnaTabla("Cédula", "c.id_persona"),
            ColumnaTabla("Nombre", _NOMBRE_OPERADOR),
            ColumnaTabla("Evento", "te.nombre_evento"),
            ColumnaTabla("Fecha", "e.fecha_registro"),
        ),
        desde=(
            "FROM fact_eventos_operador AS e "
            "JOIN dim_codigo AS c ON e.id_codigo = c.id_codigo "
            "JOIN dim_persona AS p ON c.id_persona = p.id_persona "
            "JOIN dim_tipo_evento AS te ON e.id_tipo_evento = te.id_tipo_evento"
        ),
        orden="e.fecha_registro DESC",
    ),
    DefinicionTabla(
        clave="licencias",
        etiqueta="Licencias",
        tabla="fact_licencias",
        alias="l",
        columna_id="id_hecho_licencia",
        columna_vigencia="l.id_vigencia",
        columnas=(
            ColumnaTabla("Código", "l.id_codigo"),
            ColumnaTabla("Cédula", "c.id_persona"),
            ColumnaTabla("Nombre", _NOMBRE_OPERADOR),
            ColumnaTabla("Tipo", "l.tipo"),
            ColumnaTabla("Vencimiento", "l.vencimiento"),
        ),
        desde=(
            "FROM fact_licencias AS l "
            "LEFT JOIN dim_codigo AS c ON l.id_codigo = c.id_codigo "
            "LEFT JOIN dim_persona AS p ON c.id_persona = p.id_persona"
        ),
        orden="l.id_hecho_licencia DESC",
    ),
    DefinicionTabla(
        clave="comportamientos",
        etiqueta="Comportamientos",
        tabla="fact_comportamiento",
        alias="fc",
        columna_id="id_hecho_comportamiento",
        columna_vigencia="fc.id_vigencia",
        columnas=(
            ColumnaTabla("Código", "fc.id_codigo"),
            ColumnaTabla("Cédula", "c.id_persona"),
            ColumnaTabla("Nombre", _NOMBRE_OPERADOR),
            ColumnaTabla("Fuente", "fc.fuente"),
            ColumnaTabla("Descripción", "fc.descripcion_comportamiento"),
            ColumnaTabla("Fecha evento", "fc.fecha_evento"),
        ),
        desde=(
            "FROM fact_comportamiento AS fc "
            "LEFT JOIN dim_codigo AS c ON fc.id_codigo = c.id_codigo "
            "LEFT JOIN dim_persona AS p ON c.id_persona = p.id_persona"
        ),
        orden="fc.fecha_registro DESC",
    ),
    DefinicionTabla(
        clave="operadores",
        etiqueta="Operadores",
        tabla="dim_persona",
        alias="p",
        columna_id="id_persona",
        columna_vigencia="p.id_vigencia",
        columnas=(
            ColumnaTabla("Cédula", "p.id_persona"),
            ColumnaTabla("Nombres", "p.nombres"),
            ColumnaTabla("Primer apellido", "p.primer_apellido"),
            ColumnaTabla("Segundo apellido", "p.segundo_apellido"),
            ColumnaTabla("Género", "p.genero"),
        ),
        desde="FROM dim_persona AS p",
        orden="p.id_persona",
    ),
)
"""Catálogo declarativo de las tablas que soporta la corrección de registros."""


# --- Fragmentos SQL (parámetros enlazados, sin concatenar datos) -------------
_COLUMNAS_EVENTO = """
    e.id_hecho_evento, e.id_codigo, c.id_persona AS cedula,
    COALESCE(p.nombres, '') || ' ' || COALESCE(p.primer_apellido, '') AS nombre,
    te.nombre_evento, e.fecha_registro AS fecha, e.id_vigencia
"""

_FROM_EVENTO = """
    FROM fact_eventos_operador AS e
    JOIN dim_codigo AS c ON e.id_codigo = c.id_codigo
    JOIN dim_persona AS p ON c.id_persona = p.id_persona
    JOIN dim_tipo_evento AS te ON e.id_tipo_evento = te.id_tipo_evento
"""

_SQL_TIPOS_EVENTO = text(
    "SELECT id_tipo_evento, nombre_evento FROM dim_tipo_evento ORDER BY id_tipo_evento"
)

_SQL_LOTES = text(
    f"""
    SELECT strftime('{FORMATO_LOTE}', fecha_registro) AS lote, COUNT(*) AS total
    FROM fact_eventos_operador
    GROUP BY lote
    ORDER BY lote DESC
    """
)

_SQL_ACTUALIZAR_VIGENCIA = text(
    "UPDATE fact_eventos_operador SET id_vigencia = :vigencia WHERE id_hecho_evento IN :ids"
).bindparams(bindparam("ids", expanding=True))

_SQL_ELIMINAR_REGISTROS = text(
    "DELETE FROM fact_eventos_operador WHERE id_hecho_evento IN :ids"
).bindparams(bindparam("ids", expanding=True))

_SQL_ACTUALIZAR_VIGENCIA_LOTE = text(
    f"UPDATE fact_eventos_operador SET id_vigencia = :vigencia "
    f"WHERE strftime('{FORMATO_LOTE}', fecha_registro) = :lote"
)

_SQL_ELIMINAR_LOTE = text(
    f"DELETE FROM fact_eventos_operador WHERE strftime('{FORMATO_LOTE}', fecha_registro) = :lote"
)

_SQL_AUDITORIA = text(
    "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:usuario, :accion, :detalles)"
)


def _mapear_evento(fila: RowMapping) -> EventoInfo:
    """Mapea una fila de eventos al DTO de dominio.

    Args:
        fila: Fila devuelta por SQLAlchemy.

    Returns:
        El :class:`EventoInfo` construido a partir de la fila.
    """
    return EventoInfo(
        id_hecho_evento=int(fila["id_hecho_evento"]),
        id_codigo=int(fila["id_codigo"]),
        cedula=int(fila["cedula"]),
        nombre=str(fila["nombre"] or "").strip(),
        nombre_evento=str(fila["nombre_evento"]),
        fecha=str(fila["fecha"] or ""),
        id_vigencia=int(fila["id_vigencia"]),
    )


def _condiciones_y_parametros(filtro: FiltroEventos) -> tuple[list[str], dict[str, object]]:
    """Traduce un filtro a las condiciones SQL y sus parámetros enlazados.

    Args:
        filtro: Criterios de búsqueda.

    Returns:
        La lista de condiciones ``WHERE`` y el diccionario de parámetros.
    """
    condiciones: list[str] = []
    parametros: dict[str, object] = {}
    if filtro.codigo is not None:
        condiciones.append("e.id_codigo = :codigo")
        parametros["codigo"] = filtro.codigo
    if filtro.cedula is not None:
        condiciones.append("c.id_persona = :cedula")
        parametros["cedula"] = filtro.cedula
    if filtro.id_tipo_evento is not None:
        condiciones.append("e.id_tipo_evento = :id_tipo_evento")
        parametros["id_tipo_evento"] = filtro.id_tipo_evento
    if filtro.vigencia is not None:
        condiciones.append("e.id_vigencia = :vigencia")
        parametros["vigencia"] = filtro.vigencia
    if filtro.fecha_desde is not None:
        condiciones.append("date(e.fecha_registro) >= :fecha_desde")
        parametros["fecha_desde"] = filtro.fecha_desde.isoformat()
    if filtro.fecha_hasta is not None:
        condiciones.append("date(e.fecha_registro) <= :fecha_hasta")
        parametros["fecha_hasta"] = filtro.fecha_hasta.isoformat()
    return condiciones, parametros


def _definicion(clave: str) -> DefinicionTabla:
    """Busca en el catálogo la definición de una tabla de corrección.

    Args:
        clave: Identificador corto de la tabla (p. ej. ``eventos``).

    Returns:
        La definición de la tabla solicitada.

    Raises:
        ValueError: Si la clave no corresponde a ninguna tabla soportada.
    """
    for definicion in TABLAS_CORRECCION:
        if definicion.clave == clave:
            return definicion
    raise ValueError(f"Tabla de corrección desconocida: {clave}")


def _sql_listar(definicion: DefinicionTabla) -> TextClause:
    """Construye la consulta que lista los registros de una tabla.

    Las columnas visibles se aliasan por posición (``col_0``, ``col_1``…) para
    mapearlas después a sus etiquetas, evitando colisiones entre tablas.

    Args:
        definicion: Metadatos de la tabla a listar.

    Returns:
        La sentencia parametrizada con ``:limite``.
    """
    columnas = ", ".join(
        f"{columna.expresion} AS col_{indice}" for indice, columna in enumerate(definicion.columnas)
    )
    return text(
        f"SELECT {definicion.alias}.{definicion.columna_id} AS id_registro, "
        f"{definicion.columna_vigencia} AS id_vigencia, {columnas} "
        f"{definicion.desde} ORDER BY {definicion.orden} LIMIT :limite"
    )


def _sql_cambiar_vigencia(definicion: DefinicionTabla) -> TextClause:
    """Construye la sentencia que cambia la vigencia de una tabla por IDs.

    Args:
        definicion: Metadatos de la tabla a modificar.

    Returns:
        La sentencia parametrizada con ``:vigencia`` y ``:ids`` (expansible).
    """
    return text(
        f"UPDATE {definicion.tabla} SET id_vigencia = :vigencia "
        f"WHERE {definicion.columna_id} IN :ids"
    ).bindparams(bindparam("ids", expanding=True))


def _sql_eliminar_tabla(definicion: DefinicionTabla) -> TextClause:
    """Construye la sentencia que elimina registros de una tabla por IDs.

    Args:
        definicion: Metadatos de la tabla a modificar.

    Returns:
        La sentencia parametrizada con ``:ids`` (expansible).
    """
    return text(f"DELETE FROM {definicion.tabla} WHERE {definicion.columna_id} IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )


def _mapear_registro(definicion: DefinicionTabla, fila: RowMapping) -> RegistroInfo:
    """Mapea una fila genérica al DTO de corrección.

    Args:
        definicion: Metadatos de la tabla consultada.
        fila: Fila devuelta por SQLAlchemy.

    Returns:
        El :class:`RegistroInfo` con la vigencia y los valores por etiqueta.
    """
    datos = {
        columna.etiqueta: fila[f"col_{indice}"]
        for indice, columna in enumerate(definicion.columnas)
    }
    vigencia = fila["id_vigencia"]
    return RegistroInfo(
        id_registro=int(fila["id_registro"]),
        id_vigencia=int(vigencia) if vigencia is not None else VIGENCIA_ACTIVA,
        datos=datos,
    )


class EventosRepository:
    """Repositorio de eventos de operadores sobre la base de datos.

    Concentra toda la ejecución de SQLAlchemy de la corrección de registros. El
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
        """Lista los tipos de evento disponibles para filtrar.

        Returns:
            Los tipos de evento ordenados por identificador.
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

    def buscar_eventos(self, filtro: FiltroEventos | None = None) -> list[EventoInfo]:
        """Busca eventos aplicando los filtros indicados.

        Args:
            filtro: Criterios de búsqueda. Si es ``None`` se listan los últimos
                eventos hasta :data:`LIMITE_POR_DEFECTO`.

        Returns:
            La lista de :class:`EventoInfo` del más reciente al más antiguo.
        """
        filtro = filtro or FiltroEventos()
        condiciones, parametros = _condiciones_y_parametros(filtro)
        where = " AND ".join(condiciones) if condiciones else "1 = 1"
        sentencia = text(
            f"SELECT {_COLUMNAS_EVENTO} {_FROM_EVENTO} "
            f"WHERE {where} ORDER BY e.fecha_registro DESC LIMIT :limite"
        )
        parametros["limite"] = filtro.limite
        with self.motor.connect() as conexion:
            filas = conexion.execute(sentencia, parametros).mappings().all()
        return [_mapear_evento(fila) for fila in filas]

    def listar_lotes(self) -> list[LoteInfo]:
        """Lista los lotes de eventos agrupados por minuto de cargue.

        Returns:
            Los lotes del más reciente al más antiguo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LOTES).mappings().all()
        return [LoteInfo(lote=str(fila["lote"]), total=int(fila["total"])) for fila in filas]

    def listar_eventos_de_lote(self, lote: str) -> list[EventoInfo]:
        """Lista los eventos que pertenecen a un lote (minuto de cargue).

        Args:
            lote: Marca temporal ``YYYY-MM-DD HH:MM`` del lote.

        Returns:
            Los eventos del lote ordenados por identificador.
        """
        sentencia = text(
            f"SELECT {_COLUMNAS_EVENTO} {_FROM_EVENTO} "
            f"WHERE strftime('{FORMATO_LOTE}', e.fecha_registro) = :lote "
            f"ORDER BY e.id_hecho_evento"
        )
        with self.motor.connect() as conexion:
            filas = conexion.execute(sentencia, {"lote": lote}).mappings().all()
        return [_mapear_evento(fila) for fila in filas]

    def reactivar_registros(self, ids: list[int], usuario: str) -> int:
        """Reactiva los eventos indicados y registra la auditoría.

        Args:
            ids: Identificadores de los eventos a reactivar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados.
        """
        return self._cambiar_vigencia(ids, VIGENCIA_ACTIVA, ACCION_REACTIVAR_REGISTROS, usuario)

    def anular_registros(self, ids: list[int], usuario: str) -> int:
        """Anula los eventos indicados y registra la auditoría.

        Args:
            ids: Identificadores de los eventos a anular.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados.
        """
        return self._cambiar_vigencia(ids, VIGENCIA_ANULADA, ACCION_ANULAR_REGISTROS, usuario)

    def eliminar_registros(self, ids: list[int], usuario: str) -> int:
        """Elimina físicamente los eventos indicados y registra la auditoría.

        Args:
            ids: Identificadores de los eventos a eliminar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros eliminados.
        """
        lista = self._normalizar_ids(ids)
        if not lista:
            return 0
        detalles = f"IDs: {','.join(str(identificador) for identificador in lista)}"
        with self.motor.begin() as conexion:
            filas = int(conexion.execute(_SQL_ELIMINAR_REGISTROS, {"ids": lista}).rowcount)
            self._auditar(conexion, usuario, ACCION_ELIMINAR_REGISTROS, detalles)
        return filas

    def reactivar_lote(self, lote: str, usuario: str) -> int:
        """Reactiva todos los eventos de un lote y registra la auditoría.

        Args:
            lote: Marca temporal ``YYYY-MM-DD HH:MM`` del lote.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados.
        """
        return self._cambiar_vigencia_lote(lote, VIGENCIA_ACTIVA, ACCION_REACTIVAR_LOTE, usuario)

    def anular_lote(self, lote: str, usuario: str) -> int:
        """Anula todos los eventos de un lote y registra la auditoría.

        Args:
            lote: Marca temporal ``YYYY-MM-DD HH:MM`` del lote.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados.
        """
        return self._cambiar_vigencia_lote(lote, VIGENCIA_ANULADA, ACCION_ANULAR_LOTE, usuario)

    def eliminar_lote(self, lote: str, usuario: str) -> int:
        """Elimina físicamente todos los eventos de un lote y audita la acción.

        Args:
            lote: Marca temporal ``YYYY-MM-DD HH:MM`` del lote.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros eliminados.
        """
        with self.motor.begin() as conexion:
            filas = int(conexion.execute(_SQL_ELIMINAR_LOTE, {"lote": lote}).rowcount)
            self._auditar(conexion, usuario, ACCION_ELIMINAR_LOTE, f"Lote:{lote}")
        return filas

    def registrar_auditoria(self, usuario: str, accion: str, detalles: str) -> None:
        """Registra una acción en el log de auditoría.

        Args:
            usuario: Usuario que ejecuta la acción.
            accion: Nombre de la acción realizada.
            detalles: Detalle libre de la acción.
        """
        with self.motor.begin() as conexion:
            self._auditar(conexion, usuario, accion, detalles)

    def listar_registros(self, clave: str, limite: int = LIMITE_POR_DEFECTO) -> list[RegistroInfo]:
        """Lista, de forma compacta, los registros de una tabla soportada.

        Args:
            clave: Identificador corto de la tabla (``eventos``, ``licencias``,
                ``comportamientos`` u ``operadores``).
            limite: Número máximo de filas a devolver.

        Returns:
            Las filas de la tabla, en el orden definido por su catálogo.

        Raises:
            ValueError: Si la clave no corresponde a una tabla soportada.
        """
        definicion = _definicion(clave)
        with self.motor.connect() as conexion:
            filas = conexion.execute(_sql_listar(definicion), {"limite": limite}).mappings().all()
        return [_mapear_registro(definicion, fila) for fila in filas]

    def mutar_vigencia(self, clave: str, ids: list[int], vigencia: int, usuario: str) -> int:
        """Cambia la vigencia de los registros indicados y audita la acción.

        Args:
            clave: Identificador corto de la tabla a modificar.
            ids: Identificadores de los registros a modificar.
            vigencia: Vigencia destino (activa o anulada).
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados; ``0`` si la lista está vacía.

        Raises:
            ValueError: Si la clave no corresponde a una tabla soportada.
        """
        definicion = _definicion(clave)
        lista = self._normalizar_ids(ids)
        if not lista:
            return 0
        if vigencia == VIGENCIA_ACTIVA:
            accion = f"{ACCION_REACTIVAR_TABLA} {definicion.etiqueta}"
        else:
            accion = f"{ACCION_ANULAR_TABLA} {definicion.etiqueta}"
        detalles = f"IDs: {','.join(str(identificador) for identificador in lista)}"
        with self.motor.begin() as conexion:
            filas = int(
                conexion.execute(
                    _sql_cambiar_vigencia(definicion),
                    {"vigencia": vigencia, "ids": lista},
                ).rowcount
            )
            self._auditar(conexion, usuario, accion, detalles)
        return filas

    def eliminar_registros_tabla(self, clave: str, ids: list[int], usuario: str) -> int:
        """Elimina físicamente los registros indicados y audita la acción.

        Args:
            clave: Identificador corto de la tabla a modificar.
            ids: Identificadores de los registros a eliminar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros eliminados; ``0`` si la lista está vacía.

        Raises:
            ValueError: Si la clave no corresponde a una tabla soportada.
        """
        definicion = _definicion(clave)
        lista = self._normalizar_ids(ids)
        if not lista:
            return 0
        accion = f"{ACCION_ELIMINAR_TABLA} {definicion.etiqueta}"
        detalles = f"IDs: {','.join(str(identificador) for identificador in lista)}"
        with self.motor.begin() as conexion:
            filas = int(conexion.execute(_sql_eliminar_tabla(definicion), {"ids": lista}).rowcount)
            self._auditar(conexion, usuario, accion, detalles)
        return filas

    def _cambiar_vigencia(self, ids: list[int], vigencia: int, accion: str, usuario: str) -> int:
        """Cambia la vigencia de registros individuales y audita la acción.

        Args:
            ids: Identificadores de los eventos a modificar.
            vigencia: Vigencia destino (activa o anulada).
            accion: Acción de auditoría a registrar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados; ``0`` si la lista está vacía.
        """
        lista = self._normalizar_ids(ids)
        if not lista:
            return 0
        detalles = f"IDs: {','.join(str(identificador) for identificador in lista)}"
        with self.motor.begin() as conexion:
            filas = int(
                conexion.execute(
                    _SQL_ACTUALIZAR_VIGENCIA, {"vigencia": vigencia, "ids": lista}
                ).rowcount
            )
            self._auditar(conexion, usuario, accion, detalles)
        return filas

    def _cambiar_vigencia_lote(self, lote: str, vigencia: int, accion: str, usuario: str) -> int:
        """Cambia la vigencia de un lote completo y audita la acción.

        Args:
            lote: Marca temporal ``YYYY-MM-DD HH:MM`` del lote.
            vigencia: Vigencia destino (activa o anulada).
            accion: Acción de auditoría a registrar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros afectados.
        """
        with self.motor.begin() as conexion:
            filas = int(
                conexion.execute(
                    _SQL_ACTUALIZAR_VIGENCIA_LOTE, {"vigencia": vigencia, "lote": lote}
                ).rowcount
            )
            self._auditar(conexion, usuario, accion, f"Lote:{lote}")
        return filas

    @staticmethod
    def _normalizar_ids(ids: list[int]) -> list[int]:
        """Convierte los identificadores a enteros, descartando los inválidos.

        Args:
            ids: Identificadores recibidos.

        Returns:
            La lista de identificadores enteros.
        """
        lista: list[int] = []
        for identificador in ids:
            try:
                lista.append(int(identificador))
            except (TypeError, ValueError):
                continue
        return lista

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
    "ACCION_ANULAR_LOTE",
    "ACCION_ANULAR_REGISTROS",
    "ACCION_ANULAR_TABLA",
    "ACCION_ELIMINAR_LOTE",
    "ACCION_ELIMINAR_REGISTROS",
    "ACCION_ELIMINAR_TABLA",
    "ACCION_REACTIVAR_LOTE",
    "ACCION_REACTIVAR_REGISTROS",
    "ACCION_REACTIVAR_TABLA",
    "ESTADO_ANULADO_TEXTO",
    "ESTADO_VIGENTE_TEXTO",
    "FORMATO_LOTE",
    "LIMITE_POR_DEFECTO",
    "TABLAS_CORRECCION",
    "ColumnaTabla",
    "DefinicionTabla",
    "EventoInfo",
    "EventosRepository",
    "FiltroEventos",
    "LoteInfo",
    "RegistroInfo",
    "TipoEventoInfo",
]
