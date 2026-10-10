"""Pruebas de la corrección de registros (specs 015, 017, 018, 019 y 020).

Cubren cinco frentes: el repositorio ``EventosRepository`` contra una base
SQLite temporal (búsqueda con filtros y mutaciones de la spec 006, el listado y
las mutaciones genéricas por tabla de la spec 015, las validaciones de
integridad referencial y edición segura de la spec 017, los catálogos
oficiales y la tabla de códigos de la spec 018, las columnas completas de
negocio de la tabla de eventos de la spec 019 y el bloqueo de campos por
categoría de evento de la spec 020), las funciones puras de la UI
tipo Excel (incluidas la búsqueda rápida, las acciones en bloque de la spec
018 y la proyección de columnas/filas por tipo de evento de la spec 020), el
catálogo de tablas soportadas y las verificaciones estáticas de los
criterios de aceptación: el paquete existe, la UI usa ``st.data_editor`` con
columnas protegidas y listas desplegables, ofrece el buscador rápido, expone los
botones de acción en bloque y de guardado, no contiene SQL, y el repositorio
valida dependencias y códigos. Todas las pruebas siguen el patrón AAA
(*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from certificado_operadores.domain.models import VIGENCIA_ACTIVA, VIGENCIA_ANULADA
from certificado_operadores.domain.usuarios import (
    ROL_ADMINISTRADOR,
    ROL_SUPER_ADMINISTRADOR,
)
from certificado_operadores.infra.eventos_repository import (
    ACCION_ANULAR_REGISTROS,
    ACCION_EDITAR_TABLA,
    ACCION_ELIMINAR_LOTE,
    ACCION_ELIMINAR_REGISTROS,
    ACCION_REACTIVAR_LOTE,
    ACCION_REACTIVAR_REGISTROS,
    CAMPOS_EVENTO_POR_DEFECTO,
    CAMPOS_PERMITIDOS_POR_EVENTO,
    ETIQUETA_ESTADO,
    ETIQUETA_EVENTO,
    GENEROS_VALIDOS,
    MENSAJE_CAMPO_INCOMPATIBLE,
    OPCION_ANULADO,
    OPCION_VIGENTE,
    OPCIONES_LICENCIA,
    TABLA_PERSONA,
    TABLAS_CORRECCION,
    TIPO_EDICION_CODIGO,
    TIPO_EDICION_ENTERO,
    TIPO_EDICION_EVENTO,
    TIPO_EDICION_FECHA,
    TIPO_EDICION_TEXTO,
    TIPO_EVENTO_CANCELACION,
    TIPO_EVENTO_CERTIFICACION,
    TIPO_EVENTO_OBSERVACION,
    TIPO_EVENTO_REACTIVACION,
    TIPO_EVENTO_RENOVACION,
    TIPO_EVENTO_RESTRICCION_MEDICA,
    TIPO_EVENTO_SUSPENSION,
    CambioRegistro,
    CampoIncompatibleError,
    CodigoInexistenteError,
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
from certificado_operadores.modulos.correccion_registros import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "1_Configuracion.py"
_RUTA_HEREDADO = _RUTA_UI.parents[1] / "3_Modificacion_Tablas.py"

_LOTE_CORTO = "2026-01-10 08:15"
_LOTE_MEDIO = "2026-01-10 09:40"
_LOTE_TARDIO = "2026-02-05 09:40"

CLAVES_TABLAS = ("eventos", "licencias", "comportamientos", "operadores", "codigos")
ETIQUETAS_TABLAS = ("Eventos", "Licencias", "Comportamientos", "Operadores", "Códigos")

# --- Esquema mínimo para las pruebas del repositorio ------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_tipo_evento (
        id_tipo_evento INTEGER PRIMARY KEY,
        nombre_evento TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE dim_persona (
        id_persona INTEGER PRIMARY KEY,
        nombres TEXT,
        primer_apellido TEXT,
        segundo_apellido TEXT,
        genero TEXT,
        id_vigencia INTEGER
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY,
        id_persona INTEGER NOT NULL,
        id_empresa INTEGER,
        id_vigencia INTEGER,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE dim_empresa (
        id_empresa INTEGER PRIMARY KEY,
        nombre_empresa TEXT
    );
    """,
    """
    CREATE TABLE dim_detalle_comportamiento (
        id_jerarquia INTEGER PRIMARY KEY,
        fuente TEXT,
        descripcion_comportamiento TEXT,
        id_comportamiento INTEGER
    );
    """,
    """
    CREATE TABLE fact_eventos_operador (
        id_hecho_evento INTEGER PRIMARY KEY,
        id_codigo INTEGER NOT NULL,
        id_tipo_evento INTEGER NOT NULL,
        id_vehiculo_evaluado INTEGER,
        evaluador TEXT,
        fecha_prueba TEXT,
        fecha_certificado TEXT,
        fecha_retiro TEXT,
        fecha_notificacion_retiro TEXT,
        fecha_suspension TEXT,
        fecha_observacion TEXT,
        observacion TEXT,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE fact_licencias (
        id_hecho_licencia INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        tipo TEXT,
        vencimiento TEXT,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE fact_comportamiento (
        id_hecho_comportamiento INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        fuente TEXT,
        descripcion_comportamiento TEXT,
        fecha_evento TEXT,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE log_auditoria (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        accion TEXT NOT NULL,
        detalles TEXT,
        fecha_registro TEXT
    );
    """,
)

_TIPOS = ((1, "Certificación"), (2, "Reactivación"), (7, "Cancelación"))

_EVENTOS = (
    # id_hecho_evento, id_codigo, id_tipo_evento, fecha_registro, id_vigencia,
    # id_vehiculo_evaluado, evaluador, fecha_prueba, fecha_certificado, fecha_retiro,
    # fecha_notificacion_retiro, fecha_suspension, fecha_observacion, observacion
    {
        "id_hecho_evento": 1,
        "id_codigo": 5001,
        "id_tipo_evento": 1,
        "id_vehiculo_evaluado": 1,
        "evaluador": "Juan Pérez",
        "fecha_prueba": "2026-01-08",
        "fecha_certificado": "2026-01-10",
        "fecha_retiro": None,
        "fecha_notificacion_retiro": None,
        "fecha_suspension": None,
        "fecha_observacion": None,
        "observacion": "Certificado inicial",
        "id_vigencia": VIGENCIA_ACTIVA,
        "fecha_registro": "2026-01-10 08:15:00",
    },
    {
        "id_hecho_evento": 2,
        "id_codigo": 5001,
        "id_tipo_evento": 2,
        "id_vehiculo_evaluado": None,
        "evaluador": None,
        "fecha_prueba": None,
        "fecha_certificado": None,
        "fecha_retiro": None,
        "fecha_notificacion_retiro": None,
        "fecha_suspension": None,
        "fecha_observacion": None,
        "observacion": None,
        "id_vigencia": VIGENCIA_ANULADA,
        "fecha_registro": "2026-01-10 08:15:30",
    },
    {
        "id_hecho_evento": 3,
        "id_codigo": 5002,
        "id_tipo_evento": 1,
        "id_vehiculo_evaluado": 2,
        "evaluador": "María López",
        "fecha_prueba": None,
        "fecha_certificado": None,
        "fecha_retiro": None,
        "fecha_notificacion_retiro": None,
        "fecha_suspension": None,
        "fecha_observacion": None,
        "observacion": None,
        "id_vigencia": VIGENCIA_ACTIVA,
        "fecha_registro": "2026-01-10 09:40:00",
    },
    {
        "id_hecho_evento": 4,
        "id_codigo": 5002,
        "id_tipo_evento": 7,
        "id_vehiculo_evaluado": None,
        "evaluador": None,
        "fecha_prueba": None,
        "fecha_certificado": None,
        "fecha_retiro": "2026-02-05",
        "fecha_notificacion_retiro": "2026-02-04",
        "fecha_suspension": None,
        "fecha_observacion": None,
        "observacion": "Retiro voluntario",
        "id_vigencia": VIGENCIA_ACTIVA,
        "fecha_registro": "2026-02-05 09:40:10",
    },
)

_LICENCIAS = (
    # (id, id_codigo, tipo, vencimiento, id_vigencia, fecha_registro)
    (1, 5001, "C3", "2030-01-01", VIGENCIA_ACTIVA, "2026-01-10 08:00:00"),
    (2, 5002, "C2", "2031-01-01", VIGENCIA_ANULADA, "2026-02-01 08:00:00"),
)

