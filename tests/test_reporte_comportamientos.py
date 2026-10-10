"""Pruebas del reporte de comportamientos (spec 009).

Cubren tres frentes: el repositorio ``ComportamientosRepository`` contra una base
SQLite temporal (búsqueda de operador, registro individual y masivo, reincidencia
y acciones de historial), las funciones puras de la UI (limpieza de celdas y
plantillas Excel) y las verificaciones estáticas de los criterios de aceptación:
el paquete existe, la UI y la página no contienen SQL y la página usa
``render_reporte_comportamientos`` sin ``exec``. Todas las pruebas siguen el
patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import io
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from certificado_operadores.infra.comportamientos_repository import (
    ACCION_CARGA_MASIVA_COMPORTAMIENTOS,
    ACCION_DETERMINAR_REINCIDENCIA,
    ACCION_IMPORTAR_ACCIONES_REINCIDENCIA,
    ACCION_REGISTRAR_ACCION_REINCIDENCIA,
    ACCION_REGISTRO_COMPORTAMIENTO,
    AccionReincidencia,
    ComportamientosRepository,
    DatosComportamiento,
    OperadorComportamientoInfo,
)
from certificado_operadores.modulos.reporte_comportamientos import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "2_Administracion_Operadores.py"

_HOY = date.today()
_FECHA_RECIENTE = (_HOY - timedelta(days=2)).isoformat()
_FECHA_RECIENTE_2 = (_HOY - timedelta(days=1)).isoformat()
_FECHA_ANTIGUA = (_HOY - timedelta(days=300)).isoformat()

# --- Esquema mínimo para las pruebas del repositorio ------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_persona (
        id_persona INTEGER PRIMARY KEY,
        nombres TEXT,
        primer_apellido TEXT
    );
    """,
    """
    CREATE TABLE dim_empresa (
        id_empresa INTEGER PRIMARY KEY,
        nombre_empresa TEXT
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY,
        id_persona INTEGER NOT NULL,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT,
        id_empresa INTEGER
    );
    """,
    """
    CREATE TABLE dim_impacto (
        id_impacto INTEGER PRIMARY KEY,
        impacto TEXT,
        maximo INTEGER,
        dias_maximo INTEGER
    );
    """,
    """
    CREATE TABLE dim_comportamiento (
        id_comportamiento INTEGER PRIMARY KEY,
        comportamiento TEXT,
        id_impacto INTEGER
    );
    """,
    """
    CREATE TABLE dim_detalle_comportamiento (
        id_jerarquia INTEGER PRIMARY KEY,
        descripcion_comportamiento TEXT,
        id_comportamiento INTEGER
    );
    """,
    """
    CREATE TABLE fact_comportamiento (
        id_hecho_comportamiento INTEGER PRIMARY KEY,
        id_jerarquia INTEGER,
        id_codigo INTEGER,
        fecha_evento TEXT,
        hora_evento TEXT,
        nota TEXT,
        vehiculo INTEGER,
        viaje INTEGER,
        tarea INTEGER,
        caso_bitacora_ticket TEXT,
        ruta TEXT,
        sitio_salida TEXT,
        sitio_novedad TEXT,
        numero_lesionados INTEGER,
        observacion_concesionario TEXT,
        respuesta_mc TEXT,
        responsable_pqrs_cot TEXT,
        direccion_infraccion TEXT,
        clase_servicio TEXT,
        tipo_servicio TEXT,
        fuente_infraccion TEXT,
        placa TEXT,
        id_vigencia INTEGER NOT NULL,
        usuario_registra TEXT,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE fact_reincidencia (
        id_reincidencia INTEGER PRIMARY KEY,
        id_impacto INTEGER,
        id_comportamiento INTEGER,
        id_codigo INTEGER,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        cantidad INTEGER,
        resumen TEXT,
        determinacion_mc TEXT,
        estado TEXT,
        id_hecho_evento INTEGER,
        usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE reincidencia_detalle (
        id_reincidencia INTEGER NOT NULL,
        id_hecho_comportamiento INTEGER NOT NULL
    );
    """,
    """
    CREATE TABLE fact_eventos_operador (
        id_hecho_evento INTEGER PRIMARY KEY,
        id_codigo INTEGER NOT NULL,
        id_tipo_evento INTEGER NOT NULL,
        fecha_observacion TEXT,
        observacion TEXT,
        id_vigencia INTEGER NOT NULL,
        usuario_registra TEXT,
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


def _crear_esquema(motor: Engine) -> None:
    """Crea las tablas mínimas del reporte de comportamientos.

    Args:
        motor: Motor SQLAlchemy donde se crea el esquema.
    """
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_catalogos(motor: Engine) -> None:
    """Inserta los catálogos y códigos de ejemplo (sin hechos de comportamiento).

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_persona VALUES (:id, :nombres, :apellido)"),
            [
                {"id": 1001, "nombres": "Ana", "apellido": "Pérez"},
                {"id": 1002, "nombres": "Luis", "apellido": "Rojas"},
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_empresa VALUES (:id, :nombre)"),
            [{"id": 1, "nombre": "Empresa A"}, {"id": 2, "nombre": "Empresa B"}],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_codigo (id_codigo, id_persona, id_vigencia, fecha_registro, "
                "id_empresa) VALUES (:id, :persona, :vigencia, :fecha, :empresa)"
            ),
            [
                {"id": 5001, "persona": 1001, "vigencia": 1, "fecha": "2026-01-01", "empresa": 1},
                {"id": 5002, "persona": 1002, "vigencia": 1, "fecha": "2026-01-02", "empresa": 2},
                {"id": 6000, "persona": 1001, "vigencia": 2, "fecha": "2026-01-03", "empresa": 1},
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_impacto VALUES (:id, :impacto, :maximo, :dias)"),
            [
                {"id": 1, "impacto": "Grave", "maximo": 1, "dias": 30},
                {"id": 2, "impacto": "Leve", "maximo": 2, "dias": 15},
                {"id": 3, "impacto": "Nulo", "maximo": 0, "dias": 0},
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_comportamiento VALUES (:id, :nombre, :impacto)"),
            [
                {"id": 10, "nombre": "Conducción temeraria", "impacto": 1},
                {"id": 20, "nombre": "Uso indebido", "impacto": 2},
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_detalle_comportamiento "
                "(id_jerarquia, descripcion_comportamiento, id_comportamiento) "
                "VALUES (:id, :descripcion, :comportamiento)"
            ),
            [
                {"id": 1, "descripcion": "Exceso de velocidad", "comportamiento": 10},
                {"id": 2, "descripcion": "Uso de celular", "comportamiento": 20},
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Engine:
    """Motor SQLite temporal con esquema y catálogos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_comportamientos.db'}")
    _crear_esquema(motor)
    _sembrar_catalogos(motor)
    return motor


@pytest.fixture
def repositorio(motor_sqlite: Engine) -> ComportamientosRepository:
    """Repositorio de comportamientos configurado con el motor SQLite de prueba."""
    return ComportamientosRepository(engine=motor_sqlite)


def _insertar_hecho(
    motor: Engine,
    identificador: int,
    id_jerarquia: int,
    id_codigo: int,
    fecha_evento: str,
    caso: str,
    hora: str = "08:00:00",
) -> None:
    """Inserta un hecho de comportamiento de ejemplo.

    Args:
        motor: Motor SQLAlchemy.
        identificador: Identificador del hecho.
        id_jerarquia: Jerarquía de comportamiento.
        id_codigo: Código del operador.
        fecha_evento: Fecha del evento en texto ISO.
        caso: Caso/bitácora/ticket.
        hora: Hora del evento.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO fact_comportamiento "
                "(id_hecho_comportamiento, id_jerarquia, id_codigo, fecha_evento, hora_evento, "
                "caso_bitacora_ticket, id_vigencia, usuario_registra, fecha_registro) "
                "VALUES (:id, :j, :cod, :f, :h, :caso, 1, 'admin', :f)"
            ),
            {
                "id": identificador,
                "j": id_jerarquia,
                "cod": id_codigo,
                "f": fecha_evento,
                "h": hora,
                "caso": caso,
            },
        )


def _insertar_evento(motor: Engine, identificador: int, id_codigo: int) -> None:
    """Inserta un evento de historial de ejemplo.

    Args:
        motor: Motor SQLAlchemy.
        identificador: Identificador del evento.
        id_codigo: Código del operador.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador "
                "(id_hecho_evento, id_codigo, id_tipo_evento, id_vigencia, usuario_registra) "
                "VALUES (:id, :cod, 8, 1, 'admin')"
            ),
            {"id": identificador, "cod": id_codigo},
        )


def _filas(motor: Engine, sentencia: str) -> list[tuple]:
    """Ejecuta una consulta de lectura y devuelve las filas como tuplas."""
    with motor.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(sentencia)).all()]


def _auditoria(motor: Engine) -> list[tuple[str, str]]:
    """Devuelve las acciones de auditoría registradas como pares (acción, detalle)."""
    return [
        (str(accion), str(detalles or ""))
        for accion, detalles in _filas(
            motor, "SELECT accion, detalles FROM log_auditoria ORDER BY id_log"
        )
    ]


# --- Repositorio: búsqueda del operador (RF-01) ------------------------------
def test_buscar_operador_por_codigo(repositorio: ComportamientosRepository) -> None:
    """RF-01: un código vigente devuelve el operador."""
    # Arrange / Act
    operador = repositorio.buscar_operador_por_codigo(5001)

    # Assert
    assert operador == OperadorComportamientoInfo(
        id_codigo=5001, cedula=1001, nombres="Ana", primer_apellido="Pérez"
    )
    assert operador is not None
    assert operador.nombre_completo() == "Ana Pérez"


def test_buscar_operador_por_codigo_inactivo(repositorio: ComportamientosRepository) -> None:
    """RF-01: un código con vigencia inactiva no se devuelve."""
    # Arrange / Act / Assert
    assert repositorio.buscar_operador_por_codigo(6000) is None


def test_buscar_operador_por_cedula_mas_reciente(repositorio: ComportamientosRepository) -> None:
    """RF-01: por cédula se devuelve el código activo más reciente."""
    # Arrange / Act
    operador = repositorio.buscar_operador_por_cedula(1001)

    # Assert
    assert operador is not None
    assert operador.id_codigo == 5001


def test_buscar_operador_por_cedula_inexistente(repositorio: ComportamientosRepository) -> None:
    """RF-01: una cédula sin operador no devuelve nada."""
    # Arrange / Act / Assert
    assert repositorio.buscar_operador_por_cedula(9999) is None


def test_listar_detalles_comportamiento_ordenados(repositorio: ComportamientosRepository) -> None:
    """RF-01: los detalles de comportamiento se listan por descripción."""
    # Arrange / Act
    detalles = repositorio.listar_detalles_comportamiento()

    # Assert
    assert [(detalle.id_jerarquia, detalle.descripcion) for detalle in detalles] == [
        (1, "Exceso de velocidad"),
        (2, "Uso de celular"),
    ]


# --- Repositorio: registro individual (RF-01 / CA-03) ------------------------
def test_registrar_comportamiento_inserta_y_audita(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-01/CA-03: el comportamiento se inserta y deja su auditoría."""
    # Arrange
    datos = DatosComportamiento(
        id_jerarquia=1,
        id_codigo=5001,
        fecha_evento=date(2026, 2, 1),
        hora_evento="10:30:00",
        caso_bitacora_ticket="1001",
        nota="Prueba",
        vehiculo=12,
        viaje=3,
        tarea=4,
        numero_lesionados=0,
    )

    # Act
    nuevo_id = repositorio.registrar_comportamiento(datos, "admin")

    # Assert
    assert nuevo_id == 1
    fila = _filas(
        motor_sqlite,
        "SELECT id_codigo, id_jerarquia, fecha_evento, hora_evento, vehiculo "
        "FROM fact_comportamiento WHERE id_hecho_comportamiento = 1",
    )[0]
    assert fila == (5001, 1, "2026-02-01", "10:30:00", 12)
    assert _auditoria(motor_sqlite) == [
        (ACCION_REGISTRO_COMPORTAMIENTO, "Codigo: 5001, Jerarquia: 1")
    ]


# --- Repositorio: carga masiva (RF-02 / CA-03) ------------------------------
def test_resolver_codigo_activo(repositorio: ComportamientosRepository) -> None:
    """RF-02: solo se resuelven códigos vigentes."""
    # Arrange / Act / Assert
    assert repositorio.resolver_codigo_activo(5001) == 5001
    assert repositorio.resolver_codigo_activo(6000) is None
    assert repositorio.resolver_codigo_activo(9999) is None


def test_resolver_jerarquia_por_descripcion(repositorio: ComportamientosRepository) -> None:
    """RF-02: la descripción exacta se traduce a su jerarquía."""
    # Arrange / Act / Assert
    assert repositorio.resolver_jerarquia_por_descripcion("Exceso de velocidad") == 1
    assert repositorio.resolver_jerarquia_por_descripcion("No existe") is None


def test_buscar_comportamiento_por_caso(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: un caso existente devuelve el comportamiento a actualizar."""
    # Arrange
    _insertar_hecho(motor_sqlite, 1, 1, 5001, _FECHA_RECIENTE, "1001")

    # Act / Assert
    assert repositorio.buscar_comportamiento_por_caso("1001") == 1
    assert repositorio.buscar_comportamiento_por_caso("9999") is None


def test_guardar_comportamientos_inserta_y_actualiza(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-02/CA-03: la carga masiva inserta nuevos y actualiza existentes."""
    # Arrange
    _insertar_hecho(motor_sqlite, 1, 1, 5001, _FECHA_RECIENTE, "1001")
    filas = [
        DatosComportamiento(
            id_jerarquia=1,
            id_codigo=5001,
            fecha_evento=date(2026, 3, 1),
            caso_bitacora_ticket="1001",
            nota="Actualizado",
            id_existente=1,
        ),
        DatosComportamiento(
            id_jerarquia=2,
            id_codigo=5002,
            fecha_evento=date(2026, 3, 2),
            caso_bitacora_ticket="2001",
            nota="Nuevo",
        ),
    ]

    # Act
    nuevos, actualizados = repositorio.guardar_comportamientos(filas, "admin")

    # Assert
    assert (nuevos, actualizados) == (1, 1)
    assert (
        _filas(
            motor_sqlite, "SELECT nota FROM fact_comportamiento WHERE id_hecho_comportamiento = 1"
        )[0][0]
        == "Actualizado"
    )
    assert (
        _filas(
            motor_sqlite, "SELECT nota FROM fact_comportamiento WHERE id_hecho_comportamiento = 2"
        )[0][0]
        == "Nuevo"
    )
    assert _auditoria(motor_sqlite) == [
        (ACCION_CARGA_MASIVA_COMPORTAMIENTOS, "Nuevos: 1, Actualizados: 1")
    ]


# --- Repositorio: reincidencia (RF-03 / CA-03) ------------------------------
def test_listar_impactos_excluye_maximo_cero(repositorio: ComportamientosRepository) -> None:
    """RF-03: solo se evalúan los impactos con máximo mayor que cero."""
    # Arrange / Act
    impactos = repositorio.listar_impactos()

    # Assert
    assert [impacto.id_impacto for impacto in impactos] == [1, 2]


def test_generar_reincidencias_grave_crea_un_caso_por_hecho(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: un impacto grave genera un caso por cada hecho pendiente."""
    # Arrange
    _insertar_hecho(motor_sqlite, 1, 1, 5001, _FECHA_RECIENTE, "1001")
    _insertar_hecho(motor_sqlite, 2, 1, 5001, _FECHA_RECIENTE_2, "1002")

    # Act
    nuevos = repositorio.generar_reincidencias("admin")

    # Assert
    assert nuevos == 2
    assert len(_filas(motor_sqlite, "SELECT id_reincidencia FROM fact_reincidencia")) == 2
    assert (
        len(_filas(motor_sqlite, "SELECT id_hecho_comportamiento FROM reincidencia_detalle")) == 2
    )
    cantidades = _filas(
        motor_sqlite, "SELECT cantidad FROM fact_reincidencia ORDER BY id_reincidencia"
    )
    assert cantidades == [(1,), (1,)]
    assert _filas(motor_sqlite, "SELECT DISTINCT usuario_registra FROM fact_reincidencia") == [
        ("admin",)
    ]


def test_generar_reincidencias_no_grave_crea_par(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: un impacto no grave empareja hechos dentro de la ventana de días."""
    # Arrange
    _insertar_hecho(motor_sqlite, 1, 2, 5002, _FECHA_RECIENTE, "2001")
    _insertar_hecho(motor_sqlite, 2, 2, 5002, _FECHA_RECIENTE_2, "2002")

    # Act
    nuevos = repositorio.generar_reincidencias()

    # Assert
    assert nuevos == 1
    fila = _filas(motor_sqlite, "SELECT cantidad, id_hecho_evento FROM fact_reincidencia")[0]
    assert fila[0] == 2
    assert sorted(
        valor[0]
        for valor in _filas(
            motor_sqlite, "SELECT id_hecho_comportamiento FROM reincidencia_detalle"
        )
    ) == [1, 2]


def test_generar_reincidencias_ignora_hechos_fuera_de_ventana(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: los hechos anteriores a la ventana no generan casos."""
    # Arrange
    _insertar_hecho(motor_sqlite, 1, 1, 5001, _FECHA_ANTIGUA, "1001")

    # Act
    nuevos = repositorio.generar_reincidencias()

    # Assert
    assert nuevos == 0
    assert _filas(motor_sqlite, "SELECT id_reincidencia FROM fact_reincidencia") == []


def test_listar_pares_reincidencia(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: los pares ya registrados se agrupan por caso."""
    # Arrange
    repositorio.registrar_reincidencia(
        id_impacto=2,
        id_comportamiento=20,
        id_codigo=5002,
        fecha_inicio=_HOY,
        fecha_fin=_HOY,
        cantidad=2,
        resumen="Par",
        usuario="admin",
        hechos=[5, 3],
    )

    # Act / Assert
    assert repositorio.listar_pares_reincidencia() == {(3, 5)}


def test_registrar_reincidencia_guarda_detalle(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: el caso y sus hechos se guardan en una sola operación."""
    # Arrange / Act
    nuevo_id = repositorio.registrar_reincidencia(
        id_impacto=1,
        id_comportamiento=10,
        id_codigo=5001,
        fecha_inicio=_HOY,
        fecha_fin=_HOY,
        cantidad=1,
        resumen="Caso: 1001",
        usuario="",
        hechos=[7],
    )

    # Assert
    assert nuevo_id == 1
    assert _filas(motor_sqlite, "SELECT id_hecho_evento FROM fact_reincidencia") == [(None,)]
    assert _filas(motor_sqlite, "SELECT id_hecho_comportamiento FROM reincidencia_detalle") == [
        (7,)
    ]


def test_actualizar_determinacion_audita(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: la determinación se actualiza y se audita."""
    # Arrange
    repositorio.registrar_reincidencia(1, 10, 5001, _HOY, _HOY, 1, "Caso", "", [1])

    # Act
    repositorio.actualizar_determinacion(1, "advertencia", "admin")

    # Assert
    assert _filas(
        motor_sqlite, "SELECT determinacion_mc FROM fact_reincidencia WHERE id_reincidencia = 1"
    ) == [("advertencia",)]
    assert _auditoria(motor_sqlite) == [
        (ACCION_DETERMINAR_REINCIDENCIA, "ID: 1, Decision: advertencia")
    ]


# --- Repositorio: acciones de historial (RF-03) -----------------------------
def test_registrar_accion_reincidencia_inserta_evento(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: una acción nueva se inserta en el historial y se vincula al caso."""
    # Arrange
    repositorio.registrar_reincidencia(1, 10, 5001, _HOY, _HOY, 1, "Caso", "", [1])
    accion = AccionReincidencia(
        id_reincidencia=1,
        id_codigo=5001,
        id_tipo_evento=8,
        fecha_observacion=date(2026, 5, 1),
        observacion="Advertencia por reincidencia",
    )

    # Act
    id_evento = repositorio.registrar_accion_reincidencia(accion, "admin")

    # Assert
    assert id_evento == 1
    assert _filas(
        motor_sqlite,
        "SELECT id_codigo, id_tipo_evento, fecha_observacion, observacion "
        "FROM fact_eventos_operador WHERE id_hecho_evento = 1",
    ) == [(5001, 8, "2026-05-01", "Advertencia por reincidencia")]
    assert _filas(
        motor_sqlite, "SELECT id_hecho_evento FROM fact_reincidencia WHERE id_reincidencia = 1"
    ) == [(1,)]
    assert _auditoria(motor_sqlite) == [
        (ACCION_REGISTRAR_ACCION_REINCIDENCIA, "Reinc #1, Cod: 5001, Tipo: 8")
    ]


def test_importar_acciones_reincidencia_actualiza_existente(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: la importación actualiza eventos existentes y audita una sola vez."""
    # Arrange
    repositorio.registrar_reincidencia(1, 10, 5001, _HOY, _HOY, 1, "Caso", "", [1])
    _insertar_evento(motor_sqlite, 9, 5001)
    accion = AccionReincidencia(
        id_reincidencia=1,
        id_codigo=5001,
        id_tipo_evento=6,
        fecha_observacion=date(2026, 6, 1),
        observacion="Suspensión importada",
        id_hecho_evento=9,
    )

    # Act
    insertados, actualizados = repositorio.importar_acciones_reincidencia([accion], "admin")

    # Assert
    assert (insertados, actualizados) == (0, 1)
    assert _filas(
        motor_sqlite,
        "SELECT id_tipo_evento, observacion FROM fact_eventos_operador WHERE id_hecho_evento = 9",
    ) == [(6, "Suspensión importada")]
    assert _auditoria(motor_sqlite) == [
        (ACCION_IMPORTAR_ACCIONES_REINCIDENCIA, "Nuevos: 0, Actualizados: 1")
    ]


def test_obtener_reincidencia_accion(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: se pueden consultar el código y el evento de un caso."""
    # Arrange
    repositorio.registrar_reincidencia(1, 10, 5001, _HOY, _HOY, 1, "Caso", "", [1])

    # Act / Assert
    datos = repositorio.obtener_reincidencia_accion(1)
    assert datos is not None
    assert datos.id_codigo == 5001
    assert datos.id_hecho_evento is None
    assert repositorio.obtener_reincidencia_accion(99) is None


# --- Repositorio: listados del reporte --------------------------------------
def test_listar_reincidencias_y_detalle(
    repositorio: ComportamientosRepository, motor_sqlite: Engine
) -> None:
    """RF-03: el listado de casos y su detalle reflejan los datos guardados."""
    # Arrange
    _insertar_hecho(motor_sqlite, 1, 1, 5001, _FECHA_RECIENTE, "1001")
    repositorio.registrar_reincidencia(1, 10, 5001, _HOY, _HOY, 1, "Caso", "admin", [1])

    # Act
    casos = repositorio.listar_reincidencias()
    detalle = repositorio.listar_detalle_reincidencias()

    # Assert
    assert len(casos) == 1
    assert casos[0].id_reincidencia == 1
    assert casos[0].nombre_empresa == "Empresa A"
    assert casos[0].impacto == "Grave"
    assert len(detalle) == 1
    assert detalle[0].descripcion_comportamiento == "Exceso de velocidad"
    assert detalle[0].caso_bitacora_ticket == "1001"


def test_listar_empresas(repositorio: ComportamientosRepository) -> None:
    """RF-03: las empresas se listan ordenadas por nombre."""
    # Arrange / Act
    empresas = repositorio.listar_empresas()

    # Assert
    assert [empresa.nombre_empresa for empresa in empresas] == ["Empresa A", "Empresa B"]


# --- UI: funciones puras -----------------------------------------------------
def test_parsear_entero() -> None:
    """El campo de búsqueda se traduce a un entero o ``None``."""
    # Arrange / Act / Assert
    assert ui.parsear_entero(" 5001 ") == 5001
    assert ui.parsear_entero("123456") == 123456
    assert ui.parsear_entero("abc") is None
    assert ui.parsear_entero("") is None


def test_es_codigo_operacion() -> None:
    """Los textos de cinco caracteres o menos se tratan como código."""
    # Arrange / Act / Assert
    assert ui.es_codigo_operacion("5001") is True
    assert ui.es_codigo_operacion("123456") is False


def test_opciones_detalle() -> None:
    """El mapa del selector usa el identificador como clave."""
    # Arrange
    from certificado_operadores.infra.comportamientos_repository import (
        DetalleComportamientoInfo,
    )

    detalles = [
        DetalleComportamientoInfo(1, "Exceso de velocidad"),
        DetalleComportamientoInfo(2, "Uso de celular"),
    ]

    # Act / Assert
    assert ui.opciones_detalle(detalles) == {
        "1": "Exceso de velocidad",
        "2": "Uso de celular",
    }


def test_limpiar_celdas() -> None:
    """Las celdas de Excel se normalizan a texto, entero y fecha."""
    # Arrange / Act / Assert
    assert ui.texto_celda("  Ana ") == "Ana"
    assert ui.texto_celda("") is None
    assert ui.texto_celda(float("nan")) is None
    assert ui.entero_celda("12.0") == 12
    assert ui.entero_celda("abc") is None
    assert ui.entero_celda(float("nan")) is None
    assert ui.fecha_celda("2026-02-01") == date(2026, 2, 1)
    assert ui.fecha_celda(float("nan")) is None
    assert ui.fecha_texto("2026-02-01 14:30:00") == "2026-02-01"


def test_construir_plantillas_generan_excel() -> None:
    """Las plantillas de comportamientos y acciones son libros de Excel válidos."""
    # Act
    plantilla_comportamiento = ui.construir_plantilla_comportamiento()
    plantilla_acciones = ui.construir_plantilla_acciones()

    # Assert
    assert plantilla_comportamiento[:2] == b"PK"
    assert plantilla_acciones[:2] == b"PK"
    libro = pd.ExcelFile(io.BytesIO(plantilla_comportamiento))
    assert ui.HOJA_INSTRUCCIONES in libro.sheet_names
    assert ui.HOJA_DATOS in libro.sheet_names
    assert list(
        pd.read_excel(io.BytesIO(plantilla_comportamiento), sheet_name=ui.HOJA_DATOS).columns
    ) == list(ui.COLUMNAS_PLANTILLA_COMPORTAMIENTO)


def test_filas_reincidencias() -> None:
    """Los DTOs de reincidencia se convierten en filas tabulables."""
    # Arrange
    from certificado_operadores.infra.comportamientos_repository import ReincidenciaInfo

    caso = ReincidenciaInfo(
        1,
        5001,
        "Empresa A",
        "Grave",
        "Conducción",
        "2026-01-01",
        "2026-01-02",
        1,
        None,
        None,
        None,
        "admin",
    )

    # Act
    filas = ui.filas_reincidencias([caso])

    # Assert
    assert filas[0]["id_reincidencia"] == 1
    assert filas[0]["nombre_empresa"] == "Empresa A"


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_reporte_comportamientos_existe() -> None:
    """CA-01: el paquete existe y expone ``render_reporte_comportamientos``."""
    # Arrange / Act
    from certificado_operadores.modulos.reporte_comportamientos import (
        render_reporte_comportamientos,
    )

    # Assert
    assert callable(render_reporte_comportamientos)


def test_ui_no_contiene_sql_ni_acceso_directo() -> None:
    """RNF-01: la UI no contiene SQL ni acceso directo a la base de datos."""
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


def test_pagina_usa_render_reporte_sin_exec() -> None:
    """RNF-02/CA-02: la pestaña 3 importa la función y ya no usa ``exec``."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_reporte_comportamientos" in contenido
    assert "9_Reporte_Comportamientos" not in contenido
    assert "exec(" not in contenido
    assert "run_query" not in contenido
    assert "run_transaction" not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """RNF-02/CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")
