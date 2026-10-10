"""Pruebas unitarias de la fachada de operadores (patrón Facade).

Se ejecutan contra una base SQLite temporal con un esquema mínimo y datos
sembrados, de modo que las pruebas no dependen de la base real del proyecto.
Todas las pruebas siguen el patrón AAA (*Arrange · Act · Assert*).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from certificado_operadores.facade import OperadoresFacade

# --- Esquema mínimo para las pruebas ----------------------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_vigencia_registro (id_vigencia INTEGER PRIMARY KEY, condicion_fila TEXT);
    """,
    """
    CREATE TABLE dim_empresa (
        id_empresa INTEGER PRIMARY KEY, nombre_empresa TEXT, id_vigencia INTEGER
    );
    """,
    """
    CREATE TABLE dim_persona (
        id_persona INTEGER PRIMARY KEY, nombres TEXT, primer_apellido TEXT,
        segundo_apellido TEXT, genero TEXT, id_vigencia INTEGER
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY, id_persona INTEGER, id_empresa INTEGER,
        id_perfil_tipologia INTEGER, id_vigencia INTEGER
    );
    """,
    """
    CREATE TABLE fact_eventos_operador (
        id_hecho_evento INTEGER PRIMARY KEY, id_codigo INTEGER, id_tipo_evento INTEGER,
        fecha_certificado TEXT, id_vigencia INTEGER
    );
    """,
    """
    CREATE TABLE fact_licencias (
        id_hecho_licencia INTEGER PRIMARY KEY, id_codigo INTEGER, tipo TEXT,
        vencimiento TEXT, id_vigencia INTEGER
    );
    """,
)


class _MotorRoto:
    """Motor falso que siempre falla al intentar conectar."""

    def connect(self) -> None:
        """Simula un fallo de conexión a la base de datos."""
        raise SQLAlchemyError("conexión no disponible")


def _crear_esquema(motor: Engine) -> None:
    """Crea las tablas mínimas necesarias para las pruebas."""
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta datos de ejemplo con fechas relativas al día de hoy."""
    hoy = date.today()
    por_vencer = (hoy - timedelta(days=365 * 3 - 30)).isoformat()
    vigente = (hoy - timedelta(days=10)).isoformat()
    vencido = (hoy - timedelta(days=365 * 3 + 10)).isoformat()

    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_vigencia_registro VALUES (1, 'Vigente'), (2, 'Anulado')")
        )
        conexion.execute(text("INSERT INTO dim_empresa VALUES (1, 'Git', 1), (2, 'Bnm', 1)"))
        conexion.execute(
            text(
                "INSERT INTO dim_persona VALUES "
                "(1001, 'Ana', 'Perez', 'Gomez', 'F', 1), "
                "(1002, 'Luis', 'Rojas', '', 'M', 1), "
                "(1003, 'Marta', 'Lopez', 'Diaz', 'F', 1), "
                "(1004, 'Pedro', 'Castro', '', 'M', 1), "
                "(1005, 'Sofia', 'Mora', '', 'F', 2)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO dim_codigo VALUES "
                "(5001, 1001, 1, 1, 1), "
                "(5002, 1002, 2, 1, 1), "
                "(5003, 1003, 1, 1, 1), "
                "(5004, 1004, 1, 1, 1), "
                "(5005, 1005, 2, 1, 2)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador "
                "(id_hecho_evento, id_codigo, id_tipo_evento, "
                "fecha_certificado, id_vigencia) VALUES "
                "(1, 5001, 1, :por_vencer, 1), "
                "(2, 5002, 3, :vigente, 1), "
                "(3, 5004, 1, :vigente, 1), "
                "(4, 5004, 7, NULL, 1), "
                "(5, 5005, 1, :vencido, 1)"
            ),
            {"por_vencer": por_vencer, "vigente": vigente, "vencido": vencido},
        )
        conexion.execute(
            text(
                "INSERT INTO fact_licencias VALUES "
                "(1, 5001, 'C3', '2030-01-01', 1), (2, 5002, 'C2', '2031-01-01', 1)"
            )
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Engine:
    """Motor SQLite temporal con esquema y datos de prueba."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_facade.db'}")
    _crear_esquema(motor)
    _sembrar_datos(motor)
    return motor


@pytest.fixture
def fachada(motor_sqlite: Engine) -> OperadoresFacade:
    """Fachada configurada con el motor SQLite de prueba."""
    return OperadoresFacade(engine=motor_sqlite)


# --- RF-01: estado de la conexión -------------------------------------------
def test_verificar_conexion_true_con_motor_valido(fachada: OperadoresFacade) -> None:
    """Una conexión válida reporta el estado como correcto."""
    # Arrange / Act
    resultado = fachada.verificar_conexion()

    # Assert
    assert resultado is True


def test_verificar_conexion_false_si_falla() -> None:
    """Un fallo de conexión se reporta como estado no disponible."""
    # Arrange
    fachada = OperadoresFacade(engine=cast("Engine", _MotorRoto()))

    # Act
    resultado = fachada.verificar_conexion()

    # Assert
    assert resultado is False


