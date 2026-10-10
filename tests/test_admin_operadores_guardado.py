"""Pruebas del guardado de operadores (spec 023).

Cubren el caso de uso :meth:`OperadoresFacade.guardar_operador` y sus catálogos
de empresa y tipología contra una base SQLite temporal, las funciones puras que
alimentan el formulario y las verificaciones estáticas de los criterios de
aceptación: la UI usa el Facade y el botón de guardado. Todas las pruebas siguen
el patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from certificado_operadores.domain.models import (
    MENSAJE_OPERADOR_CAMPOS_OBLIGATORIOS,
    MENSAJE_OPERADOR_CREADO,
    MENSAJE_OPERADOR_DUPLICADO,
    MENSAJE_OPERADOR_ERROR,
    RegistroOperador,
)
from certificado_operadores.facade import OperadoresFacade
from certificado_operadores.modulos.admin_operadores import ui

_RUTA_UI = Path(ui.__file__).resolve()

# --- Esquema mínimo realista de operadores ----------------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_empresa (
        id_empresa INTEGER PRIMARY KEY, nombre_empresa TEXT, id_vigencia INTEGER,
        fecha_registro TEXT, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_perfil_tipologia (
        id_perfil_tipologia INTEGER PRIMARY KEY, autoriza_articulado INTEGER,
        autoriza_padron INTEGER, autoriza_complementario INTEGER,
        autoriza_auxiliar INTEGER, id_vigencia INTEGER, fecha_registro TEXT,
        usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_persona (
        id_persona INTEGER PRIMARY KEY, primer_apellido TEXT,
        segundo_apellido TEXT, nombres TEXT, genero TEXT, id_vigencia INTEGER,
        fecha_registro TEXT, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY, id_persona INTEGER, id_empresa INTEGER,
        id_perfil_tipologia INTEGER, id_vigencia INTEGER, fecha_registro TEXT,
        usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE log_auditoria (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL,
        accion TEXT NOT NULL, detalles TEXT
    );
    """,
)


class _MotorRoto:
    """Motor falso que siempre falla al abrir una transacción."""

    def connect(self) -> None:
        """Simula un fallo de conexión."""
        raise SQLAlchemyError("conexión no disponible")

    def begin(self) -> None:
        """Simula un fallo al abrir la transacción."""
        raise SQLAlchemyError("conexión no disponible")


