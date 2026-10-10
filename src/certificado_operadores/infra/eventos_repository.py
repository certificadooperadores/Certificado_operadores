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

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, cast

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

ACCION_EDITAR_TABLA = "Editar"
"""Prefijo de auditoría al editar registros de una tabla de corrección (spec 017)."""

ETIQUETA_ESTADO = "Estado"
"""Encabezado de la columna de vigencia en el editor tipo Excel."""

ETIQUETA_EVENTO = "Evento"
"""Encabezado legible de la columna del tipo de evento (spec 020)."""

CLAVE_TABLA_EVENTOS = "eventos"
"""Clave del catálogo de la tabla de eventos dentro de ``TABLAS_CORRECCION``."""

TABLA_PERSONA = "dim_persona"
"""Nombre físico de la dimensión de personas (operadores) en la base de datos."""

OPCION_VIGENTE = "vigente"
"""Opción de la lista desplegable de estado equivalente a la vigencia activa."""

OPCION_ANULADO = "anulado"
"""Opción de la lista desplegable de estado equivalente a la vigencia anulada."""

OPCIONES_ESTADO: tuple[str, ...] = (OPCION_VIGENTE, OPCION_ANULADO)
"""Opciones restringidas de la columna ``Estado`` (spec 017, S-04)."""

GENEROS_VALIDOS: tuple[str, ...] = ("M", "F")
"""Géneros permitidos en la columna ``Género`` (spec 017, S-04)."""

OPCIONES_LICENCIA: tuple[str, ...] = ("C1", "C2", "C3")
"""Categorías oficiales de conducción colombianas de la columna ``Tipo`` (spec 018)."""

TIPO_EDICION_TEXTO = "texto"
"""Tipo de dato editable: texto libre."""

TIPO_EDICION_ENTERO = "entero"
"""Tipo de dato editable: número entero."""

TIPO_EDICION_FECHA = "fecha"
"""Tipo de dato editable: fecha en texto ISO."""

TIPO_EDICION_CODIGO = "codigo"
"""Tipo de dato editable que valida su existencia en ``dim_codigo`` (spec 017, S-02)."""

TIPO_EDICION_VIGENCIA = "vigencia"
"""Tipo de dato editable que restringe los valores a vigente/anulado (spec 017, S-04)."""

TIPO_EDICION_EVENTO = "evento"
"""Tipo de dato editable restringido a los tipos de evento de ``dim_tipo_evento``."""

TIPO_EDICION_GENERO = "genero"
"""Tipo de dato editable restringido a ``M``/``F`` (spec 017, S-04)."""

TIPO_EDICION_LICENCIA = "licencia"
"""Tipo de dato editable restringido a las licencias oficiales ``C1``/``C2``/``C3`` (spec 018)."""

TIPO_EDICION_FUENTE = "fuente"
"""Tipo de dato editable restringido a las fuentes de ``dim_detalle_comportamiento`` (spec 018)."""

TIPO_EDICION_DESCRIPCION = "descripcion"
"""Tipo editable restringido a las descripciones del catálogo (spec 018)."""

# --- Spec 020: compatibilidad de campos por categoría de evento --------------
TIPO_EVENTO_CERTIFICACION = 1
"""Identificador del evento de certificación inicial (acreditación)."""

TIPO_EVENTO_REACTIVACION = 2
"""Identificador del evento de reactivación del certificado (acreditación)."""

TIPO_EVENTO_RENOVACION = 3
"""Identificador del evento de renovación del certificado (acreditación)."""

TIPO_EVENTO_OBSERVACION = 4
"""Identificador del evento de bitácora simple (solo código, tipo y observación)."""

TIPO_EVENTO_RESTRICCION_MEDICA = 5
"""Identificador del evento de restricción médica (salud ocupacional)."""

TIPO_EVENTO_SUSPENSION = 6
"""Identificador del evento de suspensión (medida temporal)."""

TIPO_EVENTO_CANCELACION = 7
"""Identificador del evento de cancelación o desvinculación (novedad de retiro)."""

CAMPOS_EVENTO_EDITABLES: frozenset[str] = frozenset(
    {
        "id_codigo",
        "id_tipo_evento",
        "fecha_certificado",
        "fecha_retiro",
        "fecha_notificacion_retiro",
        "fecha_suspension",
        "fecha_prueba",
        "evaluador",
        "id_vehiculo_evaluado",
        "observacion",
    }
)
"""Universo de columnas editables de negocio de ``fact_eventos_operador`` (spec 020)."""

_CAMPOS_EVENTO_BASE: frozenset[str] = frozenset({"id_codigo", "id_tipo_evento", "observacion"})
"""Campos comunes a toda categoría: llaves y bitácora textual."""

_CAMPOS_EVENTO_ACREDITACION: frozenset[str] = _CAMPOS_EVENTO_BASE | {
    "fecha_certificado",
    "fecha_prueba",
    "evaluador",
    "id_vehiculo_evaluado",
}
"""Campos de acreditación/habilitación: certificado, prueba, evaluador y vehículo."""

CAMPOS_PERMITIDOS_POR_EVENTO: dict[int, frozenset[str]] = {
    TIPO_EVENTO_CERTIFICACION: _CAMPOS_EVENTO_ACREDITACION,
    TIPO_EVENTO_REACTIVACION: _CAMPOS_EVENTO_ACREDITACION,
    TIPO_EVENTO_RENOVACION: _CAMPOS_EVENTO_ACREDITACION,
    TIPO_EVENTO_CANCELACION: _CAMPOS_EVENTO_BASE
    | {
        "fecha_retiro",
        "fecha_notificacion_retiro",
    },
    TIPO_EVENTO_SUSPENSION: _CAMPOS_EVENTO_BASE | {"fecha_suspension"},
    TIPO_EVENTO_RESTRICCION_MEDICA: _CAMPOS_EVENTO_BASE,
    TIPO_EVENTO_OBSERVACION: _CAMPOS_EVENTO_BASE,
}
"""Matriz de compatibilidad ``id_tipo_evento -> columnas editables permitidas`` (spec 020, S-01)."""