# --- RF-02: consulta de operadores ------------------------------------------
def test_obtener_operador_por_cedula(fachada: OperadoresFacade) -> None:
    """La consulta por cédula devuelve los datos y la empresa del operador."""
    # Arrange
    cedula = 1002

    # Act
    operador = fachada.obtener_operador_por_cedula(cedula)

    # Assert
    assert operador is not None
    assert operador.codigo == 5002
    assert operador.cedula == 1002
    assert operador.nombre_empresa == "Bnm"
    assert operador.nombre_completo() == "Luis Rojas"


def test_obtener_operador_por_cedula_inexistente(fachada: OperadoresFacade) -> None:
    """Una cédula inexistente devuelve ``None``."""
    # Arrange
    cedula = 99999999

    # Act
    operador = fachada.obtener_operador_por_cedula(cedula)

    # Assert
    assert operador is None


def test_obtener_operador_por_codigo(fachada: OperadoresFacade) -> None:
    """La consulta por código devuelve el operador asociado."""
    # Arrange
    codigo = 5001

    # Act
    operador = fachada.obtener_operador_por_codigo(codigo)

    # Assert
    assert operador is not None
    assert operador.codigo == 5001
    assert operador.cedula == 1001
    assert operador.nombre_completo() == "Ana Perez Gomez"


def test_obtener_operador_por_codigo_inexistente(fachada: OperadoresFacade) -> None:
    """Un código inexistente devuelve ``None``."""
    # Arrange
    codigo = 1

    # Act
    operador = fachada.obtener_operador_por_codigo(codigo)

    # Assert
    assert operador is None


# --- Objetivo: validación de certificados -----------------------------------
def test_validar_certificado_por_vencer(fachada: OperadoresFacade) -> None:
    """Un certificado que vence dentro del umbral se marca ``POR_VENCER``."""
    # Arrange
    codigo = 5001

    # Act
    estado = fachada.validar_certificado(codigo)

    # Assert
    assert estado.estado == "POR_VENCER"
    assert estado.cancelado is False
    assert estado.dias_restantes is not None
    assert 0 <= estado.dias_restantes <= 90


def test_validar_certificado_vigente(fachada: OperadoresFacade) -> None:
    """Un certificado reciente se marca ``VIGENTE``."""
    # Arrange
    codigo = 5002

    # Act
    estado = fachada.validar_certificado(codigo)

    # Assert
    assert estado.estado == "VIGENTE"
    assert estado.fecha_certificado is not None
    assert estado.fecha_vencimiento is not None
    assert estado.dias_restantes is not None
    assert estado.dias_restantes > 90


def test_validar_certificado_sin_certificado(fachada: OperadoresFacade) -> None:
    """Un operador sin eventos de certificación se marca ``SIN_CERTIFICADO``."""
    # Arrange
    codigo = 5003

    # Act
    estado = fachada.validar_certificado(codigo)

    # Assert
    assert estado.estado == "SIN_CERTIFICADO"
    assert estado.fecha_certificado is None
    assert estado.dias_restantes is None


def test_validar_certificado_cancelado(fachada: OperadoresFacade) -> None:
    """Un operador con evento de cancelación se marca ``CANCELADO``."""
    # Arrange
    codigo = 5004

    # Act
    estado = fachada.validar_certificado(codigo)

    # Assert
    assert estado.estado == "CANCELADO"
    assert estado.cancelado is True


def test_validar_certificado_vencido(fachada: OperadoresFacade) -> None:
    """Un certificado con fecha anterior al periodo de vigencia se marca ``VENCIDO``."""
    # Arrange
    codigo = 5005

    # Act
    estado = fachada.validar_certificado(codigo)

    # Assert
    assert estado.estado == "VENCIDO"
    assert estado.cancelado is False
    assert estado.dias_restantes is not None
    assert estado.dias_restantes < 0


# --- Objetivo: estadísticas básicas -----------------------------------------
def test_estadisticas_basicas(fachada: OperadoresFacade) -> None:
    """Las estadísticas cuentan operadores, vigencias, empresas y licencias."""
    # Arrange / Act
    estadisticas = fachada.estadisticas_basicas()

    # Assert
    assert estadisticas.total_operadores == 5
    assert estadisticas.operadores_vigentes == 4
    assert estadisticas.operadores_anulados == 1
    assert estadisticas.total_empresas == 2
    assert estadisticas.total_licencias == 2


def test_estadisticas_basicas_devuelve_ceros_sin_esquema(tmp_path: Path) -> None:
    """Sin tablas cargadas, las estadísticas devuelven ceros sin fallar."""
    # Arrange
    motor_vacio = create_engine(f"sqlite:///{tmp_path / 'vacio.db'}")
    fachada = OperadoresFacade(engine=motor_vacio)

    # Act
    estadisticas = fachada.estadisticas_basicas()

    # Assert
    assert estadisticas.total_operadores == 0
    assert estadisticas.total_licencias == 0