def _crear_esquema(motor: Engine) -> None:
    """Crea el esquema mínimo de operadores."""
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta catálogos y dos operadores de ejemplo."""
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO dim_empresa (id_empresa, nombre_empresa, id_vigencia) "
                "VALUES (1, 'Git', 1), (2, 'Bnm', 1)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO dim_perfil_tipologia (id_perfil_tipologia, "
                "autoriza_articulado, autoriza_padron, autoriza_complementario, "
                "autoriza_auxiliar, id_vigencia) VALUES "
                "(1, 1, 1, 0, 0, 1), (2, 0, 0, 1, 0, 1)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO dim_persona (id_persona, primer_apellido, "
                "segundo_apellido, nombres, genero, id_vigencia) VALUES "
                "(1001, 'Perez', 'Gomez', 'Ana', 'F', 1), "
                "(1002, 'Rojas', '', 'Luis', 'M', 1)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO dim_codigo (id_codigo, id_persona, id_empresa, "
                "id_perfil_tipologia, id_vigencia) VALUES "
                "(5001, 1001, 1, 1, 1), (5002, 1002, 2, 2, 1)"
            )
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_guardado.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar_datos(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def fachada(motor_sqlite: Engine) -> OperadoresFacade:
    """Fachada configurada con el motor SQLite de prueba."""
    return OperadoresFacade(engine=motor_sqlite)


def _filas(motor: Engine, sentencia: str) -> list[tuple]:
    """Ejecuta una lectura y devuelve las filas como tuplas."""
    with motor.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(sentencia)).all()]


def _registro_nuevo() -> RegistroOperador:
    """Construye un operador nuevo válido para las pruebas."""
    return RegistroOperador(
        cedula=9999,
        nombres="Pedro",
        primer_apellido="Castro",
        segundo_apellido="Ruiz",
        genero="M",
        id_empresa=1,
        id_perfil_tipologia=2,
    )


# --- Catálogos de empresa y tipología ---------------------------------------
def test_listar_empresas(fachada: OperadoresFacade) -> None:
    """Las empresas se listan ordenadas por identificador."""
    # Arrange / Act
    empresas = fachada.listar_empresas()

    # Assert
    assert [(empresa.id_empresa, empresa.nombre_empresa) for empresa in empresas] == [
        (1, "Git"),
        (2, "Bnm"),
    ]


def test_listar_tipologias(fachada: OperadoresFacade) -> None:
    """Las tipologías se describen según sus autorizaciones."""
    # Arrange / Act
    tipologias = fachada.listar_tipologias()

    # Assert
    assert [tipologia.descripcion for tipologia in tipologias] == [
        "1 - Articulado, Padron",
        "2 - Complementario",
    ]


# --- Detección de duplicados -------------------------------------------------
def test_existe_operador_vigente(fachada: OperadoresFacade) -> None:
    """Una cédula con código vigente se detecta como duplicada."""
    # Arrange / Act / Assert
    assert fachada._repositorio.existe_operador_vigente(1001) is True
    assert fachada._repositorio.existe_operador_vigente(9999) is False


# --- Generación de códigos por concesionario (spec 024, R-08) ----------------
def test_siguiente_codigo_por_concesionario(fachada: OperadoresFacade) -> None:
    """R-08/CA-09: cada concesionario arranca en su base ``id_empresa * 10000``."""
    # Arrange
    repositorio = fachada._repositorio

    # Act / Assert
    assert repositorio.siguiente_codigo(1) == 10001
    assert repositorio.siguiente_codigo(2) == 20001
    assert repositorio.siguiente_codigo(3) == 30001
    assert repositorio.siguiente_codigo(4) == 40001


def test_siguiente_codigo_respeta_el_maximo_del_rango(
    fachada: OperadoresFacade, motor_sqlite: Engine
) -> None:
    """R-08: el siguiente código respeta el máximo ya asignado dentro del rango."""
    # Arrange
    with motor_sqlite.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO dim_codigo (id_codigo, id_persona, id_empresa, "
                "id_perfil_tipologia, id_vigencia) VALUES (10005, 1001, 1, 1, 1)"
            )
        )

    # Act / Assert
    assert fachada._repositorio.siguiente_codigo(1) == 10006
    # El rango del concesionario 2 no se ve afectado por los códigos del 1.
    assert fachada._repositorio.siguiente_codigo(2) == 20001


# --- guardar_operador --------------------------------------------------------
def test_guardar_operador_crea_el_registro(fachada: OperadoresFacade, motor_sqlite: Engine) -> None:
    """Un operador nuevo se persiste y se audita en una sola operación."""
    # Arrange
    registro = _registro_nuevo()

    # Act
    resultado = fachada.guardar_operador(registro, usuario="admin")

    # Assert
    assert resultado.exito is True
    assert resultado.mensaje == MENSAJE_OPERADOR_CREADO
    assert resultado.codigo == 10001
    assert _filas(
        motor_sqlite,
        "SELECT id_persona, nombres, primer_apellido, segundo_apellido, genero "
        "FROM dim_persona WHERE id_persona = 9999",
    ) == [(9999, "Pedro", "Castro", "Ruiz", "M")]
    assert _filas(
        motor_sqlite,
        "SELECT id_codigo, id_empresa, id_perfil_tipologia, id_vigencia "
        "FROM dim_codigo WHERE id_persona = 9999",
    ) == [(10001, 1, 2, 1)]
    assert _filas(motor_sqlite, "SELECT usuario, accion FROM log_auditoria") == [
        ("admin", "CREAR_OPERADOR")
    ]


def test_guardar_operador_rechaza_duplicado(fachada: OperadoresFacade) -> None:
    """Una cédula con operador vigente no se registra dos veces."""
    # Arrange
    registro = RegistroOperador(
        cedula=1002,
        nombres="Luis",
        primer_apellido="Rojas",
        segundo_apellido="",
        genero="M",
        id_empresa=2,
        id_perfil_tipologia=2,
    )

    # Act
    resultado = fachada.guardar_operador(registro)

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_OPERADOR_DUPLICADO
    assert resultado.codigo is None


def test_guardar_operador_exige_campos_obligatorios(fachada: OperadoresFacade) -> None:
    """Sin datos obligatorios el guardado se rechaza con un mensaje claro."""
    # Arrange
    registro = RegistroOperador(
        cedula=0,
        nombres="",
        primer_apellido="",
        segundo_apellido="",
        genero="",
        id_empresa=0,
        id_perfil_tipologia=0,
    )

    # Act
    resultado = fachada.guardar_operador(registro)

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_OPERADOR_CAMPOS_OBLIGATORIOS


def test_guardar_operador_maneja_error_de_persistencia() -> None:
    """Un fallo inesperado de la base se devuelve como resultado, no como excepción."""
    # Arrange
    fachada = OperadoresFacade(engine=cast("Engine", _MotorRoto()))

    # Act
    resultado = fachada.guardar_operador(_registro_nuevo())

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_OPERADOR_ERROR


# --- Funciones puras del formulario -----------------------------------------
def test_construir_registro_normaliza_los_datos() -> None:
    """El formulario se traduce al DTO con la cédula parseada y el género mapeado."""
    # Arrange
    datos: dict[str, Any] = {
        "codigo": None,
        "cedula": " 9999 ",
        "nombres": " Pedro ",
        "primer_apellido": " Castro ",
        "segundo_apellido": " Ruiz ",
        "genero": "M",
        "id_empresa": 1,
        "id_perfil_tipologia": 2,
    }

    # Act
    registro = ui.construir_registro(datos)

    # Assert
    assert registro == RegistroOperador(
        cedula=9999,
        nombres="Pedro",
        primer_apellido="Castro",
        segundo_apellido="Ruiz",
        genero="M",
        id_empresa=1,
        id_perfil_tipologia=2,
    )


def test_construir_registro_con_cedula_invalida() -> None:
    """Una cédula inválida se traduce a cero para que la fachada la rechace."""
    # Arrange
    datos: dict[str, Any] = {"cedula": "abc", "nombres": "X"}

    # Act
    registro = ui.construir_registro(datos)

    # Assert
    assert registro.cedula == 0


def test_indice_genero_traduce_los_codigos() -> None:
    """Los códigos almacenados se traducen a la posición del desplegable."""
    # Arrange / Act / Assert
    assert ui._indice_genero("F") == 1
    assert ui._indice_genero("OTRO") == 2
    assert ui._indice_genero("desconocido") == 0


# --- Criterios de aceptación verificables (CA-04 y CA-05) -------------------
def test_ui_usa_el_boton_guardar_y_el_facade() -> None:
    """CA-05: la UI delega el guardado en ``guardar_operador``."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "guardar_operador" in contenido
    assert "st.form_submit_button" in contenido


def test_ui_organiza_el_formulario_en_columnas() -> None:
    """CA-04: el formulario organiza los datos en columnas horizontales."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "st.columns" in contenido
    assert "Empresa Concesionaria" in contenido
    assert "Tipología de Bus" in contenido
    assert "st.selectbox" in contenido


def test_ui_no_contiene_sentencias_sql() -> None:
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
