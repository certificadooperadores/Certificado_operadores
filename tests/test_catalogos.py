"""Pruebas de la gestión de catálogos (spec 007).

Cubren el repositorio ``CatalogosRepository`` contra una base SQLite temporal
(las cinco dimensiones, con sus mutaciones y la auditoría), las funciones puras
de la UI y las verificaciones estáticas de los criterios de aceptación: el
paquete existe, la UI y la página no contienen SQL y la página usa
``render_catalogos`` sin ``exec``. Todas las pruebas siguen el patrón AAA
(*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from certificado_operadores.domain.models import VIGENCIA_ACTIVA, VIGENCIA_ANULADA
from certificado_operadores.infra.catalogos_repository import (
    ACCION_CREAR_COMPORTAMIENTO,
    ACCION_CREAR_DETALLE,
    ACCION_CREAR_IMPACTO,
    ACCION_EDITAR_COMPORTAMIENTO,
    ACCION_EDITAR_DETALLE,
    ACCION_EDITAR_IMPACTO,
    CatalogosRepository,
    ComportamientoInfo,
    DatosDetalleComportamiento,
    DetalleComportamientoInfo,
    EmpresaInfo,
    ImpactoInfo,
    VehiculoInfo,
    construir_descripcion_comportamiento,
)
from certificado_operadores.modulos.catalogos import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_REPOSITORIO = _RUTA_UI.parents[2] / "infra" / "catalogos_repository.py"
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "1_Configuracion.py"

# --- Esquema mínimo para las pruebas del repositorio ------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_empresa (
        id_empresa INTEGER PRIMARY KEY, nombre_empresa TEXT,
        id_vigencia INTEGER, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_vehiculo (
        id_vehiculo INTEGER PRIMARY KEY, nombre_vehiculo TEXT, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_impacto (
        id_impacto INTEGER PRIMARY KEY, impacto TEXT,
        maximo INTEGER, dias_maximo INTEGER, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_comportamiento (
        id_comportamiento INTEGER PRIMARY KEY, comportamiento TEXT,
        id_impacto INTEGER, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE dim_detalle_comportamiento (
        id_jerarquia INTEGER PRIMARY KEY, fuente TEXT, descripcion_comportamiento TEXT,
        tipo TEXT, servicios TEXT, jerarquia_1 TEXT, jerarquia_2 TEXT, jerarquia_3 TEXT,
        jerarquia_4 TEXT, id_comportamiento INTEGER, usuario_registra TEXT
    );
    """,
    """
    CREATE TABLE log_auditoria (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL,
        accion TEXT NOT NULL, detalles TEXT, fecha_registro TEXT
    );
    """,
)

_EMPRESAS = (
    (1, "ALCANOS", VIGENCIA_ACTIVA),
    (2, "BLANCO Y NEGRO", VIGENCIA_ANULADA),
)
_VEHICULOS = ((1, "ABC123"), (2, "XYZ789"))
_IMPACTOS = ((1, "LEVE", 2, 90), (2, "GRAVE", 3, 180))
_COMPORTAMIENTOS = (
    (1, "exceso de velocidad", 2),
    (2, "no usar cinturón", 1),
)
_DETALLES = (
    (1, "pqrs", "tipo::servicio::j1", "tipo", "servicio", "j1", None, None, None, 1),
    (2, "jerarquia hgi", "t2::s2::a::b", "t2", "s2", "a", "b", None, None, 2),
)