CAMPOS_EVENTO_POR_DEFECTO: frozenset[str] = _CAMPOS_EVENTO_BASE
"""Conjunto aplicado a categorías no listadas en la matriz (política restrictiva, spec 020)."""

CAMPOS_FECHA_EVENTO: frozenset[str] = frozenset(
    {
        "fecha_certificado",
        "fecha_retiro",
        "fecha_notificacion_retiro",
        "fecha_suspension",
        "fecha_prueba",
    }
)
"""Columnas de fecha de evento sujetas a validación de plausibilidad (spec 020, S-04)."""

_PATRON_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
"""Patrón que exige el formato de fecha ``AAAA-MM-DD`` antes de interpretarla."""

MENSAJE_DEPENDENCIAS = (
    "No se puede eliminar: el registro tiene {eventos} eventos y "
    "{comportamientos} comportamientos dependientes. Debe anularlo o "
    "depurar los registros hijos primero."
)
"""Mensaje explícito que aborta la eliminación de un registro con hijos (spec 017, S-01)."""

MENSAJE_CODIGO_INEXISTENTE = (
    "El código {codigo} no existe en el catálogo de códigos; la edición fue cancelada."
)
"""Mensaje de error al reasignar un código inexistente (spec 017, S-02)."""

MENSAJE_COLUMNA_PROTEGIDA = "La columna «{etiqueta}» es de solo lectura y no puede modificarse."
"""Mensaje de error al intentar editar una columna protegida (spec 017, S-03)."""

MENSAJE_VALOR_INVALIDO = "El valor «{valor}» no es válido para la columna «{etiqueta}»."
"""Mensaje de error ante un valor fuera del catálogo permitido (spec 017, S-04)."""

MENSAJE_CAMPO_INCOMPATIBLE = (
    "El evento de tipo «{nombre_evento}» no admite la columna «{etiqueta}»."
)
"""Mensaje de rechazo de un campo prohibido para la categoría del evento (spec 020, S-02)."""

MENSAJE_FECHA_INVALIDA = (
    "La fecha «{valor}» de la columna «{etiqueta}» no tiene el formato AAAA-MM-DD."
)
"""Mensaje de rechazo de una fecha con formato inválido (spec 020, S-04)."""

MENSAJE_FECHA_FUTURA = (
    "La fecha «{valor}» de la columna «{etiqueta}» no puede ser posterior a {limite}."
)
"""Mensaje de rechazo de una fecha futura inverosímil (spec 020, S-04)."""


class DependenciaRegistroError(ValueError):
    """Error de integridad referencial: el registro tiene hijos dependientes (spec 017, S-01)."""


class CodigoInexistenteError(ValueError):
    """Error de reasignación: el código indicado no existe en ``dim_codigo`` (spec 017, S-02)."""


class ColumnaProtegidaError(ValueError):
    """Error de edición: se intentó modificar una columna de solo lectura (spec 017, S-03)."""


class ValorInvalidoError(ValueError):
    """Error de edición: el valor está fuera del catálogo permitido (spec 017, S-04)."""


class CampoIncompatibleError(ValueError):
    """Error de edición: el campo no aplica a la categoría del evento (spec 020, S-02)."""


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
class ColumnaEditable:
    """Columna editable de una tabla de corrección (editor tipo Excel, spec 017).

    Attributes:
        etiqueta: Encabezado legible que comparte con la columna visible.
        columna: Nombre físico de la columna en la tabla de la base de datos.
        tipo: Tipo de edición (texto, entero, fecha, código, vigencia, evento o género).
    """

    etiqueta: str
    columna: str
    tipo: str


@dataclass(frozen=True)
class CambioRegistro:
    """Cambio solicitado sobre una celda de una tabla de corrección.

    Attributes:
        id_registro: Valor de la clave primaria de la fila a modificar.
        etiqueta: Encabezado legible de la columna editada.
        valor: Valor nuevo propuesto para la celda.
    """

    id_registro: int
    etiqueta: str
    valor: object