_COMPORTAMIENTOS = (
    # (id, id_codigo, fuente, descripcion, fecha_evento, id_vigencia, fecha_registro)
    (1, 5001, "PQRS", "Exceso de velocidad", "2026-01-05", VIGENCIA_ACTIVA, "2026-01-10"),
    (2, 5002, "Operativo", "Alta sin cinturón", "2026-02-05", VIGENCIA_ACTIVA, "2026-02-06"),
)

_EMPRESAS = (
    # (id_empresa, nombre_empresa)
    (1, "Metro Línea S.A."),
    (2, "Blanco y Negro S.A."),
)

_DETALLES_COMPORTAMIENTO = (
    # (id_jerarquia, fuente, descripcion_comportamiento, id_comportamiento)
    (1, "PQRS", "Exceso de velocidad", 1),
    (2, "Operativo", "Alta sin cinturón", 2),
)

_CODIGOS = (
    # (id_codigo, id_persona, id_empresa, id_vigencia, fecha_registro)
    (5001, 1001, 1, VIGENCIA_ACTIVA, "2020-05-04"),
    (5002, 1002, 2, VIGENCIA_ACTIVA, "2021-07-15"),
    (5003, 1003, None, VIGENCIA_ANULADA, "2022-01-20"),
)


def _crear_esquema(motor: Engine) -> None:
    """Crea las tablas mínimas de eventos, dimensiones y auditoría.

    Args:
        motor: Motor SQLAlchemy donde se crea el esquema.
    """
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta tipos, personas, códigos y registros de ejemplo.

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_tipo_evento VALUES (:id, :nombre)"),
            [{"id": tipo, "nombre": nombre} for tipo, nombre in _TIPOS],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_persona "
                "(id_persona, nombres, primer_apellido, segundo_apellido, genero, id_vigencia) "
                "VALUES (:id, :nombres, :apellido, :segundo, :genero, :vigencia)"
            ),
            [
                {
                    "id": 1001,
                    "nombres": "Ana",
                    "apellido": "Pérez",
                    "segundo": "Gómez",
                    "genero": "F",
                    "vigencia": VIGENCIA_ACTIVA,
                },
                {
                    "id": 1002,
                    "nombres": "Luis",
                    "apellido": "Rojas",
                    "segundo": "",
                    "genero": "M",
                    "vigencia": VIGENCIA_ACTIVA,
                },
                {
                    "id": 1003,
                    "nombres": "Marta",
                    "apellido": "López",
                    "segundo": "Díaz",
                    "genero": "F",
                    "vigencia": VIGENCIA_ANULADA,
                },
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_empresa (id_empresa, nombre_empresa) VALUES (:id, :nombre)"),
            [{"id": id_empresa, "nombre": nombre} for id_empresa, nombre in _EMPRESAS],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_detalle_comportamiento "
                "(id_jerarquia, fuente, descripcion_comportamiento, id_comportamiento) "
                "VALUES (:id, :fuente, :descripcion, :comportamiento)"
            ),
            [
                {
                    "id": id_jerarquia,
                    "fuente": fuente,
                    "descripcion": descripcion,
                    "comportamiento": comportamiento,
                }
                for id_jerarquia, fuente, descripcion, comportamiento in _DETALLES_COMPORTAMIENTO
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_codigo "
                "(id_codigo, id_persona, id_empresa, id_vigencia, fecha_registro) "
                "VALUES (:id_codigo, :id_persona, :id_empresa, :vigencia, :fecha_registro)"
            ),
            [
                {
                    "id_codigo": id_codigo,
                    "id_persona": id_persona,
                    "id_empresa": id_empresa,
                    "vigencia": vigencia,
                    "fecha_registro": fecha_registro,
                }
                for id_codigo, id_persona, id_empresa, vigencia, fecha_registro in _CODIGOS
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador "
                "(id_hecho_evento, id_codigo, id_tipo_evento, id_vehiculo_evaluado, "
                "evaluador, fecha_prueba, fecha_certificado, fecha_retiro, "
                "fecha_notificacion_retiro, fecha_suspension, fecha_observacion, "
                "observacion, id_vigencia, fecha_registro) "
                "VALUES (:id_hecho_evento, :id_codigo, :id_tipo_evento, "
                ":id_vehiculo_evaluado, :evaluador, :fecha_prueba, :fecha_certificado, "
                ":fecha_retiro, :fecha_notificacion_retiro, :fecha_suspension, "
                ":fecha_observacion, :observacion, :id_vigencia, :fecha_registro)"
            ),
            _EVENTOS,
        )
        conexion.execute(
            text(
                "INSERT INTO fact_licencias "
                "(id_hecho_licencia, id_codigo, tipo, vencimiento, id_vigencia, fecha_registro) "
                "VALUES (:id, :codigo, :tipo, :vencimiento, :vigencia, :fecha)"
            ),
            [
                {
                    "id": identificador,
                    "codigo": codigo,
                    "tipo": tipo,
                    "vencimiento": vencimiento,
                    "vigencia": vigencia,
                    "fecha": fecha,
                }
                for identificador, codigo, tipo, vencimiento, vigencia, fecha in _LICENCIAS
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_comportamiento "
                "(id_hecho_comportamiento, id_codigo, fuente, descripcion_comportamiento, "
                "fecha_evento, id_vigencia, fecha_registro) "
                "VALUES (:id, :codigo, :fuente, :descripcion, :fecha_evento, :vigencia, :fecha)"
            ),
            [
                {
                    "id": identificador,
                    "codigo": codigo,
                    "fuente": fuente,
                    "descripcion": descripcion,
                    "fecha_evento": fecha_evento,
                    "vigencia": vigencia,
                    "fecha": fecha,
                }
                for (
                    identificador,
                    codigo,
                    fuente,
                    descripcion,
                    fecha_evento,
                    vigencia,
                    fecha,
                ) in _COMPORTAMIENTOS
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_eventos.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar_datos(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def repositorio(motor_sqlite: Engine) -> EventosRepository:
    """Repositorio de eventos configurado con el motor SQLite de prueba."""
    return EventosRepository(engine=motor_sqlite)


def _vigencia_de(motor: Engine, tabla: str, columna: str, identificador: int) -> int:
    """Devuelve la vigencia almacenada de un registro de cualquier tabla."""
    with motor.connect() as conexion:
        return int(
            conexion.execute(
                text(f"SELECT id_vigencia FROM {tabla} WHERE {columna} = :id"),
                {"id": identificador},
            ).scalar_one()
        )


def _total(motor: Engine, tabla: str) -> int:
    """Cuenta las filas de una tabla."""
    with motor.connect() as conexion:
        return int(conexion.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar_one())


def _celda(motor: Engine, id_evento: int, columna: str) -> object:
    """Devuelve el valor de una columna de un evento de ``fact_eventos_operador``."""
    with motor.connect() as conexion:
        return conexion.execute(
            text(f"SELECT {columna} FROM fact_eventos_operador WHERE id_hecho_evento = :id"),
            {"id": id_evento},
        ).scalar_one()


def _columna_fisica(etiqueta: str) -> str:
    """Traduce la etiqueta legible de una columna editable de Eventos a su nombre físico."""
    return next(
        columna.columna
        for columna in _definicion("eventos").editables
        if columna.etiqueta == etiqueta
    )


def _auditoria(motor: Engine) -> list[tuple[str, str]]:
    """Devuelve las acciones de auditoría registradas como pares (acción, detalle)."""
    with motor.connect() as conexion:
        filas = conexion.execute(
            text("SELECT accion, detalles FROM log_auditoria ORDER BY id_log")
        ).all()
    return [(str(accion), str(detalles or "")) for accion, detalles in filas]


def _ids(eventos: Iterable[EventoInfo]) -> list[int]:
    """Extrae los identificadores de una lista de eventos."""
    return [evento.id_hecho_evento for evento in eventos]


def _definicion(clave: str) -> DefinicionTabla:
    """Devuelve la definición del catálogo para una clave."""
    return next(definicion for definicion in TABLAS_CORRECCION if definicion.clave == clave)


# --- Repositorio: tipos de evento -------------------------------------------
def test_listar_tipos_evento_devuelve_dtos_ordenados(repositorio: EventosRepository) -> None:
    """El repositorio devuelve los tipos de evento ordenados por id."""
    # Arrange / Act
    tipos = repositorio.listar_tipos_evento()

    # Assert
    assert tipos == [
        TipoEventoInfo(1, "Certificación"),
        TipoEventoInfo(2, "Reactivación"),
        TipoEventoInfo(7, "Cancelación"),
    ]


# --- Repositorio: búsqueda con filtros (spec 006) ---------------------------
def test_buscar_eventos_sin_filtro_devuelve_todos(repositorio: EventosRepository) -> None:
    """RF-01: sin filtros se listan todos los eventos, del más reciente al más antiguo."""
    # Arrange / Act
    eventos = repositorio.buscar_eventos()

    # Assert
    assert _ids(eventos) == [4, 3, 2, 1]
    assert eventos[0].nombre == "Luis Rojas"
    assert eventos[0].estado == "Vigente"


def test_buscar_eventos_filtra_por_codigo(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por código limita los eventos del operador."""
    # Arrange
    filtro = FiltroEventos(codigo=5001)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [2, 1]


def test_buscar_eventos_filtra_por_vigencia(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por estado deja solo los eventos de esa vigencia."""
    # Arrange
    filtro = FiltroEventos(vigencia=VIGENCIA_ANULADA)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [2]
    assert eventos[0].estado == "Anulado"


def test_buscar_eventos_filtra_por_rango_de_fechas(repositorio: EventosRepository) -> None:
    """RF-01: el rango de fechas es inclusivo en ambos extremos."""
    # Arrange
    filtro = FiltroEventos(fecha_desde=date(2026, 1, 10), fecha_hasta=date(2026, 1, 31))

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [3, 2, 1]


def test_buscar_eventos_respeta_el_limite(repositorio: EventosRepository) -> None:
    """RF-01: la búsqueda nunca devuelve más filas que el límite indicado."""
    # Arrange
    filtro = FiltroEventos(limite=2)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [4, 3]


# --- Repositorio: lotes (spec 006) ------------------------------------------
def test_listar_lotes_agrupa_por_minuto(repositorio: EventosRepository) -> None:
    """RF-02: los lotes se agrupan por minuto de cargue, del más reciente al más antiguo."""
    # Arrange / Act
    lotes = repositorio.listar_lotes()

    # Assert
    assert lotes == [
        LoteInfo(_LOTE_TARDIO, 1),
        LoteInfo(_LOTE_MEDIO, 1),
        LoteInfo(_LOTE_CORTO, 2),
    ]


def test_reactivar_lote_afecta_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: reactivar el lote actualiza todos sus eventos y audita."""
    # Act
    afectados = repositorio.reactivar_lote(_LOTE_CORTO, "admin")

    # Assert
    assert afectados == 2
    assert _vigencia_de(motor_sqlite, "fact_eventos_operador", "id_hecho_evento", 2) == (
        VIGENCIA_ACTIVA
    )
    assert _auditoria(motor_sqlite) == [(ACCION_REACTIVAR_LOTE, f"Lote:{_LOTE_CORTO}")]


# --- Repositorio: mutaciones individuales con auditoría (spec 006) ----------
def test_reactivar_registros_cambia_vigencia_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: reactivar actualiza la vigencia y registra la auditoría."""
    # Act
    afectados = repositorio.reactivar_registros([2], "admin")

    # Assert
    assert afectados == 1
    assert _vigencia_de(motor_sqlite, "fact_eventos_operador", "id_hecho_evento", 2) == (
        VIGENCIA_ACTIVA
    )
    assert _auditoria(motor_sqlite) == [(ACCION_REACTIVAR_REGISTROS, "IDs: 2")]


def test_anular_registros_cambia_vigencia_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: anular actualiza la vigencia de todos los ids y audita."""
    # Act
    afectados = repositorio.anular_registros([1, 3], "admin")

    # Assert
    assert afectados == 2
    assert _auditoria(motor_sqlite) == [(ACCION_ANULAR_REGISTROS, "IDs: 1,3")]


def test_eliminar_registros_borra_fisicamente_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: eliminar borra la fila y registra la auditoría."""
    # Act
    afectados = repositorio.eliminar_registros([4], "admin")

    # Assert
    assert afectados == 1
    assert _total(motor_sqlite, "fact_eventos_operador") == 3
    assert _auditoria(motor_sqlite) == [(ACCION_ELIMINAR_REGISTROS, "IDs: 4")]


def test_eliminar_lote_borra_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: eliminar el lote borra sus eventos y audita."""
    # Act
    afectados = repositorio.eliminar_lote(_LOTE_TARDIO, "admin")

    # Assert
    assert afectados == 1
    assert _auditoria(motor_sqlite) == [(ACCION_ELIMINAR_LOTE, f"Lote:{_LOTE_TARDIO}")]


# --- Catálogo de tablas (specs 015 y 018) -----------------------------------
def test_catalogo_tablas_expone_las_cinco_tablas() -> None:
    """CA-01/CA-04: el catálogo declara las cinco tablas en el orden de las sub-pestañas."""
    # Arrange / Act
    claves = tuple(definicion.clave for definicion in TABLAS_CORRECCION)
    etiquetas = tuple(definicion.etiqueta for definicion in TABLAS_CORRECCION)

    # Assert
    assert claves == CLAVES_TABLAS
    assert etiquetas == ETIQUETAS_TABLAS


# --- Repositorio: listado genérico por tabla (spec 015) ---------------------
def test_listar_registros_eventos_mapea_filas(repositorio: EventosRepository) -> None:
    """CA-03: el listado genérico de eventos devuelve filas con etiquetas legibles."""
    # Act
    registros = repositorio.listar_registros("eventos")

    # Assert
    assert [registro.id_registro for registro in registros] == [4, 3, 2, 1]
    assert registros[0].datos["Nombre"] == "Luis Rojas"
    assert registros[0].datos["Evento"] == "Cancelación"
    assert registros[0].estado == "Vigente"
    assert registros[2].estado == "Anulado"


# --- Spec 019: columnas completas de negocio en eventos ---------------------
def test_definicion_eventos_expone_todas_las_columnas_de_negocio() -> None:
    """CA-01: la definición de eventos incluye fechas, evaluador, vehículo y observación."""
    # Arrange
    definicion = _definicion("eventos")

    # Act
    etiquetas = [columna.etiqueta for columna in definicion.columnas]

    # Assert
    assert etiquetas == [
        "Código",
        "Cédula",
        "Nombre",
        "Evento",
        "Fecha Certificado",
        "Fecha Retiro",
        "Fecha Notif. Retiro",
        "Fecha Suspensión",
        "Fecha Prueba",
        "Evaluador",
        "Vehículo Evaluado",
        "Observación",
        "Registro",
    ]


def test_definicion_eventos_marca_columnas_editables_con_su_tipo() -> None:
    """CA-01/CA-02: cada columna de negocio editable declara su tipo de edición."""
    # Arrange
    definicion = _definicion("eventos")

    # Act
    tipos = {columna.etiqueta: columna.tipo for columna in definicion.editables}

    # Assert
    assert tipos["Fecha Certificado"] == TIPO_EDICION_FECHA
    assert tipos["Fecha Retiro"] == TIPO_EDICION_FECHA
    assert tipos["Fecha Notif. Retiro"] == TIPO_EDICION_FECHA
    assert tipos["Fecha Suspensión"] == TIPO_EDICION_FECHA
    assert tipos["Fecha Prueba"] == TIPO_EDICION_FECHA
    assert tipos["Evaluador"] == TIPO_EDICION_TEXTO
    assert tipos["Vehículo Evaluado"] == TIPO_EDICION_ENTERO
    assert tipos["Observación"] == TIPO_EDICION_TEXTO
    assert tipos["Código"] == TIPO_EDICION_CODIGO
    assert tipos["Evento"] == TIPO_EDICION_EVENTO


def test_listar_registros_eventos_expone_las_columnas_de_negocio(
    repositorio: EventosRepository,
) -> None:
    """CA-01: el listado trae los valores de fechas, evaluador, vehículo y observación."""
    # Act
    registros = repositorio.listar_registros("eventos")

    # Assert: evento 4 (índice 0) trae retiro y observación
    assert registros[0].datos["Fecha Retiro"] == "2026-02-05"
    assert registros[0].datos["Fecha Notif. Retiro"] == "2026-02-04"
    assert registros[0].datos["Observación"] == "Retiro voluntario"
    # Evento 1 (índice 3) trae certificado, prueba, evaluador y vehículo
    assert registros[3].datos["Fecha Certificado"] == "2026-01-10"
    assert registros[3].datos["Fecha Prueba"] == "2026-01-08"
    assert registros[3].datos["Evaluador"] == "Juan Pérez"
    assert registros[3].datos["Vehículo Evaluado"] == 1
    assert registros[3].datos["Registro"] == "2026-01-10 08:15:00"


def test_listar_registros_licencias(repositorio: EventosRepository) -> None:
    """CA-01: la tabla de licencias expone sus columnas propias."""
    # Act
    registros = repositorio.listar_registros("licencias")

    # Assert
    assert [registro.id_registro for registro in registros] == [2, 1]
    assert registros[1].datos["Tipo"] == "C3"
    assert registros[1].datos["Cédula"] == 1001
    assert registros[0].estado == "Anulado"


def test_listar_registros_comportamientos(repositorio: EventosRepository) -> None:
    """CA-01: la tabla de comportamientos expone su fuente y descripción."""
    # Act
    registros = repositorio.listar_registros("comportamientos")

    # Assert
    assert [registro.id_registro for registro in registros] == [2, 1]
    assert registros[0].datos["Fuente"] == "Operativo"
    assert registros[1].datos["Descripción"] == "Exceso de velocidad"


def test_listar_registros_operadores(repositorio: EventosRepository) -> None:
    """CA-01: la tabla de operadores lista personas con su vigencia."""
    # Act
    registros = repositorio.listar_registros("operadores")

    # Assert
    assert [registro.id_registro for registro in registros] == [1001, 1002, 1003]
    assert registros[0].datos["Nombres"] == "Ana"
    assert registros[0].datos["Primer apellido"] == "Pérez"
    assert registros[2].estado == "Anulado"


def test_listar_registros_codigos(repositorio: EventosRepository) -> None:
    """CA-04: la tabla de códigos expone operador, empresa y fecha de vigencia."""
    # Act
    registros = repositorio.listar_registros("codigos")

    # Assert
    assert [registro.id_registro for registro in registros] == [5001, 5002, 5003]
    assert registros[0].datos["Código"] == 5001
    assert registros[0].datos["Cédula"] == 1001
    assert registros[0].datos["Nombre"] == "Ana Pérez"
    assert registros[0].datos["Empresa"] == "Metro Línea S.A."
    assert registros[0].datos["Desde"] == "2020-05-04"
    assert registros[1].datos["Empresa"] == "Blanco y Negro S.A."
    assert registros[2].datos["Empresa"] is None


def test_listar_fuentes_comportamiento(repositorio: EventosRepository) -> None:
    """CA-03: el repositorio lista las fuentes oficiales del catálogo."""
    # Act
    fuentes = repositorio.listar_fuentes_comportamiento()

    # Assert
    assert fuentes == ["Operativo", "PQRS"]


def test_listar_descripciones_comportamiento(repositorio: EventosRepository) -> None:
    """CA-03: el repositorio lista las descripciones oficiales del catálogo."""
    # Act
    descripciones = repositorio.listar_descripciones_comportamiento()

    # Assert
    assert descripciones == ["Alta sin cinturón", "Exceso de velocidad"]


def test_listar_registros_respeta_el_limite(repositorio: EventosRepository) -> None:
    """El listado genérico no devuelve más filas que el límite indicado."""
    # Act
    registros = repositorio.listar_registros("eventos", limite=2)

    # Assert
    assert [registro.id_registro for registro in registros] == [4, 3]


def test_listar_registros_clave_desconocida_lanza(repositorio: EventosRepository) -> None:
    """Una tabla fuera del catálogo produce un error explícito."""
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        repositorio.listar_registros("inexistente")


# --- Repositorio: mutaciones genéricas por tabla (spec 015) -----------------
def test_mutar_vigencia_reactiva_los_ids(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-04: reactivar cambia la vigencia a activa y audita con la tabla."""
    # Act
    afectados = repositorio.mutar_vigencia("licencias", [2], VIGENCIA_ACTIVA, "admin")

    # Assert
    assert afectados == 1
    assert _vigencia_de(motor_sqlite, "fact_licencias", "id_hecho_licencia", 2) == VIGENCIA_ACTIVA
    assert _auditoria(motor_sqlite) == [("Reactivar Licencias", "IDs: 2")]


def test_mutar_vigencia_anula_los_ids(repositorio: EventosRepository, motor_sqlite: Engine) -> None:
    """CA-04: anular cambia la vigencia a inactiva y audita."""
    # Act
    afectados = repositorio.mutar_vigencia("operadores", [1001, 1002], VIGENCIA_ANULADA, "admin")

    # Assert
    assert afectados == 2
    assert _vigencia_de(motor_sqlite, "dim_persona", "id_persona", 1001) == VIGENCIA_ANULADA
    assert _auditoria(motor_sqlite) == [("Anular Operadores", "IDs: 1001,1002")]


def test_eliminar_registros_tabla_borra_fisicamente_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-04: eliminar borra el registro de la tabla y audita."""
    # Act
    afectados = repositorio.eliminar_registros_tabla("comportamientos", [2], "admin")

    # Assert
    assert afectados == 1
    assert _total(motor_sqlite, "fact_comportamiento") == 1
    assert _auditoria(motor_sqlite) == [("Eliminar Comportamientos", "IDs: 2")]


def test_mutar_vigencia_sin_ids_no_afecta_ni_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: una selección vacía no ejecuta SQL ni deja auditoría."""
    # Arrange / Act
    afectados = repositorio.mutar_vigencia("eventos", [], VIGENCIA_ACTIVA, "admin")

    # Assert
    assert afectados == 0
    assert _auditoria(motor_sqlite) == []


def test_eliminar_registros_tabla_sin_ids_no_afecta_ni_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: eliminar con una selección vacía no ejecuta SQL."""
    # Arrange / Act
    afectados = repositorio.eliminar_registros_tabla("operadores", [], "admin")

    # Assert
    assert afectados == 0
    assert _total(motor_sqlite, "dim_persona") == 3
    assert _auditoria(motor_sqlite) == []


# --- Spec 017: integridad referencial (S-01) --------------------------------
def test_contar_dependencias_operador_cuenta_hijos(repositorio: EventosRepository) -> None:
    """CA-02: el operador 1001 tiene 2 eventos, 1 comportamiento y 1 licencia."""
    # Arrange / Act
    dependencias = repositorio.contar_dependencias_operador(1001)

    # Assert
    assert dependencias == {"eventos": 2, "comportamientos": 1, "licencias": 1}


def test_contar_dependencias_operador_por_codigo(repositorio: EventosRepository) -> None:
    """CA-02: el conteo se puede acotar a un código de operación concreto."""
    # Arrange / Act
    dependencias = repositorio.contar_dependencias_operador(1001, id_codigo=5001)

    # Assert
    assert dependencias == {"eventos": 2, "comportamientos": 1, "licencias": 1}


def test_contar_dependencias_operador_sin_codigos(repositorio: EventosRepository) -> None:
    """CA-02: un operador sin códigos no tiene dependencias."""
    # Arrange / Act
    dependencias = repositorio.contar_dependencias_operador(9999)

    # Assert
    assert dependencias == {"eventos": 0, "comportamientos": 0, "licencias": 0}


def test_validar_codigo_existe(repositorio: EventosRepository) -> None:
    """CA-03: el repositorio distingue códigos existentes de inexistentes."""
    # Arrange / Act / Assert
    assert repositorio.validar_codigo_existe(5001) is True
    assert repositorio.validar_codigo_existe(9999) is False


def test_eliminar_operador_con_dependencias_bloquea(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02/S-01: no se elimina un operador con eventos ni comportamientos."""
    # Arrange
    with pytest.raises(DependenciaRegistroError) as error:
        # Act
        repositorio.eliminar_registros_tabla("operadores", [1001], "admin")

    # Assert
    assert "2 eventos" in str(error.value)
    assert "1 comportamientos" in str(error.value)
    assert "depurar los registros hijos" in str(error.value)
    assert _total(motor_sqlite, TABLA_PERSONA) == 3
    assert _auditoria(motor_sqlite) == []


def test_eliminar_operador_sin_dependencias_permite(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02/S-01: un operador sin hijos sí puede eliminarse y se audita."""
    # Act
    afectados = repositorio.eliminar_registros_tabla("operadores", [1003], "admin")

    # Assert
    assert afectados == 1
    assert _total(motor_sqlite, TABLA_PERSONA) == 2
    assert _auditoria(motor_sqlite) == [("Eliminar Operadores", "IDs: 1003")]


# --- Spec 017: edición segura de celdas (S-02, S-03, S-04, S-05) ------------
def test_actualizar_registros_seguros_cambia_estado(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-04: el editor cambia el estado y audita con la tabla."""
    # Arrange
    cambio = CambioRegistro(1, ETIQUETA_ESTADO, OPCION_ANULADO)

    # Act
    afectados = repositorio.actualizar_registros_seguros("licencias", [cambio], "admin")

    # Assert
    assert afectados == 1
    assert _vigencia_de(motor_sqlite, "fact_licencias", "id_hecho_licencia", 1) == VIGENCIA_ANULADA
    assert _auditoria(motor_sqlite) == [
        (f"{ACCION_EDITAR_TABLA} Licencias", "IDs: 1; Columnas: Estado")
    ]


def test_actualizar_registros_seguros_reasigna_codigo_valido(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: reasignar un código existente se aplica y audita."""
    # Arrange
    cambio = CambioRegistro(1, "Código", 5002)

    # Act
    afectados = repositorio.actualizar_registros_seguros("comportamientos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        codigo = conexion.execute(
            text("SELECT id_codigo FROM fact_comportamiento WHERE id_hecho_comportamiento = 1")
        ).scalar_one()
    assert int(codigo) == 5002
    assert _auditoria(motor_sqlite) == [
        (f"{ACCION_EDITAR_TABLA} Comportamientos", "IDs: 1; Columnas: Código")
    ]


def test_actualizar_registros_seguros_codigo_inexistente_cancela(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03/S-02: reasignar un código inexistente cancela la edición."""
    # Arrange
    cambio = CambioRegistro(1, "Código", 9999)

    # Act
    with pytest.raises(CodigoInexistenteError):
        repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert _auditoria(motor_sqlite) == []


def test_actualizar_registros_seguros_columna_protegida_lanza(
    repositorio: EventosRepository,
) -> None:
    """CA-01/S-03: editar una columna de solo lectura está prohibido."""
    # Arrange
    cambio = CambioRegistro(1, "Nombre", "Intruso")

    # Act / Assert
    with pytest.raises(ColumnaProtegidaError):
        repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")


def test_actualizar_registros_seguros_rollback_atomico(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-04/S-05: un error revierte por completo la transacción (sin auditoría)."""
    # Arrange
    cambios = [
        CambioRegistro(1, ETIQUETA_ESTADO, OPCION_ANULADO),
        CambioRegistro(2, "Código", 9999),
    ]

    # Act
    with pytest.raises(CodigoInexistenteError):
        repositorio.actualizar_registros_seguros("eventos", cambios, "admin")

    # Assert: el primer cambio válido también se revirtió
    assert (
        _vigencia_de(motor_sqlite, "fact_eventos_operador", "id_hecho_evento", 1) == VIGENCIA_ACTIVA
    )
    assert _auditoria(motor_sqlite) == []


def test_actualizar_registros_seguros_cambia_evento_por_nombre(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """S-04: la lista de eventos se resuelve por nombre contra ``dim_tipo_evento``."""
    # Arrange
    cambio = CambioRegistro(1, "Evento", "Cancelación")

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        tipo = conexion.execute(
            text("SELECT id_tipo_evento FROM fact_eventos_operador WHERE id_hecho_evento = 1")
        ).scalar_one()
    assert int(tipo) == 7


def test_actualizar_registros_seguros_genero_invalido_lanza(
    repositorio: EventosRepository,
) -> None:
    """S-04: un género fuera de la lista permitida se rechaza."""
    # Arrange
    cambio = CambioRegistro(1001, "Género", "X")

    # Act / Assert
    with pytest.raises(ValorInvalidoError):
        repositorio.actualizar_registros_seguros("operadores", [cambio], "admin")


# --- Spec 019: persistencia de las columnas de negocio de eventos -----------
def test_actualizar_registros_seguros_cambia_fecha_certificado(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02: la fecha de certificado se edita y persiste en la tabla de eventos."""
    # Arrange
    cambio = CambioRegistro(1, "Fecha Certificado", "2026-03-01")

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        fecha = conexion.execute(
            text("SELECT fecha_certificado FROM fact_eventos_operador WHERE id_hecho_evento = 1")
        ).scalar_one()
    assert str(fecha) == "2026-03-01"


def test_actualizar_registros_seguros_cambia_fecha_retiro_y_notificacion(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02: las fechas de retiro y notificación de retiro se editan y persisten."""
    # Arrange
    cambios = [
        CambioRegistro(4, "Fecha Retiro", "2026-04-01"),
        CambioRegistro(4, "Fecha Notif. Retiro", "2026-03-30"),
    ]

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", cambios, "admin")

    # Assert
    assert afectados == 2
    with motor_sqlite.connect() as conexion:
        fila = conexion.execute(
            text(
                "SELECT fecha_retiro, fecha_notificacion_retiro FROM fact_eventos_operador "
                "WHERE id_hecho_evento = 4"
            )
        ).one()
    assert str(fila[0]) == "2026-04-01"
    assert str(fila[1]) == "2026-03-30"


def test_actualizar_registros_seguros_cambia_evaluador_vehiculo_y_observacion(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02: evaluador, vehículo evaluado y observación se editan y persisten."""
    # Arrange
    cambios = [
        CambioRegistro(2, "Evaluador", "Pedro Ramírez"),
        CambioRegistro(2, "Vehículo Evaluado", "7"),
        CambioRegistro(2, "Observación", "Motivo de retiro"),
    ]

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", cambios, "admin")

    # Assert
    assert afectados == 3
    with motor_sqlite.connect() as conexion:
        fila = conexion.execute(
            text(
                "SELECT evaluador, id_vehiculo_evaluado, observacion FROM fact_eventos_operador "
                "WHERE id_hecho_evento = 2"
            )
        ).one()
    assert str(fila[0]) == "Pedro Ramírez"
    assert int(fila[1]) == 7
    assert str(fila[2]) == "Motivo de retiro"


def test_actualizar_registros_seguros_cambia_fecha_prueba(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02/S-01: la fecha de prueba (permitida en certificación) se edita y persiste."""
    # Arrange
    cambio = CambioRegistro(3, "Fecha Prueba", "2026-05-08")

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        fecha = conexion.execute(
            text("SELECT fecha_prueba FROM fact_eventos_operador WHERE id_hecho_evento = 3")
        ).scalar_one()
    assert str(fecha) == "2026-05-08"


# --- Spec 020: compatibilidad de campos por categoría de evento --------------
def test_matriz_campos_permitidos_por_evento_define_las_categorias() -> None:
    """CA-01/S-01: la matriz declara las categorías con sus campos permitidos."""
    # Arrange
    base = {"id_codigo", "id_tipo_evento", "observacion"}
    acreditacion = base | {
        "fecha_certificado",
        "fecha_prueba",
        "evaluador",
        "id_vehiculo_evaluado",
    }

    # Act / Assert
    assert set(CAMPOS_PERMITIDOS_POR_EVENTO) == {
        TIPO_EVENTO_CERTIFICACION,
        TIPO_EVENTO_REACTIVACION,
        TIPO_EVENTO_RENOVACION,
        TIPO_EVENTO_CANCELACION,
        TIPO_EVENTO_SUSPENSION,
        TIPO_EVENTO_RESTRICCION_MEDICA,
        TIPO_EVENTO_OBSERVACION,
    }
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_CERTIFICACION] == acreditacion
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_REACTIVACION] == acreditacion
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_RENOVACION] == acreditacion
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_CANCELACION] == base | {
        "fecha_retiro",
        "fecha_notificacion_retiro",
    }
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_SUSPENSION] == base | {"fecha_suspension"}
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_RESTRICCION_MEDICA] == base
    assert CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_OBSERVACION] == base


def test_campos_permitidos_evento_categoria_desconocida_es_restrictiva() -> None:
    """CA-01/S-01: una categoría no listada usa el conjunto más restrictivo."""
    # Act / Assert
    assert campos_permitidos_evento(99) == CAMPOS_EVENTO_POR_DEFECTO
    assert (
        campos_permitidos_evento(TIPO_EVENTO_CANCELACION)
        == (CAMPOS_PERMITIDOS_POR_EVENTO[TIPO_EVENTO_CANCELACION])
    )


@pytest.mark.parametrize(
    ("id_evento", "etiqueta", "valor"),
    [
        (1, "Fecha Retiro", "2026-04-01"),
        (1, "Fecha Notif. Retiro", "2026-03-30"),
        (1, "Fecha Suspensión", "2026-05-10"),
        (3, "Fecha Retiro", "2026-04-01"),
        (2, "Fecha Retiro", "2026-04-01"),
        (2, "Fecha Notif. Retiro", "2026-03-30"),
        (2, "Fecha Suspensión", "2026-05-10"),
        (4, "Fecha Certificado", "2026-04-01"),
        (4, "Fecha Prueba", "2026-04-01"),
        (4, "Fecha Suspensión", "2026-05-10"),
        (4, "Evaluador", "Intruso"),
        (4, "Vehículo Evaluado", 9),
    ],
)
def test_actualizar_registros_seguros_rechaza_campos_incompatibles(
    repositorio: EventosRepository,
    motor_sqlite: Engine,
    id_evento: int,
    etiqueta: str,
    valor: object,
) -> None:
    """CA-02/S-02: cada campo prohibido por la matriz se rechaza con rollback atómico."""
    # Arrange
    columna = _columna_fisica(etiqueta)
    original = _celda(motor_sqlite, id_evento, columna)
    cambio = CambioRegistro(id_evento, etiqueta, valor)

    # Act
    with pytest.raises(CampoIncompatibleError) as error:
        repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert: mensaje descriptivo, dato intacto y sin auditoría (rollback)
    assert etiqueta in str(error.value)
    assert MENSAJE_CAMPO_INCOMPATIBLE.split("«")[0].strip() in str(error.value)
    assert _celda(motor_sqlite, id_evento, columna) == original
    assert _auditoria(motor_sqlite) == []


def test_actualizar_registros_seguros_permite_nulo_en_campo_prohibido(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """S-02: asignar nulo a un campo prohibido no cuenta como valor incompatible."""
    # Arrange: el evento 1 (certificación) tiene fecha_retiro en NULL
    cambio = CambioRegistro(1, "Fecha Retiro", None)

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert afectados == 1
    assert _celda(motor_sqlite, 1, "fecha_retiro") is None


def test_actualizar_registros_seguros_limpia_campos_al_cambiar_tipo(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03/S-03: cambiar a cancelación limpia los campos exclusivos de certificación."""
    # Arrange
    cambio = CambioRegistro(1, "Evento", "Cancelación")

    # Act
    afectados = repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        fila = conexion.execute(
            text(
                "SELECT id_tipo_evento, fecha_certificado, fecha_prueba, evaluador, "
                "id_vehiculo_evaluado, observacion FROM fact_eventos_operador "
                "WHERE id_hecho_evento = 1"
            )
        ).one()
    assert int(fila[0]) == TIPO_EVENTO_CANCELACION
    assert fila[1] is None
    assert fila[2] is None
    assert fila[3] is None
    assert fila[4] is None
    assert str(fila[5]) == "Certificado inicial"
    assert _auditoria(motor_sqlite) == [
        (f"{ACCION_EDITAR_TABLA} Eventos", "IDs: 1; Columnas: Evento")
    ]


@pytest.mark.parametrize(
    ("etiqueta", "valor"),
    [
        ("Fecha Certificado", "2030-01-01"),
        ("Fecha Certificado", "2026/01/08"),
        ("Fecha Prueba", "2026-13-40"),
    ],
)
def test_actualizar_registros_seguros_rechaza_fechas_invalidas(
    repositorio: EventosRepository,
    motor_sqlite: Engine,
    etiqueta: str,
    valor: str,
) -> None:
    """CA-04/S-04: una fecha futura lejana o con formato inválido se rechaza."""
    # Arrange
    cambio = CambioRegistro(1, etiqueta, valor)

    # Act
    with pytest.raises(ValorInvalidoError):
        repositorio.actualizar_registros_seguros("eventos", [cambio], "admin")

    # Assert
    assert _auditoria(motor_sqlite) == []


# --- Spec 018: listas oficiales de licencias y comportamientos --------------
def test_actualizar_registros_seguros_licencia_valida_normaliza(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-02: una licencia oficial se normaliza a mayúsculas y se guarda."""
    # Arrange
    cambio = CambioRegistro(1, "Tipo", "c1")

    # Act
    afectados = repositorio.actualizar_registros_seguros("licencias", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        tipo = conexion.execute(
            text("SELECT tipo FROM fact_licencias WHERE id_hecho_licencia = 1")
        ).scalar_one()
    assert str(tipo) == "C1"


def test_actualizar_registros_seguros_licencia_invalida_lanza(
    repositorio: EventosRepository,
) -> None:
    """CA-02: una licencia fuera de ``C1``/``C2``/``C3`` se rechaza."""
    # Arrange
    cambio = CambioRegistro(1, "Tipo", "C4")

    # Act / Assert
    with pytest.raises(ValorInvalidoError):
        repositorio.actualizar_registros_seguros("licencias", [cambio], "admin")


def test_actualizar_registros_seguros_fuente_valida(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: una fuente del catálogo se guarda en el comportamiento."""
    # Arrange
    cambio = CambioRegistro(1, "Fuente", "Operativo")

    # Act
    afectados = repositorio.actualizar_registros_seguros("comportamientos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        fuente = conexion.execute(
            text("SELECT fuente FROM fact_comportamiento WHERE id_hecho_comportamiento = 1")
        ).scalar_one()
    assert str(fuente) == "Operativo"


def test_actualizar_registros_seguros_fuente_invalida_lanza(
    repositorio: EventosRepository,
) -> None:
    """CA-03: una fuente fuera del catálogo se rechaza."""
    # Arrange
    cambio = CambioRegistro(1, "Fuente", "Fuente inexistente")

    # Act / Assert
    with pytest.raises(ValorInvalidoError):
        repositorio.actualizar_registros_seguros("comportamientos", [cambio], "admin")


def test_actualizar_registros_seguros_descripcion_valida(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: una descripción del catálogo se guarda en el comportamiento."""
    # Arrange
    cambio = CambioRegistro(1, "Descripción", "Alta sin cinturón")

    # Act
    afectados = repositorio.actualizar_registros_seguros("comportamientos", [cambio], "admin")

    # Assert
    assert afectados == 1
    with motor_sqlite.connect() as conexion:
        descripcion = conexion.execute(
            text(
                "SELECT descripcion_comportamiento FROM fact_comportamiento "
                "WHERE id_hecho_comportamiento = 1"
            )
        ).scalar_one()
    assert str(descripcion) == "Alta sin cinturón"


def test_actualizar_registros_seguros_descripcion_invalida_lanza(
    repositorio: EventosRepository,
) -> None:
    """CA-03: una descripción fuera del catálogo se rechaza."""
    # Arrange
    cambio = CambioRegistro(1, "Descripción", "Descripción inexistente")

    # Act / Assert
    with pytest.raises(ValorInvalidoError):
        repositorio.actualizar_registros_seguros("comportamientos", [cambio], "admin")


def test_actualizar_registros_seguros_sin_cambios_no_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: una lista de cambios vacía no ejecuta SQL ni audita."""
    # Arrange / Act
    afectados = repositorio.actualizar_registros_seguros("eventos", [], "admin")

    # Assert
    assert afectados == 0
    assert _auditoria(motor_sqlite) == []


# --- UI: funciones puras -----------------------------------------------------
def test_filas_editor_mapea_estado_en_minusculas() -> None:
    """CA-01: el editor expone la columna ID, las visibles y el estado restringido."""
    # Arrange
    registro = RegistroInfo(
        id_registro=2,
        id_vigencia=VIGENCIA_ANULADA,
        datos={
            "Código": 5002,
            "Cédula": 1002,
            "Nombre": "Luis Rojas",
            "Tipo": "C2",
            "Vencimiento": "2031-01-01",
        },
    )

    # Act
    filas = ui.filas_editor(_definicion("licencias"), [registro])

    # Assert
    assert filas == [
        {
            "ID": 2,
            "Código": 5002,
            "Cédula": 1002,
            "Nombre": "Luis Rojas",
            "Tipo": "C2",
            "Vencimiento": "2031-01-01",
            "Estado": "anulado",
        }
    ]


def test_columnas_protegidas_marca_solo_lectura() -> None:
    """CA-01/S-03: la cédula, el nombre y el ID quedan de solo lectura."""
    # Arrange / Act
    protegidas = ui.columnas_protegidas(_definicion("licencias"))

    # Assert
    assert "ID" in protegidas
    assert "Cédula" in protegidas
    assert "Nombre" in protegidas
    assert "Código" not in protegidas
    assert "Vencimiento" not in protegidas
    assert ETIQUETA_ESTADO not in protegidas


def test_configuracion_columnas_expone_las_listas_desplegables() -> None:
    """CA-01/S-04: estado y género usan ``SelectboxColumn`` con opciones fijas."""
    # Arrange
    definicion = _definicion("operadores")

    # Act
    config = ui.configuracion_columnas(definicion, ["Certificación", "Cancelación"])

    # Assert
    assert config[ETIQUETA_ESTADO]["type_config"]["type"] == "selectbox"
    assert list(config[ETIQUETA_ESTADO]["type_config"]["options"]) == [
        OPCION_VIGENTE,
        OPCION_ANULADO,
    ]
    assert list(config["Género"]["type_config"]["options"]) == list(GENEROS_VALIDOS)


def test_configuracion_columnas_evento_usa_el_catalogo() -> None:
    """CA-01/S-04: la columna de evento ofrece los tipos de ``dim_tipo_evento``."""
    # Arrange / Act
    config = ui.configuracion_columnas(_definicion("eventos"), ["Certificación", "Cancelación"])

    # Assert
    assert "Evento" in config
    assert list(config["Evento"]["type_config"]["options"]) == ["Certificación", "Cancelación"]


def test_detectar_cambios_extrae_las_celdas_modificadas() -> None:
    """CA-01: solo las celdas editables modificadas producen cambios."""
    # Arrange
    original: list[dict[str, object]] = [
        {"ID": 1, "Código": 5001, "Nombre": "Ana", "Tipo": "C3", ETIQUETA_ESTADO: OPCION_VIGENTE}
    ]
    editado: list[dict[str, object]] = [
        {"ID": 1, "Código": 5002, "Nombre": "Otra", "Tipo": "C3", ETIQUETA_ESTADO: OPCION_ANULADO}
    ]

    # Act
    cambios = ui.detectar_cambios(_definicion("licencias"), original, editado)

    # Assert
    assert CambioRegistro(1, "Código", 5002) in cambios
    assert CambioRegistro(1, ETIQUETA_ESTADO, OPCION_ANULADO) in cambios
    assert all(cambio.etiqueta != "Nombre" for cambio in cambios)


def test_detectar_cambios_sin_diferencias_devuelve_vacio() -> None:
    """CA-01: sin diferencias no hay cambios que guardar."""
    # Arrange
    original: list[dict[str, object]] = [{"ID": 1, "Código": 5001, ETIQUETA_ESTADO: OPCION_VIGENTE}]
    editado: list[dict[str, object]] = [{"ID": 1, "Código": 5001, ETIQUETA_ESTADO: OPCION_VIGENTE}]

    # Act / Assert
    assert ui.detectar_cambios(_definicion("eventos"), original, editado) == []


def test_ids_eliminados_detecta_filas_removidas() -> None:
    """CA-02: las filas ausentes del editor se reportan como eliminadas."""
    # Arrange
    original: list[dict[str, object]] = [{"ID": 1}, {"ID": 2}, {"ID": 3}]
    editado: list[dict[str, object]] = [{"ID": 2}]

    # Act / Assert
    assert ui.ids_eliminados(original, editado) == [1, 3]


def test_opciones_evento_elimina_duplicados() -> None:
    """Las opciones de evento conservan el orden y descartan repetidos."""
    # Arrange / Act / Assert
    assert ui.opciones_evento(["Certificación", "Cancelación", "Certificación"]) == [
        "Certificación",
        "Cancelación",
    ]


def test_puede_eliminar_solo_super_admin() -> None:
    """Solo el rol Super Administrador puede eliminar registros."""
    # Arrange / Act / Assert
    assert ui.puede_eliminar(ROL_SUPER_ADMINISTRADOR) is True
    assert ui.puede_eliminar(ROL_ADMINISTRADOR) is False


# --- UI (spec 018): búsqueda rápida y listas oficiales ----------------------
def test_filtrar_filas_por_termino_insensible_a_mayusculas() -> None:
    """CA-01: la búsqueda rápida filtra por cualquier celda y sin distinguir mayúsculas."""
    # Arrange
    filas: list[dict[str, object]] = [
        {"ID": 1, "Código": 5001, "Nombre": "Ana", ETIQUETA_ESTADO: OPCION_VIGENTE},
        {"ID": 2, "Código": 5002, "Nombre": "Luis", ETIQUETA_ESTADO: OPCION_ANULADO},
    ]

    # Act / Assert
    assert ui.filtrar_filas(filas, "ana") == [filas[0]]
    assert ui.filtrar_filas(filas, "5002") == [filas[1]]
    assert ui.filtrar_filas(filas, "").__len__() == 2
    assert ui.filtrar_filas(filas, "zzz") == []


def test_filas_con_seleccion_anexa_casilla_desmarcada() -> None:
    """CA-05: cada fila del editor incorpora la casilla ``Seleccionar`` en falso."""
    # Arrange
    filas: list[dict[str, object]] = [{"ID": 7, "Código": 5001}]

    # Act
    resultado = ui.filas_con_seleccion(filas)

    # Assert
    assert resultado == [{"Seleccionar": False, "ID": 7, "Código": 5001}]


def test_ids_seleccionados_toma_solo_las_filas_marcadas() -> None:
    """CA-05: solo las filas con la casilla marcada e ID válido se devuelven."""
    # Arrange
    filas: list[dict[str, object]] = [
        {"Seleccionar": True, "ID": 1},
        {"Seleccionar": False, "ID": 2},
        {"Seleccionar": True, "ID": 3},
        {"Seleccionar": True, "ID": None},
    ]

    # Act / Assert
    assert ui.ids_seleccionados(filas) == [1, 3]


def test_configuracion_columnas_licencias_usa_opciones_oficiales() -> None:
    """CA-02: la columna ``Tipo`` de licencias es un desplegable ``C1``/``C2``/``C3``."""
    # Arrange / Act
    config = ui.configuracion_columnas(_definicion("licencias"), [])

    # Assert
    assert config["Tipo"]["type_config"]["type"] == "selectbox"
    assert list(config["Tipo"]["type_config"]["options"]) == list(OPCIONES_LICENCIA)


def test_configuracion_columnas_comportamientos_usa_catalogos() -> None:
    """CA-03: ``Fuente`` y ``Descripción`` son desplegables con las opciones recibidas."""
    # Arrange / Act
    config = ui.configuracion_columnas(
        _definicion("comportamientos"),
        [],
        ["Operativo", "PQRS"],
        ["Alta sin cinturón"],
    )

    # Assert
    assert list(config["Fuente"]["type_config"]["options"]) == ["Operativo", "PQRS"]
    assert list(config["Descripción"]["type_config"]["options"]) == ["Alta sin cinturón"]


def test_configuracion_columnas_incluye_la_casilla_de_seleccion() -> None:
    """CA-05: el editor ofrece la casilla ``Seleccionar`` para las acciones en bloque."""
    # Arrange / Act
    config = ui.configuracion_columnas(_definicion("codigos"), [])

    # Assert
    assert ui.ETIQUETA_SELECCION in config
    assert config[ui.ETIQUETA_SELECCION]["type_config"]["type"] == "checkbox"


# --- UI (spec 019): columnas de negocio del editor de eventos ---------------
def test_columnas_protegidas_eventos_deja_las_identificaciones_solo_lectura() -> None:
    """CA-01/S-03: cédula, nombre y registro quedan protegidos; las de negocio no."""
    # Arrange / Act
    protegidas = ui.columnas_protegidas(_definicion("eventos"))

    # Assert
    assert {"ID", "Cédula", "Nombre", "Registro"}.issubset(set(protegidas))
    for etiqueta in (
        "Fecha Certificado",
        "Fecha Retiro",
        "Fecha Notif. Retiro",
        "Fecha Suspensión",
        "Fecha Prueba",
        "Evaluador",
        "Vehículo Evaluado",
        "Observación",
    ):
        assert etiqueta not in protegidas


def test_configuracion_columnas_eventos_configura_las_columnas_de_negocio() -> None:
    """CA-02: el editor expone editables las fechas, evaluador, vehículo y observación."""
    # Arrange / Act
    config = ui.configuracion_columnas(_definicion("eventos"), ["Certificación"])

    # Assert
    for etiqueta in (
        "Fecha Certificado",
        "Fecha Retiro",
        "Fecha Notif. Retiro",
        "Fecha Suspensión",
        "Fecha Prueba",
        "Evaluador",
        "Observación",
    ):
        assert config[etiqueta]["type_config"]["type"] == "text"
    assert config["Vehículo Evaluado"]["type_config"]["type"] == "number"


# --- UI (spec 020): proyección de columnas por tipo de evento ---------------
def test_columnas_por_tipo_evento_proyecta_solo_las_aplicables() -> None:
    """CA-04/S-05: al filtrar por cancelación solo quedan las columnas aplicables."""
    # Arrange
    definicion = _definicion("eventos")

    # Act
    proyectada = ui.columnas_por_tipo_evento(definicion, TIPO_EVENTO_CANCELACION)

    # Assert
    assert [columna.etiqueta for columna in proyectada.columnas] == [
        "Código",
        "Cédula",
        "Nombre",
        "Evento",
        "Fecha Retiro",
        "Fecha Notif. Retiro",
        "Observación",
        "Registro",
    ]
    assert [columna.etiqueta for columna in proyectada.editables] == [
        "Código",
        "Evento",
        "Fecha Retiro",
        "Fecha Notif. Retiro",
        "Observación",
    ]


def test_columnas_por_tipo_evento_todos_conserva_todas() -> None:
    """CA-04/S-05: con «Todos» (id nulo) se conserva la definición completa."""
    # Arrange
    definicion = _definicion("eventos")

    # Act / Assert
    assert ui.columnas_por_tipo_evento(definicion, None) is definicion


def test_id_tipo_evento_por_nombre_resuelve_el_catalogo() -> None:
    """CA-04/S-05: el nombre seleccionado se traduce al identificador del catálogo."""
    # Arrange
    tipos = [TipoEventoInfo(1, "Certificación"), TipoEventoInfo(7, "Cancelación")]

    # Act / Assert
    assert ui.id_tipo_evento_por_nombre(tipos, "Cancelación") == 7
    assert ui.id_tipo_evento_por_nombre(tipos, "Inexistente") is None


def test_filas_por_tipo_evento_filtra_por_nombre() -> None:
    """CA-04/S-05: solo permanecen las filas del tipo seleccionado."""
    # Arrange
    filas: list[dict[str, object]] = [
        {"ID": 1, ETIQUETA_EVENTO: "Certificación"},
        {"ID": 2, ETIQUETA_EVENTO: "Cancelación"},
    ]

    # Act / Assert
    assert ui.filas_por_tipo_evento(filas, "Cancelación") == [filas[1]]
    assert ui.filas_por_tipo_evento(filas, "") == filas


def test_ui_adapta_columnas_por_tipo_evento_de_la_spec_020() -> None:
    """CA-04/S-05: la UI proyecta columnas por tipo y captura el error de compatibilidad."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "columnas_por_tipo_evento(" in contenido
    assert "st.selectbox(" in contenido
    assert "CampoIncompatibleError" in contenido
    assert "MENSAJE_RESTRICCIONES_EVENTO" in contenido
    assert "columnas aplicables" in contenido


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_correccion_registros_existe() -> None:
    """CA-01: el paquete expone ``render_correccion_registros``."""
    # Arrange / Act
    from certificado_operadores.modulos.correccion_registros import (
        render_correccion_registros,
    )

    # Assert
    assert callable(render_correccion_registros)


def test_repositorio_expone_los_metodos_de_seguridad() -> None:
    """CA-02/CA-03: el repositorio expone las validaciones de la spec 017."""
    # Arrange / Act / Assert
    for nombre in (
        "contar_dependencias_operador",
        "validar_codigo_existe",
        "actualizar_registros_seguros",
    ):
        assert callable(getattr(EventosRepository, nombre))


def test_ui_organiza_la_correccion_en_subtabs_por_tabla() -> None:
    """CA-01: la UI construye las sub-pestañas a partir del catálogo de tablas."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "st.tabs(" in contenido
    assert "for definicion in TABLAS_CORRECCION" in contenido
    claves = {definicion.clave for definicion in TABLAS_CORRECCION}
    etiquetas = {definicion.etiqueta for definicion in TABLAS_CORRECCION}
    assert claves == set(CLAVES_TABLAS)
    assert etiquetas == set(ETIQUETAS_TABLAS)


def test_ui_usa_editor_tipo_excel_con_columnas_protegidas() -> None:
    """CA-01: la UI usa ``st.data_editor`` con listas y columnas protegidas."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "st.data_editor(" in contenido
    assert "st.column_config.SelectboxColumn(" in contenido
    assert "st.column_config.CheckboxColumn(" in contenido
    assert "disabled=" in contenido
    assert 'num_rows="dynamic"' in contenido
    assert 'width="stretch"' in contenido


def test_ui_expone_buscador_rapido_por_tabla() -> None:
    """CA-01: cada tabla incluye la barra de búsqueda rápida ``🔍 Filtrar tabla``."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "st.text_input(" in contenido
    assert ui.ETIQUETA_FILTRO in contenido
    assert ui.PLACEHOLDER_FILTRO in contenido
    assert "filtrar_filas(" in contenido


def test_ui_expone_botones_de_accion_en_bloque() -> None:
    """CA-05: la UI ofrece los botones de acción en bloque y delega en el repositorio."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert ui.ETIQUETA_VIGENTE_BLOQUE in contenido
    assert ui.ETIQUETA_ANULADO_BLOQUE in contenido
    assert ui.ETIQUETA_ELIMINAR_BLOQUE in contenido
    assert "mutar_vigencia(" in contenido
    assert "ids_seleccionados(" in contenido


def test_ui_expone_el_boton_de_guardado_y_delega_en_el_repositorio() -> None:
    """CA-04: la UI ofrece Guardar Cambios y delega en el repositorio."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert ui.ETIQUETA_GUARDAR in contenido
    assert "actualizar_registros_seguros(" in contenido
    assert "eliminar_registros_tabla(" in contenido
    assert "contar_dependencias_operador(" not in contenido


def test_ui_no_contiene_sql_ni_acceso_directo() -> None:
    """CA-02/RNF-01: la UI no contiene SQL ni acceso directo a la base de datos."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8").upper()
    patron = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")
    acceso_directo = ("RUN_QUERY", "RUN_TRANSACTION")

    # Act
    sentencias = patron.findall(contenido)
    directos = [palabra for palabra in acceso_directo if palabra in contenido]

    # Assert
    assert sentencias == []
    assert directos == []


def test_pagina_usa_render_correccion_registros_sin_funciones_inlined() -> None:
    """CA-02: la página importa la función y no contiene la corrección inlined."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_correccion_registros" in contenido
    assert "def correccion_individual" not in contenido
    assert "def correccion_lote" not in contenido
    assert "run_query" not in contenido
    assert "run_transaction" not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")


def test_modulo_heredado_deprecado_sin_sql() -> None:
    """El módulo heredado quedó eliminado o deprecado sin SQL."""
    # Arrange / Act / Assert
    if not _RUTA_HEREDADO.exists():
        assert not _RUTA_HEREDADO.exists()
        return

    contenido = _RUTA_HEREDADO.read_text(encoding="utf-8").upper()
    patron = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")

    assert "RENDER_CORRECCION_REGISTROS" in contenido
    assert patron.findall(contenido) == []
