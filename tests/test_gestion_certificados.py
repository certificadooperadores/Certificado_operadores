"""Pruebas de la gestión de certificados (spec 008).

Cubren tres frentes: el repositorio ``CertificadosRepository`` contra una base
SQLite temporal (catálogos auxiliares, búsqueda del operador activo y registro
de eventos con auditoría), las funciones puras de la UI (limpieza, validación y
construcción de datos) y las verificaciones estáticas de los criterios de
aceptación: el paquete existe, la UI y la página no contienen SQL y la página
usa ``render_gestion_certificados`` sin ``exec`` en la pestaña 2. Todas las
pruebas siguen el patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from certificado_operadores.infra.certificados_repository import (
    ACCION_CARGA_MASIVA,
    ACCION_REGISTRO_EVENTO,
    TIPO_EVENTO_CANCELACION,
    CertificadosRepository,
    DatosEvento,
    OperadorActivoInfo,
)
from certificado_operadores.infra.eventos_repository import TipoEventoInfo
from certificado_operadores.modulos.gestion_certificados import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "2_Administracion_Operadores.py"
_RUTA_HEREDADO = _RUTA_UI.parents[1] / "6_Gestion_Certificados.py"

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
        segundo_apellido TEXT
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY,
        id_persona INTEGER NOT NULL,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE dim_vehiculo (
        id_vehiculo INTEGER PRIMARY KEY,
        nombre_vehiculo TEXT
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
        restriccion_medica TEXT,
        elemento_de_proteccion TEXT,
        inicio_restriccion_medica TEXT,
        fin_restriccion_medica TEXT,
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

_TIPOS = (
    (1, "Certificación"),
    (2, "Reactivación"),
    (3, "Renovación"),
    (4, "Observación"),
    (5, "Restricción Médica"),
    (6, "Suspensión"),
    (7, "Cancelación"),
    (8, "Advertencia"),
    (9, "Condicionamiento"),
)

_PERSONAS = (
    (1001, "Ana", "Pérez", "Gómez"),
    (1002, "Luis", "Rojas", ""),
)

# (id_codigo, id_persona, id_vigencia, fecha_registro)
_CODIGOS = (
    (5001, 1001, 1, "2026-01-01 08:00:00"),
    (5002, 1002, 1, "2026-01-02 08:00:00"),
    (5999, 1002, 1, "2026-01-03 08:00:00"),  # activo pero cancelado
    (6000, 1002, 2, "2026-01-04 08:00:00"),  # inactivo
)

# (id_hecho_evento, id_codigo, id_tipo_evento, evaluador, fecha_registro)
_EVENTOS = (
    (1, 5001, 1, "Juan Pérez", "2026-01-10 08:15:00"),
    (2, 5999, TIPO_EVENTO_CANCELACION, None, "2026-01-11 08:15:00"),
    (3, 5002, 1, "María López", "2026-01-12 08:15:00"),
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
    """Inserta catálogos, códigos y eventos de ejemplo.

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_tipo_evento VALUES (:id, :nombre)"),
            [{"id": identificador, "nombre": nombre} for identificador, nombre in _TIPOS],
        )
        conexion.execute(
            text("INSERT INTO dim_persona VALUES (:id, :nombres, :apellido, :segundo)"),
            [
                {"id": identificador, "nombres": nombres, "apellido": apellido, "segundo": segundo}
                for identificador, nombres, apellido, segundo in _PERSONAS
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_codigo VALUES (:id, :persona, :vigencia, :fecha)"),
            [
                {"id": codigo, "persona": persona, "vigencia": vigencia, "fecha": fecha}
                for codigo, persona, vigencia, fecha in _CODIGOS
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_vehiculo VALUES (:id, :nombre)"),
            [
                {"id": 1, "nombre": "Bus A"},
                {"id": 2, "nombre": "Bus B"},
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador "
                "(id_hecho_evento, id_codigo, id_tipo_evento, evaluador, id_vigencia, "
                "fecha_registro) "
                "VALUES (:id, :codigo, :tipo, :evaluador, 1, :fecha)"
            ),
            [
                {
                    "id": identificador,
                    "codigo": codigo,
                    "tipo": tipo,
                    "evaluador": evaluador,
                    "fecha": fecha,
                }
                for identificador, codigo, tipo, evaluador, fecha in _EVENTOS
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_certificados.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar_datos(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def repositorio(motor_sqlite: Engine) -> CertificadosRepository:
    """Repositorio de certificados configurado con el motor SQLite de prueba."""
    return CertificadosRepository(engine=motor_sqlite)


def _evento_por_id(motor: Engine, identificador: int) -> dict[str, object]:
    """Devuelve una fila de ``fact_eventos_operador`` como diccionario."""
    with motor.connect() as conexion:
        fila = (
            conexion.execute(
                text("SELECT * FROM fact_eventos_operador WHERE id_hecho_evento = :id"),
                {"id": identificador},
            )
            .mappings()
            .one()
        )
    return dict(fila)


def _auditoria(motor: Engine) -> list[tuple[str, str]]:
    """Devuelve las acciones de auditoría registradas como pares (acción, detalle)."""
    with motor.connect() as conexion:
        filas = conexion.execute(
            text("SELECT accion, detalles FROM log_auditoria ORDER BY id_log")
        ).all()
    return [(str(accion), str(detalles or "")) for accion, detalles in filas]


def _total_eventos(motor: Engine) -> int:
    """Cuenta las filas de ``fact_eventos_operador``."""
    with motor.connect() as conexion:
        return int(
            conexion.execute(text("SELECT COUNT(*) FROM fact_eventos_operador")).scalar_one()
        )


# --- Repositorio: catálogos --------------------------------------------------
def test_listar_tipos_evento_devuelve_dtos_ordenados(repositorio: CertificadosRepository) -> None:
    """El repositorio devuelve los tipos de evento ordenados por id."""
    # Arrange / Act
    tipos = repositorio.listar_tipos_evento()

    # Assert
    assert len(tipos) == 9
    assert tipos[0] == TipoEventoInfo(1, "Certificación")


def test_listar_vehiculos_devuelve_dtos(repositorio: CertificadosRepository) -> None:
    """El repositorio devuelve los vehículos ordenados por id."""
    # Arrange / Act
    vehiculos = repositorio.listar_vehiculos()

    # Assert
    assert [(vehiculo.id_vehiculo, vehiculo.nombre_vehiculo) for vehiculo in vehiculos] == [
        (1, "Bus A"),
        (2, "Bus B"),
    ]


def test_listar_evaluadores_devuelve_distintos_ordenados(
    repositorio: CertificadosRepository,
) -> None:
    """El repositorio lista los evaluadores históricos sin repetir."""
    # Arrange / Act
    evaluadores = repositorio.listar_evaluadores()

    # Assert
    assert evaluadores == ["Juan Pérez", "María López"]


# --- Repositorio: búsqueda del operador activo (RF-01) -----------------------
def test_buscar_operador_activo_por_codigo(repositorio: CertificadosRepository) -> None:
    """RF-01: un código vigente y no cancelado devuelve el operador."""
    # Arrange / Act
    operador = repositorio.buscar_operador_activo_por_codigo(5001)

    # Assert
    assert operador == OperadorActivoInfo(
        id_codigo=5001,
        cedula=1001,
        nombres="Ana",
        primer_apellido="Pérez",
        segundo_apellido="Gómez",
    )
    assert operador is not None
    assert operador.nombre_completo() == "Ana Pérez Gómez"


def test_buscar_operador_activo_por_codigo_cancelado(
    repositorio: CertificadosRepository,
) -> None:
    """RF-01: un código con evento de cancelación no se considera activo."""
    # Arrange / Act
    operador = repositorio.buscar_operador_activo_por_codigo(5999)

    # Assert
    assert operador is None


def test_buscar_operador_activo_por_codigo_inactivo(
    repositorio: CertificadosRepository,
) -> None:
    """RF-01: un código con vigencia inactiva no se devuelve."""
    # Arrange / Act / Assert
    assert repositorio.buscar_operador_activo_por_codigo(6000) is None


def test_buscar_operador_activo_por_cedula_omite_cancelados_e_inactivos(
    repositorio: CertificadosRepository,
) -> None:
    """RF-01: con varios códigos se devuelve el activo más reciente no cancelado."""
    # Arrange / Act
    operador = repositorio.buscar_operador_activo_por_cedula(1002)

    # Assert
    assert operador is not None
    assert operador.id_codigo == 5002


def test_buscar_operador_activo_por_cedula_inexistente(
    repositorio: CertificadosRepository,
) -> None:
    """RF-01: una cédula sin operador no devuelve nada."""
    # Arrange / Act / Assert
    assert repositorio.buscar_operador_activo_por_cedula(9999) is None


# --- Repositorio: registro de eventos con auditoría (RF-02 / CA-03) ----------
def test_registrar_evento_inserta_y_audita(
    repositorio: CertificadosRepository, motor_sqlite: Engine
) -> None:
    """RF-02/CA-03: el evento se inserta con sus campos y queda la auditoría."""
    # Arrange
    datos = DatosEvento(
        id_codigo=5001,
        id_tipo_evento=1,
        id_vehiculo_evaluado=1,
        evaluador="Juan Pérez",
        fecha_prueba=date(2026, 2, 1),
        fecha_certificado=date(2026, 2, 2),
        observacion="Aprobado",
    )

    # Act
    nuevo_id = repositorio.registrar_evento(datos, "admin")

    # Assert
    assert nuevo_id == 4
    fila = _evento_por_id(motor_sqlite, 4)
    assert fila["id_codigo"] == 5001
    assert fila["id_tipo_evento"] == 1
    assert fila["id_vehiculo_evaluado"] == 1
    assert fila["evaluador"] == "Juan Pérez"
    assert fila["fecha_prueba"] == "2026-02-01"
    assert fila["fecha_certificado"] == "2026-02-02"
    assert fila["id_vigencia"] == 1
    assert fila["usuario_registra"] == "admin"
    assert _auditoria(motor_sqlite) == [(ACCION_REGISTRO_EVENTO, "Codigo: 5001, Evento ID: 1")]


def test_registrar_eventos_masivo_cuenta_y_audita(
    repositorio: CertificadosRepository, motor_sqlite: Engine
) -> None:
    """RF-03/CA-03: la carga masiva inserta todo e inyecta una sola auditoría."""
    # Arrange
    eventos = [
        DatosEvento(id_codigo=5001, id_tipo_evento=2, evaluador="Juan Pérez"),
        DatosEvento(id_codigo=5002, id_tipo_evento=3, evaluador="María López"),
    ]

    # Act
    total = repositorio.registrar_eventos(
        eventos, "admin", ACCION_CARGA_MASIVA, "Registros exitosos: 2"
    )

    # Assert
    assert total == 2
    assert _total_eventos(motor_sqlite) == 5
    assert _evento_por_id(motor_sqlite, 4)["id_tipo_evento"] == 2
    assert _evento_por_id(motor_sqlite, 5)["id_tipo_evento"] == 3
    assert _auditoria(motor_sqlite) == [(ACCION_CARGA_MASIVA, "Registros exitosos: 2")]


def test_registrar_eventos_vacio_no_hace_nada(
    repositorio: CertificadosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: una lista vacía no inserta ni audita."""
    # Arrange / Act
    total = repositorio.registrar_eventos([], "admin")

    # Assert
    assert total == 0
    assert _total_eventos(motor_sqlite) == 3
    assert _auditoria(motor_sqlite) == []


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


def test_limpiar_texto_y_entero() -> None:
    """La limpieza normaliza textos vacíos, ``NaN`` y decimales de Excel."""
    # Arrange / Act / Assert
    assert ui.limpiar_texto("  Ana ") == "Ana"
    assert ui.limpiar_texto("") is None
    assert ui.limpiar_texto(float("nan")) is None
    assert ui.limpiar_texto(None) is None
    assert ui.limpiar_entero("12.0") == 12
    assert ui.limpiar_entero("abc") is None
    assert ui.limpiar_entero(float("nan")) is None


def test_opciones_evento_e_id_desde_opcion() -> None:
    """Las opciones del selector se construyen y se vuelven a traducir a id."""
    # Arrange
    tipos = [TipoEventoInfo(1, "certificación"), TipoEventoInfo(7, "cancelación")]

    # Act
    opciones = ui.opciones_evento(tipos)

    # Assert
    assert opciones == ["1 - Certificación", "7 - Cancelación"]
    assert ui.id_desde_opcion(opciones[1]) == 7


def test_nombre_hoja() -> None:
    """Cada tipo de evento tiene su hoja de Excel."""
    # Arrange / Act / Assert
    assert ui.nombre_hoja(1) == "1-Certificacion"
    assert ui.nombre_hoja(7) == "7-Retiros"


def test_validar_evento_individual_por_tipo() -> None:
    """La validación individual exige los campos propios de cada tipo de evento."""
    # Arrange / Act / Assert
    assert ui.validar_evento_individual(1, {"id_vehiculo_evaluado": None, "evaluador": "X"})
    assert ui.validar_evento_individual(1, {"id_vehiculo_evaluado": 1, "evaluador": "X"}) == []
    assert ui.validar_evento_individual(2, {"evaluador": None})
    assert ui.validar_evento_individual(
        5, {"restriccion_medica": "Lumbalgia", "fin_restriccion_medica": None}
    )
    assert (
        ui.validar_evento_individual(
            5, {"restriccion_medica": "Lumbalgia", "fin_restriccion_medica": date(2026, 3, 1)}
        )
        == []
    )
    assert ui.validar_evento_individual(7, {"observacion": None})
    assert ui.validar_evento_individual(
        7, {"observacion": "Retiro", "fecha_retiro": None, "fecha_notificacion_retiro": None}
    )
    assert (
        ui.validar_evento_individual(7, {"observacion": "Retiro", "fecha_retiro": date(2026, 3, 1)})
        == []
    )
    assert ui.validar_evento_individual(4, {"observacion": "Falta", "fecha_observacion": None})
    assert (
        ui.validar_evento_individual(
            4, {"observacion": "Falta", "fecha_observacion": date(2026, 3, 1)}
        )
        == []
    )


def test_validar_fila_masiva() -> None:
    """La validación masiva marca errores según el tipo de evento."""
    # Arrange / Act / Assert
    assert ui.validar_fila_masiva(1, {"id_vehiculo_evaluado": None, "evaluador": None}).startswith(
        "🔴"
    )
    assert ui.validar_fila_masiva(1, {"id_vehiculo_evaluado": 1, "evaluador": "X"}) == ""
    assert ui.validar_fila_masiva(2, {"evaluador": None}).startswith("🔴")
    assert ui.validar_fila_masiva(5, {"restriccion_medica": "X", "fin_restriccion_medica": None})
    assert ui.validar_fila_masiva(
        7, {"observacion": "Motivo", "fecha_retiro": None, "fecha_notificacion_retiro": None}
    )
    assert (
        ui.validar_fila_masiva(
            7,
            {
                "observacion": "Motivo",
                "fecha_retiro": "2026-03-01",
                "fecha_notificacion_retiro": None,
            },
        )
        == ""
    )
    assert ui.validar_fila_masiva(8, {"observacion": "Nota", "fecha_observacion": None})
    assert (
        ui.validar_fila_masiva(8, {"observacion": "Nota", "fecha_observacion": "2026-03-01"}) == ""
    )


def test_construir_datos_desde_fila_traduce_campos() -> None:
    """La fila del Excel se traduce a un ``DatosEvento`` tipado."""
    # Arrange
    fila = {
        "id_vehiculo_evaluado": 1,
        "evaluador": "  Juan  ",
        "fecha_prueba": "2026-02-01",
        "fecha_certificado": "2026-02-02",
        "observacion": "",
    }

    # Act
    datos = ui.construir_datos_desde_fila(1, 5001, fila)

    # Assert
    assert datos == DatosEvento(
        id_codigo=5001,
        id_tipo_evento=1,
        id_vehiculo_evaluado=1,
        evaluador="Juan",
        fecha_prueba=date(2026, 2, 1),
        fecha_certificado=date(2026, 2, 2),
        observacion=None,
    )


def test_construir_plantilla_eventos_genera_excel() -> None:
    """La plantilla maestra es un libro de Excel con una hoja por evento."""
    # Act
    contenido = ui.construir_plantilla_eventos(["Juan Pérez"])

    # Assert
    assert contenido[:2] == b"PK"
    libro = pd.ExcelFile(io.BytesIO(contenido))
    assert ui.HOJA_INSTRUCCIONES in libro.sheet_names
    assert "1-Certificacion" in libro.sheet_names
    assert "7-Retiros" in libro.sheet_names


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_gestion_certificados_existe() -> None:
    """CA-01: el paquete expone ``render_gestion_certificados``."""
    # Arrange / Act
    from certificado_operadores.modulos.gestion_certificados import (
        render_gestion_certificados,
    )

    # Assert
    assert callable(render_gestion_certificados)


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


def test_pagina_usa_render_gestion_certificados_sin_exec() -> None:
    """RNF-02/CA-02: la pestaña 2 importa la función y ya no usa ``exec``."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_gestion_certificados" in contenido
    assert "6_Gestion_Certificados" not in contenido
    assert "run_query" not in contenido
    assert "run_transaction" not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """RNF-02/CA-02: el archivo de la página es sintácticamente válido."""
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

    assert "RENDER_GESTION_CERTIFICADOS" in contenido
    assert patron.findall(contenido) == []