def _crear_esquema(motor: Engine) -> None:
    """Crea las tablas mínimas de catálogos y auditoría.

    Args:
        motor: Motor SQLAlchemy donde se crea el esquema.
    """
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta empresas, vehículos, impactos, comportamientos y detalles.

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_empresa VALUES (:id, :nombre, :vigencia, :usuario)"),
            [
                {"id": identificador, "nombre": nombre, "vigencia": vigencia, "usuario": "seed"}
                for identificador, nombre, vigencia in _EMPRESAS
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_vehiculo VALUES (:id, :nombre, :usuario)"),
            [
                {"id": identificador, "nombre": nombre, "usuario": "seed"}
                for identificador, nombre in _VEHICULOS
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_impacto VALUES (:id, :nombre, :maximo, :dias, :usuario)"),
            [
                {
                    "id": identificador,
                    "nombre": nombre,
                    "maximo": maximo,
                    "dias": dias,
                    "usuario": "seed",
                }
                for identificador, nombre, maximo, dias in _IMPACTOS
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_comportamiento VALUES (:id, :nombre, :id_impacto, :usuario)"),
            [
                {
                    "id": identificador,
                    "nombre": nombre,
                    "id_impacto": id_impacto,
                    "usuario": "seed",
                }
                for identificador, nombre, id_impacto in _COMPORTAMIENTOS
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_detalle_comportamiento VALUES "
                "(:id, :fuente, :descripcion, :tipo, :servicios, "
                ":j1, :j2, :j3, :j4, :comp, :usuario)"
            ),
            [
                {
                    "id": identificador,
                    "fuente": fuente,
                    "descripcion": descripcion,
                    "tipo": tipo,
                    "servicios": servicios,
                    "j1": j1,
                    "j2": j2,
                    "j3": j3,
                    "j4": j4,
                    "comp": comp,
                    "usuario": "seed",
                }
                for (
                    identificador,
                    fuente,
                    descripcion,
                    tipo,
                    servicios,
                    j1,
                    j2,
                    j3,
                    j4,
                    comp,
                ) in _DETALLES
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_catalogos.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar_datos(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def repositorio(motor_sqlite: Engine) -> CatalogosRepository:
    """Repositorio de catálogos configurado con el motor SQLite de prueba."""
    return CatalogosRepository(engine=motor_sqlite)


def _auditoria(motor: Engine) -> list[tuple[str, str]]:
    """Devuelve las acciones de auditoría registradas como pares (acción, detalle)."""
    with motor.connect() as conexion:
        filas = conexion.execute(
            text("SELECT accion, detalles FROM log_auditoria ORDER BY id_log")
        ).all()
    return [(str(accion), str(detalles or "")) for accion, detalles in filas]


def _vigencia_empresa(motor: Engine, id_empresa: int) -> int:
    """Devuelve la vigencia almacenada de una empresa."""
    with motor.connect() as conexion:
        return int(
            conexion.execute(
                text("SELECT id_vigencia FROM dim_empresa WHERE id_empresa = :id"),
                {"id": id_empresa},
            ).scalar_one()
        )


# --- Repositorio: empresas (RF-01) ------------------------------------------
def test_listar_empresas_devuelve_dtos_ordenados(repositorio: CatalogosRepository) -> None:
    """RF-01: las empresas se listan ordenadas y con su estado legible."""
    # Arrange / Act
    empresas = repositorio.listar_empresas()

    # Assert
    assert empresas == [
        EmpresaInfo(1, "ALCANOS", VIGENCIA_ACTIVA),
        EmpresaInfo(2, "BLANCO Y NEGRO", VIGENCIA_ANULADA),
    ]
    assert [empresa.estado for empresa in empresas] == ["Activo", "Inactivo"]


def test_crear_empresa_asigna_siguiente_id_y_normaliza(
    repositorio: CatalogosRepository,
) -> None:
    """RF-01: crear empresa usa el siguiente id, la activa y la pone en mayúsculas."""
    # Act
    nuevo_id = repositorio.crear_empresa("nueva empresa", "admin")

    # Assert
    assert nuevo_id == 3
    assert repositorio.listar_empresas()[-1] == EmpresaInfo(3, "NUEVA EMPRESA", VIGENCIA_ACTIVA)


def test_cambiar_vigencia_empresa(repositorio: CatalogosRepository, motor_sqlite: Engine) -> None:
    """RF-01: activar/inactivar cambia la vigencia de la empresa."""
    # Act
    repositorio.cambiar_vigencia_empresa(1, VIGENCIA_ANULADA)

    # Assert
    assert _vigencia_empresa(motor_sqlite, 1) == VIGENCIA_ANULADA


def test_renombrar_empresa(repositorio: CatalogosRepository, motor_sqlite: Engine) -> None:
    """RF-01: renombrar cambia el nombre y lo normaliza a mayúsculas."""
    # Act
    repositorio.renombrar_empresa(1, "alcanos s.a.")

    # Assert
    with motor_sqlite.connect() as conexion:
        nombre = conexion.execute(
            text("SELECT nombre_empresa FROM dim_empresa WHERE id_empresa = 1")
        ).scalar_one()
    assert nombre == "ALCANOS S.A."


# --- Repositorio: vehículos (RF-02) -----------------------------------------
def test_listar_vehiculos(repositorio: CatalogosRepository) -> None:
    """RF-02: los vehículos se listan ordenados por identificador."""
    # Arrange / Act
    vehiculos = repositorio.listar_vehiculos()

    # Assert
    assert vehiculos == [VehiculoInfo(1, "ABC123"), VehiculoInfo(2, "XYZ789")]


def test_crear_y_renombrar_vehiculo(repositorio: CatalogosRepository) -> None:
    """RF-02: crear usa el siguiente id y renombrar cambia el nombre."""
    # Act
    nuevo_id = repositorio.crear_vehiculo("def456", "admin")
    repositorio.renombrar_vehiculo(1, "abc999")

    # Assert
    assert nuevo_id == 3
    assert repositorio.listar_vehiculos() == [
        VehiculoInfo(1, "ABC999"),
        VehiculoInfo(2, "XYZ789"),
        VehiculoInfo(3, "DEF456"),
    ]


# --- Repositorio: impactos (RF-03) ------------------------------------------
def test_listar_impactos(repositorio: CatalogosRepository) -> None:
    """RF-03: los impactos se listan ordenados por identificador."""
    # Arrange / Act
    impactos = repositorio.listar_impactos()

    # Assert
    assert impactos == [
        ImpactoInfo(1, "LEVE", 2, 90),
        ImpactoInfo(2, "GRAVE", 3, 180),
    ]


def test_crear_impacto_audita(repositorio: CatalogosRepository, motor_sqlite: Engine) -> None:
    """RF-03: crear impacto guarda el registro y su auditoría en la transacción."""
    # Act
    nuevo_id = repositorio.crear_impacto("medio", 4, 120, "admin")

    # Assert
    assert nuevo_id == 3
    assert repositorio.listar_impactos()[-1] == ImpactoInfo(3, "MEDIO", 4, 120)
    assert _auditoria(motor_sqlite) == [(ACCION_CREAR_IMPACTO, "Impacto: medio")]


def test_actualizar_impacto_audita(repositorio: CatalogosRepository, motor_sqlite: Engine) -> None:
    """RF-03: actualizar impacto cambia sus valores y audita."""
    # Act
    repositorio.actualizar_impacto(1, "muy leve", 5, 30, "admin")

    # Assert
    assert repositorio.listar_impactos()[0] == ImpactoInfo(1, "MUY LEVE", 5, 30)
    assert _auditoria(motor_sqlite) == [(ACCION_EDITAR_IMPACTO, "ID: 1")]


# --- Repositorio: comportamientos (RF-04) -----------------------------------
def test_listar_comportamientos_cruza_el_impacto(repositorio: CatalogosRepository) -> None:
    """RF-04: el listado une cada comportamiento con el nombre de su impacto."""
    # Arrange / Act
    comportamientos = repositorio.listar_comportamientos()

    # Assert
    assert comportamientos == [
        ComportamientoInfo(1, "exceso de velocidad", 2, "GRAVE"),
        ComportamientoInfo(2, "no usar cinturón", 1, "LEVE"),
    ]


def test_crear_comportamiento_audita(
    repositorio: CatalogosRepository, motor_sqlite: Engine
) -> None:
    """RF-04: crear comportamiento normaliza la descripción y audita."""
    # Act
    nuevo_id = repositorio.crear_comportamiento("Sin luces", 1, "admin")

    # Assert
    assert nuevo_id == 3
    assert repositorio.listar_comportamientos()[-1] == ComportamientoInfo(3, "sin luces", 1, "LEVE")
    assert _auditoria(motor_sqlite) == [(ACCION_CREAR_COMPORTAMIENTO, "Comportamiento: Sin luces")]


def test_actualizar_comportamiento_audita(
    repositorio: CatalogosRepository, motor_sqlite: Engine
) -> None:
    """RF-04: actualizar comportamiento cambia el impacto asociado y audita."""
    # Act
    repositorio.actualizar_comportamiento(1, "Exceso Moderado", 1, "admin")

    # Assert
    assert repositorio.listar_comportamientos()[0] == ComportamientoInfo(
        1, "exceso moderado", 1, "LEVE"
    )
    assert _auditoria(motor_sqlite) == [(ACCION_EDITAR_COMPORTAMIENTO, "ID: 1")]


# --- Repositorio: detalles de comportamiento (RF-05) ------------------------
def test_listar_detalles_devuelve_dtos(repositorio: CatalogosRepository) -> None:
    """RF-05: los detalles se listan con su comportamiento asociado."""
    # Arrange / Act
    detalles = repositorio.listar_detalles()

    # Assert
    assert [detalle.id_jerarquia for detalle in detalles] == [1, 2]
    assert detalles[0].comportamiento == "exceso de velocidad"
    assert detalles[1].jerarquia_2 == "b"


def test_listar_detalles_filtra_por_fuente(repositorio: CatalogosRepository) -> None:
    """RF-05: el listado se puede filtrar por fuente."""
    # Act
    detalles = repositorio.listar_detalles(fuente="pqrs")

    # Assert
    assert [detalle.id_jerarquia for detalle in detalles] == [1]


def test_crear_detalle_construye_descripcion_y_audita(
    repositorio: CatalogosRepository, motor_sqlite: Engine
) -> None:
    """RF-05: crear detalle compone la descripción y registra la auditoría."""
    # Arrange
    datos = DatosDetalleComportamiento(
        fuente="pqrs",
        tipo="Tipo",
        servicios="Servicio",
        jerarquia_1="A",
        jerarquia_2="B",
        jerarquia_3=None,
        jerarquia_4=None,
        id_comportamiento=1,
    )

    # Act
    nuevo_id = repositorio.crear_detalle(datos, "admin")

    # Assert
    assert nuevo_id == 3
    creado = repositorio.listar_detalles(fuente="pqrs")[-1]
    assert creado.descripcion_comportamiento == "tipo::servicio::a::b"
    assert creado.jerarquia_2 == "b"
    assert creado.jerarquia_3 is None
    assert _auditoria(motor_sqlite) == [(ACCION_CREAR_DETALLE, "Desc: tipo::servicio::a::b")]


def test_actualizar_detalle_audita(repositorio: CatalogosRepository, motor_sqlite: Engine) -> None:
    """RF-05: actualizar detalle recomputa la descripción y audita."""
    # Arrange
    datos = DatosDetalleComportamiento(
        fuente="secretaría de movilidad",
        tipo="Nuevo",
        servicios="Serv",
        jerarquia_1="J1",
        jerarquia_2=None,
        jerarquia_3=None,
        jerarquia_4=None,
        id_comportamiento=2,
    )

    # Act
    repositorio.actualizar_detalle(1, datos, "admin")

    # Assert
    actualizado = repositorio.listar_detalles()[0]
    assert actualizado.fuente == "secretaría de movilidad"
    assert actualizado.descripcion_comportamiento == "nuevo::serv::j1"
    assert actualizado.id_comportamiento == 2
    assert _auditoria(motor_sqlite) == [(ACCION_EDITAR_DETALLE, "ID: 1")]


# --- Repositorio: función pura de descripción -------------------------------
def test_construir_descripcion_comportamiento() -> None:
    """La descripción compuesta une en minúsculas las jerarquías presentes."""
    # Arrange / Act / Assert
    assert (
        construir_descripcion_comportamiento("TIPO", "Serv", "A", "B", "C", "D")
        == "tipo::serv::a::b::c::d"
    )
    assert construir_descripcion_comportamiento("TIPO", "Serv", "A") == "tipo::serv::a"


# --- UI: funciones puras -----------------------------------------------------
def test_vigencia_desde_accion() -> None:
    """La acción legible se traduce a la vigencia de la base."""
    # Arrange / Act / Assert
    assert ui.vigencia_desde_accion("Activar") == VIGENCIA_ACTIVA
    assert ui.vigencia_desde_accion("Inactivar") == VIGENCIA_ANULADA


def test_filas_empresas_y_vehiculos() -> None:
    """Las tablas de empresa y vehículo exponen columnas legibles."""
    # Arrange
    empresas = [EmpresaInfo(1, "ALCANOS", VIGENCIA_ACTIVA)]
    vehiculos = [VehiculoInfo(1, "ABC123")]

    # Act / Assert
    assert ui.filas_empresas(empresas) == [{"ID": 1, "Empresa": "ALCANOS", "Estado": "Activo"}]
    assert ui.filas_vehiculos(vehiculos) == [{"ID": 1, "Vehículo": "ABC123"}]


def test_filas_impactos_y_comportamientos() -> None:
    """Las tablas de impacto y comportamiento exponen sus columnas."""
    # Arrange
    impactos = [ImpactoInfo(1, "LEVE", 2, 90)]
    comportamientos = [ComportamientoInfo(1, "exceso", 1, "LEVE")]

    # Act / Assert
    assert ui.filas_impactos(impactos) == [
        {"ID": 1, "Impacto": "LEVE", "Máximo": 2, "Días reinicio": 90}
    ]
    assert ui.filas_comportamientos(comportamientos) == [
        {"ID": 1, "Comportamiento": "exceso", "Impacto": "LEVE"}
    ]


def test_filas_detalles() -> None:
    """La tabla de detalles expone la jerarquía completa."""
    # Arrange
    detalle = DetalleComportamientoInfo(
        id_jerarquia=1,
        fuente="pqrs",
        descripcion_comportamiento="tipo::serv::j1",
        tipo="tipo",
        servicios="serv",
        jerarquia_1="j1",
        jerarquia_2=None,
        jerarquia_3=None,
        jerarquia_4=None,
        id_comportamiento=1,
        comportamiento="exceso",
    )

    # Act
    filas = ui.filas_detalles([detalle])

    # Assert
    assert filas == [
        {
            "ID": 1,
            "Fuente": "pqrs",
            "Descripción": "tipo::serv::j1",
            "Tipo": "tipo",
            "Servicios": "serv",
            "Jerarquía 1": "j1",
            "Jerarquía 2": None,
            "Jerarquía 3": None,
            "Jerarquía 4": None,
            "Comportamiento": "exceso",
        }
    ]


def test_opciones_impacto_y_su_busqueda() -> None:
    """El mapa de impactos permite elegir por nombre y recuperar su id."""
    # Arrange
    impactos = [ImpactoInfo(1, "LEVE", 2, 90), ImpactoInfo(2, "GRAVE", 3, 180)]

    # Act
    opciones = ui.opciones_impacto(impactos)

    # Assert
    assert opciones == {1: "LEVE", 2: "GRAVE"}
    assert ui.id_impacto_desde_nombre(opciones, "GRAVE") == 2
    assert ui.id_impacto_desde_nombre(opciones, "INEXISTENTE") is None


def test_opciones_comportamiento() -> None:
    """El mapa de comportamientos se indexa por su identificador textual."""
    # Arrange
    comportamientos = [ComportamientoInfo(1, "exceso", 1, "LEVE")]

    # Act / Assert
    assert ui.opciones_comportamiento(comportamientos) == {"1": "exceso"}


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_catalogos_existe() -> None:
    """CA-01: el paquete expone ``render_catalogos``."""
    # Arrange / Act
    from certificado_operadores.modulos.catalogos import render_catalogos

    # Assert
    assert callable(render_catalogos)


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


def test_repositorio_encapsula_la_sql() -> None:
    """CA-03: todo el acceso a datos de catálogos vive en el repositorio."""
    # Arrange
    contenido = _RUTA_REPOSITORIO.read_text(encoding="utf-8").upper()

    # Act / Assert
    assert "CATALOGOSREPOSITORY" in contenido
    assert "RUN_QUERY" not in contenido
    assert "RUN_TRANSACTION" not in contenido


def test_pagina_usa_render_catalogos_sin_exec() -> None:
    """CA-02/RNF-02: la página importa ``render_catalogos`` y no usa ``exec``."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "from modulos.catalogos.ui import render_catalogos" in contenido
    assert "render_catalogos()" in contenido
    assert "exec(" not in contenido
    assert "4_Catalogos.py" not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")