@dataclass(frozen=True)
class DefinicionTabla:
    """Metadatos de una tabla soportada por la corrección de registros.

    Concentra, como configuración declarativa, el nombre de la tabla, su clave
    primaria, la columna de vigencia y las columnas visibles y editables. La UI y
    el repositorio la consumen para listar y mutar registros sin conocer el esquema.

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
        editables: Columnas que el editor permite modificar (spec 017).
        protege_dependencias: Si es ``True``, la eliminación se bloquea cuando el
            registro tiene hijos dependientes (spec 017, S-01).
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
    editables: tuple[ColumnaEditable, ...] = ()
    protege_dependencias: bool = False


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
            ColumnaTabla("Fecha Certificado", "e.fecha_certificado"),
            ColumnaTabla("Fecha Retiro", "e.fecha_retiro"),
            ColumnaTabla("Fecha Notif. Retiro", "e.fecha_notificacion_retiro"),
            ColumnaTabla("Fecha Suspensión", "e.fecha_suspension"),
            ColumnaTabla("Fecha Prueba", "e.fecha_prueba"),
            ColumnaTabla("Evaluador", "e.evaluador"),
            ColumnaTabla("Vehículo Evaluado", "e.id_vehiculo_evaluado"),
            ColumnaTabla("Observación", "e.observacion"),
            ColumnaTabla("Registro", "e.fecha_registro"),
        ),
        desde=(
            "FROM fact_eventos_operador AS e "
            "JOIN dim_codigo AS c ON e.id_codigo = c.id_codigo "
            "JOIN dim_persona AS p ON c.id_persona = p.id_persona "
            "JOIN dim_tipo_evento AS te ON e.id_tipo_evento = te.id_tipo_evento"
        ),
        orden="e.fecha_registro DESC",
        editables=(
            ColumnaEditable("Código", "id_codigo", TIPO_EDICION_CODIGO),
            ColumnaEditable("Evento", "id_tipo_evento", TIPO_EDICION_EVENTO),
            ColumnaEditable("Fecha Certificado", "fecha_certificado", TIPO_EDICION_FECHA),
            ColumnaEditable("Fecha Retiro", "fecha_retiro", TIPO_EDICION_FECHA),
            ColumnaEditable("Fecha Notif. Retiro", "fecha_notificacion_retiro", TIPO_EDICION_FECHA),
            ColumnaEditable("Fecha Suspensión", "fecha_suspension", TIPO_EDICION_FECHA),
            ColumnaEditable("Fecha Prueba", "fecha_prueba", TIPO_EDICION_FECHA),
            ColumnaEditable("Evaluador", "evaluador", TIPO_EDICION_TEXTO),
            ColumnaEditable("Vehículo Evaluado", "id_vehiculo_evaluado", TIPO_EDICION_ENTERO),
            ColumnaEditable("Observación", "observacion", TIPO_EDICION_TEXTO),
        ),
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
        editables=(
            ColumnaEditable("Código", "id_codigo", TIPO_EDICION_CODIGO),
            ColumnaEditable("Tipo", "tipo", TIPO_EDICION_LICENCIA),
            ColumnaEditable("Vencimiento", "vencimiento", TIPO_EDICION_FECHA),
        ),
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
        editables=(
            ColumnaEditable("Código", "id_codigo", TIPO_EDICION_CODIGO),
            ColumnaEditable("Fuente", "fuente", TIPO_EDICION_FUENTE),
            ColumnaEditable("Descripción", "descripcion_comportamiento", TIPO_EDICION_DESCRIPCION),
            ColumnaEditable("Fecha evento", "fecha_evento", TIPO_EDICION_FECHA),
        ),
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
        editables=(
            ColumnaEditable("Nombres", "nombres", TIPO_EDICION_TEXTO),
            ColumnaEditable("Primer apellido", "primer_apellido", TIPO_EDICION_TEXTO),
            ColumnaEditable("Segundo apellido", "segundo_apellido", TIPO_EDICION_TEXTO),
            ColumnaEditable("Género", "genero", TIPO_EDICION_GENERO),
        ),
        protege_dependencias=True,
    ),
    DefinicionTabla(
        clave="codigos",
        etiqueta="Códigos",
        tabla="dim_codigo",
        alias="c",
        columna_id="id_codigo",
        columna_vigencia="c.id_vigencia",
        columnas=(
            ColumnaTabla("Código", "c.id_codigo"),
            ColumnaTabla("Cédula", "p.id_persona"),
            ColumnaTabla("Nombre", _NOMBRE_OPERADOR),
            ColumnaTabla("Empresa", "e.nombre_empresa"),
            ColumnaTabla("Desde", "c.fecha_registro"),
        ),
        desde=(
            "FROM dim_codigo AS c "
            "JOIN dim_persona AS p ON c.id_persona = p.id_persona "
            "LEFT JOIN dim_empresa AS e ON c.id_empresa = e.id_empresa"
        ),
        orden="c.id_codigo",
        editables=(),
        protege_dependencias=True,
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

# --- Spec 017: integridad referencial y edición segura ----------------------
_SQL_CODIGOS_DE_PERSONA = text("SELECT id_codigo FROM dim_codigo WHERE id_persona = :id_persona")

_SQL_CODIGO_EXISTE = text("SELECT 1 FROM dim_codigo WHERE id_codigo = :id_codigo LIMIT 1")

# --- Spec 018: catálogos oficiales de las listas desplegables ----------------
_SQL_FUENTES_COMPORTAMIENTO = text(
    "SELECT DISTINCT fuente FROM dim_detalle_comportamiento "
    "WHERE fuente IS NOT NULL AND TRIM(fuente) <> '' ORDER BY fuente"
)

_SQL_DESCRIPCIONES_COMPORTAMIENTO = text(
    "SELECT DISTINCT descripcion_comportamiento FROM dim_detalle_comportamiento "
    "WHERE descripcion_comportamiento IS NOT NULL "
    "AND TRIM(descripcion_comportamiento) <> '' "
    "ORDER BY descripcion_comportamiento"
)

_SQL_FUENTE_EXISTE = text("SELECT 1 FROM dim_detalle_comportamiento WHERE fuente = :valor LIMIT 1")

_SQL_DESCRIPCION_EXISTE = text(
    "SELECT 1 FROM dim_detalle_comportamiento WHERE descripcion_comportamiento = :valor LIMIT 1"
)

_SQL_TIPO_EVENTO_POR_NOMBRE = text(
    "SELECT id_tipo_evento FROM dim_tipo_evento WHERE nombre_evento = :nombre LIMIT 1"
)

# --- Spec 020: resolución del tipo de evento de una fila ---------------------
_SQL_TIPO_EVENTO_ACTUAL = text(
    "SELECT id_tipo_evento FROM fact_eventos_operador WHERE id_hecho_evento = :id"
)

_SQL_NOMBRE_TIPO_EVENTO = text(
    "SELECT nombre_evento FROM dim_tipo_evento WHERE id_tipo_evento = :id LIMIT 1"
)

_SQL_CONTEO_DEPENDENCIAS: dict[str, TextClause] = {
    "eventos": text(
        "SELECT COUNT(*) FROM fact_eventos_operador WHERE id_codigo IN :ids"
    ).bindparams(bindparam("ids", expanding=True)),
    "comportamientos": text(
        "SELECT COUNT(*) FROM fact_comportamiento WHERE id_codigo IN :ids"
    ).bindparams(bindparam("ids", expanding=True)),
    "licencias": text("SELECT COUNT(*) FROM fact_licencias WHERE id_codigo IN :ids").bindparams(
        bindparam("ids", expanding=True)
    ),
}


def _sql_actualizar_columna(definicion: DefinicionTabla, columna: str) -> TextClause:
    """Construye la sentencia que actualiza una columna de una fila de la tabla.

    El nombre de la tabla y de la columna provienen del catálogo declarativo (no
    de datos del usuario); el valor viaja como parámetro enlazado.

    Args:
        definicion: Metadatos de la tabla a modificar.
        columna: Nombre físico de la columna a actualizar.

    Returns:
        La sentencia parametrizada con ``:valor`` e ``:id``.
    """
    return text(
        f"UPDATE {definicion.tabla} SET {columna} = :valor WHERE {definicion.columna_id} = :id"
    )


def _columna_editable(definicion: DefinicionTabla, etiqueta: str) -> ColumnaEditable | None:
    """Busca en la definición la columna editable con esa etiqueta.

    Args:
        definicion: Metadatos de la tabla.
        etiqueta: Encabezado legible de la columna.

    Returns:
        La :class:`ColumnaEditable` correspondiente, o ``None`` si la etiqueta no
        es editable (columna protegida o inexistente).
    """
    if etiqueta == ETIQUETA_ESTADO:
        return ColumnaEditable(ETIQUETA_ESTADO, "id_vigencia", TIPO_EDICION_VIGENCIA)
    for columna in definicion.editables:
        if columna.etiqueta == etiqueta:
            return columna
    return None


def campos_permitidos_evento(id_tipo_evento: int) -> frozenset[str]:
    """Devuelve las columnas editables permitidas para una categoría de evento.

    Aplica la matriz :data:`CAMPOS_PERMITIDOS_POR_EVENTO`; para una categoría no
    listada usa el conjunto más restrictivo :data:`CAMPOS_EVENTO_POR_DEFECTO`
    (spec 020, S-01).

    Args:
        id_tipo_evento: Identificador del tipo de evento (``dim_tipo_evento``).

    Returns:
        El conjunto de nombres físicos de columnas editables permitidas.
    """
    return CAMPOS_PERMITIDOS_POR_EVENTO.get(id_tipo_evento, CAMPOS_EVENTO_POR_DEFECTO)


def _valor_vacio(valor: object) -> bool:
    """Indica si el valor de una celda está vacío.

    Se consideran vacíos ``None``, las cadenas en blanco y el ``NaN`` que el
    editor puede entregar para una celda sin dato.

    Args:
        valor: Valor crudo proveniente del editor o de la base de datos.

    Returns:
        ``True`` si el valor no representa un dato asignado.
    """
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip() == ""
    return isinstance(valor, float) and valor != valor


def _validar_fecha_evento(valor: object, etiqueta: str) -> None:
    """Valida el formato y la plausibilidad de una fecha de evento (spec 020, S-04).

    Exige el formato exacto ``AAAA-MM-DD`` y rechaza las fechas posteriores a
    ``date.today() + 1 día``.

    Args:
        valor: Valor nuevo propuesto para la celda de fecha.
        etiqueta: Encabezado legible de la columna (para el mensaje de error).

    Raises:
        ValorInvalidoError: Si el formato es inválido o la fecha es inverosímil.
    """
    texto = str(valor).strip()
    if not _PATRON_FECHA_ISO.match(texto):
        raise ValorInvalidoError(MENSAJE_FECHA_INVALIDA.format(valor=valor, etiqueta=etiqueta))
    try:
        fecha = date.fromisoformat(texto)
    except ValueError as error:
        raise ValorInvalidoError(
            MENSAJE_FECHA_INVALIDA.format(valor=valor, etiqueta=etiqueta)
        ) from error
    limite = date.today() + timedelta(days=1)
    if fecha > limite:
        raise ValorInvalidoError(
            MENSAJE_FECHA_FUTURA.format(valor=valor, etiqueta=etiqueta, limite=limite.isoformat())
        )


def _a_entero(valor: object) -> int:
    """Convierte el valor de una celda a entero, tolerando cadenas y decimales.

    Args:
        valor: Valor crudo proveniente del editor o de la base de datos.

    Returns:
        El valor convertido a ``int``.

    Raises:
        ValorInvalidoError: Si el valor no es convertible a entero.
    """
    try:
        return int(float(str(valor)))
    except (TypeError, ValueError) as error:
        raise ValorInvalidoError(MENSAJE_VALOR_INVALIDO.format(valor=valor, etiqueta="")) from error


def _vigencia_desde_opcion(valor: object) -> int:
    """Traduce el valor de la lista desplegable de estado a la vigencia numérica.

    Args:
        valor: ``vigente``/``anulado`` (texto) o el propio identificador numérico.

    Returns:
        La vigencia equivalente (``VIGENCIA_ACTIVA`` o ``VIGENCIA_ANULADA``).

    Raises:
        ValorInvalidoError: Si el valor no corresponde a una opción permitida.
    """
    if isinstance(valor, int) and valor in (VIGENCIA_ACTIVA, VIGENCIA_ANULADA):
        return valor
    texto = str(valor).strip().lower()
    if texto == OPCION_VIGENTE:
        return VIGENCIA_ACTIVA
    if texto == OPCION_ANULADO:
        return VIGENCIA_ANULADA
    raise ValorInvalidoError(MENSAJE_VALOR_INVALIDO.format(valor=valor, etiqueta=ETIQUETA_ESTADO))


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

    def listar_fuentes_comportamiento(self) -> list[str]:
        """Lista las fuentes oficiales de comportamiento (spec 018).

        Lee las fuentes distintas del catálogo ``dim_detalle_comportamiento``
        para alimentar la lista desplegable de la columna ``Fuente``.

        Returns:
            Las fuentes distintas, ordenadas alfabéticamente y sin vacíos.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_FUENTES_COMPORTAMIENTO).all()
        return [str(fila[0]) for fila in filas]

    def listar_descripciones_comportamiento(self) -> list[str]:
        """Lista las descripciones oficiales de comportamiento (spec 018).

        Lee las descripciones distintas del catálogo
        ``dim_detalle_comportamiento`` para alimentar la lista desplegable de la
        columna ``Descripción``.

        Returns:
            Las descripciones distintas, ordenadas alfabéticamente y sin vacíos.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_DESCRIPCIONES_COMPORTAMIENTO).all()
        return [str(fila[0]) for fila in filas]

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

        Antes de borrar, si la tabla protege dependencias (operadores), comprueba
        que ningún registro tenga eventos, comportamientos o licencias asociados
        y aborta con un mensaje explícito (spec 017, S-01).

        Args:
            clave: Identificador corto de la tabla a modificar.
            ids: Identificadores de los registros a eliminar.
            usuario: Usuario que ejecuta la acción.

        Returns:
            Número de registros eliminados; ``0`` si la lista está vacía.

        Raises:
            ValueError: Si la clave no corresponde a una tabla soportada.
            DependenciaRegistroError: Si algún registro tiene hijos dependientes.
        """
        definicion = _definicion(clave)
        lista = self._normalizar_ids(ids)
        if not lista:
            return 0
        if definicion.protege_dependencias:
            self._verificar_dependencias(definicion, lista)
        accion = f"{ACCION_ELIMINAR_TABLA} {definicion.etiqueta}"
        detalles = f"IDs: {','.join(str(identificador) for identificador in lista)}"
        with self.motor.begin() as conexion:
            filas = int(conexion.execute(_sql_eliminar_tabla(definicion), {"ids": lista}).rowcount)
            self._auditar(conexion, usuario, accion, detalles)
        return filas

    def contar_dependencias_operador(
        self, id_persona: int, id_codigo: int | None = None
    ) -> dict[str, int]:
        """Cuenta los registros hijos asociados a un operador (spec 017, S-01).

        Args:
            id_persona: Documento del operador (``dim_persona.id_persona``).
            id_codigo: Código de operación concreto. Si es ``None`` se cuentan
                todos los códigos del operador.

        Returns:
            Un mapa ``{"eventos": int, "comportamientos": int, "licencias": int}``
            con el total de registros dependientes en cada tabla de hechos.
        """
        with self.motor.connect() as conexion:
            if id_codigo is None:
                filas = conexion.execute(
                    _SQL_CODIGOS_DE_PERSONA, {"id_persona": int(id_persona)}
                ).all()
                codigos = [int(fila[0]) for fila in filas]
            else:
                codigos = [int(id_codigo)]
            if not codigos:
                return dict.fromkeys(_SQL_CONTEO_DEPENDENCIAS, 0)
            return {
                tabla: int(conexion.execute(sentencia, {"ids": codigos}).scalar_one())
                for tabla, sentencia in _SQL_CONTEO_DEPENDENCIAS.items()
            }

    def validar_codigo_existe(self, id_codigo: int) -> bool:
        """Indica si un código de operación existe en ``dim_codigo`` (spec 017, S-02).

        Args:
            id_codigo: Código de operación a validar.

        Returns:
            ``True`` si el código existe; ``False`` en caso contrario.
        """
        with self.motor.connect() as conexion:
            return (
                conexion.execute(_SQL_CODIGO_EXISTE, {"id_codigo": int(id_codigo)}).first()
                is not None
            )

    def actualizar_registros_seguros(
        self, clave: str, cambios: list[CambioRegistro], usuario: str
    ) -> int:
        """Aplica cambios de celdas validando las reglas de seguridad (specs 017 y 020).

        Cada cambio se resuelve y valida dentro de la misma transacción: la
        columna debe ser editable (S-03), los códigos reasignados deben existir en
        ``dim_codigo`` (S-02) y los valores de listas desplegables deben pertenecer
        al catálogo permitido (S-04). Sobre la tabla de eventos, la spec 020 exige
        además que cada campo sea compatible con la categoría del evento
        (S-01/S-02), limpia los campos huérfanos al cambiar el tipo (S-03) y valida
        la plausibilidad de las fechas (S-04). Si cualquier cambio falla, la
        transacción se revierte por completo y no se registra auditoría (S-05).

        Args:
            clave: Identificador corto de la tabla a modificar.
            cambios: Lista de :class:`CambioRegistro` solicitados.
            usuario: Usuario que ejecuta la acción (para auditoría).

        Returns:
            Número de filas afectadas; ``0`` si la lista está vacía.

        Raises:
            ValueError: Si la clave no corresponde a una tabla soportada.
            ColumnaProtegidaError: Si se intenta editar una columna de solo lectura.
            CodigoInexistenteError: Si se reasigna un código inexistente.
            ValorInvalidoError: Si el valor no pertenece al catálogo permitido o la
                fecha es inválida.
            CampoIncompatibleError: Si el campo no aplica a la categoría del evento.
        """
        definicion = _definicion(clave)
        if not cambios:
            return 0
        with self.motor.begin() as conexion:
            if definicion.clave == CLAVE_TABLA_EVENTOS:
                afectados = self._aplicar_cambios_evento(conexion, definicion, cambios)
            else:
                afectados = self._aplicar_cambios_simples(conexion, definicion, cambios)
            detalles = (
                f"IDs: {','.join(str(int(cambio.id_registro)) for cambio in cambios)}; "
                f"Columnas: {','.join(cambio.etiqueta for cambio in cambios)}"
            )
            self._auditar(
                conexion, usuario, f"{ACCION_EDITAR_TABLA} {definicion.etiqueta}", detalles
            )
        return afectados

    def _aplicar_cambios_simples(
        self, conexion: Connection, definicion: DefinicionTabla, cambios: list[CambioRegistro]
    ) -> int:
        """Aplica cambios genéricos de una tabla sin reglas por categoría (spec 017).

        Args:
            conexion: Conexión activa dentro de la transacción.
            definicion: Metadatos de la tabla a modificar.
            cambios: Lista de cambios solicitados.

        Returns:
            Número de filas afectadas.

        Raises:
            ColumnaProtegidaError: Si se intenta editar una columna de solo lectura.
            CodigoInexistenteError: Si se reasigna un código inexistente.
            ValorInvalidoError: Si el valor no pertenece al catálogo permitido.
        """
        afectados = 0
        for cambio in cambios:
            columna = _columna_editable(definicion, cambio.etiqueta)
            if columna is None:
                raise ColumnaProtegidaError(
                    MENSAJE_COLUMNA_PROTEGIDA.format(etiqueta=cambio.etiqueta)
                )
            valor = self._resolver_valor(conexion, columna, cambio.valor)
            afectados += int(
                conexion.execute(
                    _sql_actualizar_columna(definicion, columna.columna),
                    {"valor": valor, "id": int(cambio.id_registro)},
                ).rowcount
            )
        return afectados

    def _aplicar_cambios_evento(
        self, conexion: Connection, definicion: DefinicionTabla, cambios: list[CambioRegistro]
    ) -> int:
        """Aplica cambios de la tabla de eventos agrupados por fila (spec 020).

        Agrupa los cambios por registro para resolver una sola vez el tipo de
        evento efectivo de cada fila y validar la compatibilidad de todos sus
        campos contra la categoría resultante.

        Args:
            conexion: Conexión activa dentro de la transacción.
            definicion: Metadatos de la tabla de eventos.
            cambios: Lista de cambios solicitados.

        Returns:
            Número de filas afectadas (sin contar la limpieza de campos huérfanos).
        """
        por_fila: dict[int, list[CambioRegistro]] = {}
        for cambio in cambios:
            por_fila.setdefault(int(cambio.id_registro), []).append(cambio)
        afectados = 0
        for id_registro, cambios_fila in por_fila.items():
            afectados += self._aplicar_cambios_evento_fila(
                conexion, definicion, id_registro, cambios_fila
            )
        return afectados

    def _aplicar_cambios_evento_fila(
        self,
        conexion: Connection,
        definicion: DefinicionTabla,
        id_registro: int,
        cambios_fila: list[CambioRegistro],
    ) -> int:
        """Valida, ejecuta y limpia los cambios de una sola fila de evento (spec 020).

        Args:
            conexion: Conexión activa dentro de la transacción.
            definicion: Metadatos de la tabla de eventos.
            id_registro: Clave primaria de la fila editada.
            cambios_fila: Cambios solicitados sobre esa fila.

        Returns:
            Número de filas afectadas por los cambios explícitos.

        Raises:
            ColumnaProtegidaError: Si se intenta editar una columna de solo lectura.
            CampoIncompatibleError: Si un campo no aplica a la categoría del evento.
            ValorInvalidoError: Si una fecha es inválida o el valor no es válido.
            CodigoInexistenteError: Si se reasigna un código inexistente.
        """
        columnas: dict[str, ColumnaEditable] = {}
        for cambio in cambios_fila:
            columna = _columna_editable(definicion, cambio.etiqueta)
            if columna is None:
                raise ColumnaProtegidaError(
                    MENSAJE_COLUMNA_PROTEGIDA.format(etiqueta=cambio.etiqueta)
                )
            columnas[cambio.etiqueta] = columna

        id_tipo_evento, nombre_evento = self._tipo_evento_efectivo(
            conexion, id_registro, columnas, cambios_fila
        )
        permitidos = (
            CAMPOS_EVENTO_POR_DEFECTO
            if id_tipo_evento is None
            else campos_permitidos_evento(id_tipo_evento)
        )
        self._validar_compatibilidad_evento(cambios_fila, columnas, permitidos, nombre_evento)

        afectados = 0
        for cambio in cambios_fila:
            columna = columnas[cambio.etiqueta]
            valor = self._resolver_valor(conexion, columna, cambio.valor)
            afectados += int(
                conexion.execute(
                    _sql_actualizar_columna(definicion, columna.columna),
                    {"valor": valor, "id": id_registro},
                ).rowcount
            )
        if any(cambio.etiqueta == ETIQUETA_EVENTO for cambio in cambios_fila):
            self._limpiar_campos_huerfanos(conexion, definicion, id_registro, permitidos)
        return afectados

    @staticmethod
    def _tipo_evento_efectivo(
        conexion: Connection,
        id_registro: int,
        columnas: dict[str, ColumnaEditable],
        cambios_fila: list[CambioRegistro],
    ) -> tuple[int | None, str]:
        """Resuelve el tipo de evento efectivo de una fila tras la edición.

        Si el usuario modificó la columna ``Evento`` se usa el tipo nuevo; en caso
        contrario se lee el tipo actual de la base de datos.

        Args:
            conexion: Conexión activa dentro de la transacción.
            id_registro: Clave primaria de la fila.
            columnas: Columnas editables de la fila indexadas por etiqueta.
            cambios_fila: Cambios solicitados sobre la fila.

        Returns:
            La tupla ``(id_tipo_evento, nombre_evento)``; ``id_tipo_evento`` es
            ``None`` si la fila no existe.
        """
        cambio_evento = next(
            (cambio for cambio in cambios_fila if cambio.etiqueta == ETIQUETA_EVENTO), None
        )
        if cambio_evento is not None:
            id_tipo_evento = cast(
                int,
                EventosRepository._resolver_valor(
                    conexion, columnas[ETIQUETA_EVENTO], cambio_evento.valor
                ),
            )
            return id_tipo_evento, str(cambio_evento.valor).strip()

        fila = conexion.execute(_SQL_TIPO_EVENTO_ACTUAL, {"id": id_registro}).first()
        if fila is None:
            return None, ""
        id_tipo_evento = int(fila[0])
        return id_tipo_evento, EventosRepository._nombre_tipo_evento(conexion, id_tipo_evento)

    @staticmethod
    def _nombre_tipo_evento(conexion: Connection, id_tipo_evento: int) -> str:
        """Devuelve el nombre legible de un tipo de evento (o su id si no existe).

        Args:
            conexion: Conexión activa dentro de la transacción.
            id_tipo_evento: Identificador del tipo de evento.

        Returns:
            El nombre del tipo de evento, o el identificador como texto.
        """
        fila = conexion.execute(_SQL_NOMBRE_TIPO_EVENTO, {"id": id_tipo_evento}).first()
        return str(fila[0]) if fila is not None else str(id_tipo_evento)

    @staticmethod
    def _validar_compatibilidad_evento(
        cambios_fila: list[CambioRegistro],
        columnas: dict[str, ColumnaEditable],
        permitidos: frozenset[str],
        nombre_evento: str,
    ) -> None:
        """Rechaza campos prohibidos y fechas inválidas de una fila de evento (spec 020).

        Args:
            cambios_fila: Cambios solicitados sobre la fila.
            columnas: Columnas editables de la fila indexadas por etiqueta.
            permitidos: Conjunto de columnas permitidas para la categoría.
            nombre_evento: Nombre legible de la categoría (para el mensaje).

        Raises:
            CampoIncompatibleError: Si un campo con valor no aplica a la categoría.
            ValorInvalidoError: Si una fecha es inválida o inverosímil.
        """
        for cambio in cambios_fila:
            columna = columnas[cambio.etiqueta]
            if columna.tipo == TIPO_EDICION_VIGENCIA:
                continue
            if columna.columna not in permitidos and not _valor_vacio(cambio.valor):
                raise CampoIncompatibleError(
                    MENSAJE_CAMPO_INCOMPATIBLE.format(
                        nombre_evento=nombre_evento, etiqueta=cambio.etiqueta
                    )
                )
            if columna.columna in CAMPOS_FECHA_EVENTO and not _valor_vacio(cambio.valor):
                _validar_fecha_evento(cambio.valor, cambio.etiqueta)

    @staticmethod
    def _limpiar_campos_huerfanos(
        conexion: Connection,
        definicion: DefinicionTabla,
        id_registro: int,
        permitidos: frozenset[str],
    ) -> None:
        """Resetea a ``NULL`` los campos incompatibles con el nuevo tipo (spec 020, S-03).

        Args:
            conexion: Conexión activa dentro de la transacción.
            definicion: Metadatos de la tabla de eventos.
            id_registro: Clave primaria de la fila editada.
            permitidos: Columnas permitidas para el nuevo tipo de evento.
        """
        for columna in CAMPOS_EVENTO_EDITABLES - permitidos:
            conexion.execute(
                _sql_actualizar_columna(definicion, columna),
                {"valor": None, "id": id_registro},
            )

    def _verificar_dependencias(self, definicion: DefinicionTabla, ids: list[int]) -> None:
        """Aborta la eliminación si algún registro tiene hijos dependientes.

        Args:
            definicion: Metadatos de la tabla a eliminar.
            ids: Identificadores de los registros que se intentan borrar.

        Raises:
            DependenciaRegistroError: Si el total de eventos o comportamientos
                dependientes es mayor que cero.
        """
        totales = {"eventos": 0, "comportamientos": 0, "licencias": 0}
        for id_registro in ids:
            if definicion.tabla == TABLA_PERSONA:
                dependencias = self.contar_dependencias_operador(id_registro)
            else:
                dependencias = self.contar_dependencias_operador(0, id_codigo=id_registro)
            for tabla, total in dependencias.items():
                totales[tabla] += total
        if totales["eventos"] > 0 or totales["comportamientos"] > 0 or totales["licencias"] > 0:
            raise DependenciaRegistroError(
                MENSAJE_DEPENDENCIAS.format(
                    eventos=totales["eventos"], comportamientos=totales["comportamientos"]
                )
            )

    @staticmethod
    def _resolver_valor(conexion: Connection, columna: ColumnaEditable, valor: object) -> object:
        """Valida y normaliza el valor de una celda según el tipo de columna.

        Args:
            conexion: Conexión activa dentro de la transacción.
            columna: Metadatos de la columna editable.
            valor: Valor nuevo propuesto.

        Returns:
            El valor listo para el parámetro enlazado del ``UPDATE``.

        Raises:
            CodigoInexistenteError: Si el código reasignado no existe.
            ValorInvalidoError: Si el valor no pertenece al catálogo permitido.
        """
        if columna.tipo == TIPO_EDICION_VIGENCIA:
            return _vigencia_desde_opcion(valor)
        if columna.tipo == TIPO_EDICION_CODIGO:
            codigo = _a_entero(valor)
            if conexion.execute(_SQL_CODIGO_EXISTE, {"id_codigo": codigo}).first() is None:
                raise CodigoInexistenteError(MENSAJE_CODIGO_INEXISTENTE.format(codigo=codigo))
            return codigo
        if columna.tipo == TIPO_EDICION_EVENTO:
            nombre = str(valor)
            fila = conexion.execute(_SQL_TIPO_EVENTO_POR_NOMBRE, {"nombre": nombre}).first()
            if fila is None:
                raise ValorInvalidoError(
                    MENSAJE_VALOR_INVALIDO.format(valor=valor, etiqueta=columna.etiqueta)
                )
            return int(fila[0])
        if columna.tipo == TIPO_EDICION_GENERO:
            genero = str(valor).strip().upper()
            if genero not in GENEROS_VALIDOS:
                raise ValorInvalidoError(
                    MENSAJE_VALOR_INVALIDO.format(valor=valor, etiqueta=columna.etiqueta)
                )
            return genero
        if columna.tipo == TIPO_EDICION_LICENCIA:
            licencia = str(valor).strip().upper()
            if licencia not in OPCIONES_LICENCIA:
                raise ValorInvalidoError(
                    MENSAJE_VALOR_INVALIDO.format(valor=valor, etiqueta=columna.etiqueta)
                )
            return licencia
        if columna.tipo in (TIPO_EDICION_FUENTE, TIPO_EDICION_DESCRIPCION):
            texto = "" if valor is None else str(valor)
            sentencia = (
                _SQL_FUENTE_EXISTE
                if columna.tipo == TIPO_EDICION_FUENTE
                else _SQL_DESCRIPCION_EXISTE
            )
            if conexion.execute(sentencia, {"valor": texto}).first() is None:
                raise ValorInvalidoError(
                    MENSAJE_VALOR_INVALIDO.format(valor=valor, etiqueta=columna.etiqueta)
                )
            return texto
        if columna.tipo == TIPO_EDICION_ENTERO:
            return _a_entero(valor)
        if valor is None:
            return None
        return str(valor)

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
    "ACCION_EDITAR_TABLA",
    "ACCION_ELIMINAR_LOTE",
    "ACCION_ELIMINAR_REGISTROS",
    "ACCION_ELIMINAR_TABLA",
    "ACCION_REACTIVAR_LOTE",
    "ACCION_REACTIVAR_REGISTROS",
    "ACCION_REACTIVAR_TABLA",
    "CAMPOS_EVENTO_EDITABLES",
    "CAMPOS_EVENTO_POR_DEFECTO",
    "CAMPOS_FECHA_EVENTO",
    "CAMPOS_PERMITIDOS_POR_EVENTO",
    "CLAVE_TABLA_EVENTOS",
    "ESTADO_ANULADO_TEXTO",
    "ESTADO_VIGENTE_TEXTO",
    "ETIQUETA_ESTADO",
    "ETIQUETA_EVENTO",
    "FORMATO_LOTE",
    "GENEROS_VALIDOS",
    "LIMITE_POR_DEFECTO",
    "MENSAJE_CAMPO_INCOMPATIBLE",
    "MENSAJE_CODIGO_INEXISTENTE",
    "MENSAJE_COLUMNA_PROTEGIDA",
    "MENSAJE_DEPENDENCIAS",
    "MENSAJE_FECHA_FUTURA",
    "MENSAJE_FECHA_INVALIDA",
    "MENSAJE_VALOR_INVALIDO",
    "OPCIONES_ESTADO",
    "OPCIONES_LICENCIA",
    "OPCION_ANULADO",
    "OPCION_VIGENTE",
    "TABLAS_CORRECCION",
    "TABLA_PERSONA",
    "TIPO_EDICION_CODIGO",
    "TIPO_EDICION_DESCRIPCION",
    "TIPO_EDICION_ENTERO",
    "TIPO_EDICION_EVENTO",
    "TIPO_EDICION_FECHA",
    "TIPO_EDICION_FUENTE",
    "TIPO_EDICION_GENERO",
    "TIPO_EDICION_LICENCIA",
    "TIPO_EDICION_TEXTO",
    "TIPO_EDICION_VIGENCIA",
    "TIPO_EVENTO_CANCELACION",
    "TIPO_EVENTO_CERTIFICACION",
    "TIPO_EVENTO_OBSERVACION",
    "TIPO_EVENTO_REACTIVACION",
    "TIPO_EVENTO_RENOVACION",
    "TIPO_EVENTO_RESTRICCION_MEDICA",
    "TIPO_EVENTO_SUSPENSION",
    "CambioRegistro",
    "CampoIncompatibleError",
    "CodigoInexistenteError",
    "ColumnaEditable",
    "ColumnaProtegidaError",
    "ColumnaTabla",
    "DefinicionTabla",
    "DependenciaRegistroError",
    "EventoInfo",
    "EventosRepository",
    "FiltroEventos",
    "LoteInfo",
    "RegistroInfo",
    "TipoEventoInfo",
    "ValorInvalidoError",
    "campos_permitidos_evento",
]
