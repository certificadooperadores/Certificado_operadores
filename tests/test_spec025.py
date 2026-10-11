"""Pruebas de la spec 025: índices, pragmas y fachadas especializadas.

Verifican los criterios de aceptación: la UI no importa repositorios, el motor
SQLite opera con ``WAL``/``busy_timeout`` y usa los índices estratégicos, las
fachadas delegan en la infraestructura y el estado de versión se consulta a
través de ``BackupService``. Patrón AAA contra bases SQLite temporales.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from certificado_operadores.db import INDICES_SQLITE, configurar_pragmas, crear_indices
from certificado_operadores.facade_certificados import CertificadosFacade
from certificado_operadores.facade_comportamientos import ComportamientosFacade
from certificado_operadores.facade_configuracion import ConfiguracionFacade
from certificado_operadores.facade_reportes import ReportesFacade
from certificado_operadores.infra.backup_service import (
    ORIGEN_BD_INICIAL,
    BackupService,
)

RAIZ = Path(__file__).resolve().parents[1]
RUTA_PYPROJECT = RAIZ / "pyproject.toml"
RUTA_MODULOS = RAIZ / "src" / "certificado_operadores" / "modulos"
MODULOS_UI = (
    "gestion_certificados",
    "reporte_comportamientos",
    "reportes",
    "catalogos",
    "correccion_registros",
)

_SQL_TABLAS_PRUEBA = (
    "CREATE TABLE dim_persona (id_persona INTEGER PRIMARY KEY)",
    "CREATE TABLE dim_empresa (id_empresa INTEGER PRIMARY KEY, nombre_empresa TEXT, "
    "id_vigencia INTEGER, usuario_registra TEXT)",
    "CREATE TABLE dim_codigo (id_codigo INTEGER PRIMARY KEY, id_persona INTEGER, "
    "id_empresa INTEGER, id_vigencia INTEGER)",
    "CREATE TABLE fact_eventos_operador (id_codigo INTEGER, id_tipo_evento INTEGER, "
    "id_vigencia INTEGER, fecha_certificado TEXT, fecha_retiro TEXT)",
    "CREATE TABLE fact_comportamiento (id_codigo INTEGER, fecha_evento TEXT)",
    "CREATE TABLE fact_reincidencia (id_codigo INTEGER, estado TEXT)",
)


@pytest.fixture
def motor(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con pragmas e índices listos para consultar."""
    engine = create_engine(f"sqlite:///{tmp_path / 'prueba.db'}", poolclass=NullPool, future=True)
    configurar_pragmas(engine)
    with engine.begin() as conexion:
        for sentencia in _SQL_TABLAS_PRUEBA:
            conexion.execute(text(sentencia))
    yield engine
    engine.dispose()


def test_pragmas_de_rendimiento_activos(motor: Engine) -> None:
    """CA-03: el motor opera con WAL, busy_timeout=5000 y synchronous=NORMAL."""
    # Arrange / Act
    with motor.connect() as conexion:
        journal = conexion.execute(text("PRAGMA journal_mode")).scalar_one()
        busy = conexion.execute(text("PRAGMA busy_timeout")).scalar_one()
        synchronous = conexion.execute(text("PRAGMA synchronous")).scalar_one()

    # Assert
    assert str(journal).lower() == "wal"
    assert int(busy) == 5000
    assert int(synchronous) == 1


def test_crear_indices_es_idempotente(motor: Engine) -> None:
    """CA-02: se crean los siete índices estratégicos y repetirlo no falla."""
    # Arrange / Act
    crear_indices(motor)
    crear_indices(motor)
    with motor.connect() as conexion:
        nombres = {
            fila[0]
            for fila in conexion.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'index'")
            )
        }

    # Assert
    for nombre, _tabla, _columnas in INDICES_SQLITE:
        assert nombre in nombres


def test_consulta_analitica_usa_indice(motor: Engine) -> None:
    """CA-02: la consulta por código usa el índice de comportamientos."""
    # Arrange
    crear_indices(motor)

    # Act
    with motor.connect() as conexion:
        plan = conexion.execute(
            text("EXPLAIN QUERY PLAN SELECT * FROM fact_comportamiento WHERE id_codigo = 1")
        ).all()
    detalle = " ".join(str(fila[-1]) for fila in plan)

    # Assert
    assert "idx_comportamiento_codigo" in detalle


@pytest.mark.parametrize("modulo", MODULOS_UI)
def test_ui_no_importa_repositorios(modulo: str) -> None:
    """CA-01: ningún módulo de UI importa una clase ``*Repository``."""
    # Arrange
    contenido = (RUTA_MODULOS / modulo / "ui.py").read_text(encoding="utf-8")

    # Act / Assert
    assert "Repository" not in contenido
    assert re.search(r"import\s+.*Repository", contenido) is None


def test_fachada_configuracion_delega_en_catalogos(motor: Engine) -> None:
    """Las fachadas encapsulan la infraestructura y exponen sus casos de uso."""
    # Arrange
    fachada = ConfiguracionFacade(engine=motor)

    # Act
    id_empresa = fachada.crear_empresa("Alcanos", "admin")
    empresas = fachada.listar_empresas()

    # Assert
    assert id_empresa == 1
    assert [empresa.nombre_empresa for empresa in empresas] == ["ALCANOS"]


def test_fachadas_exponen_casos_de_uso(motor: Engine) -> None:
    """Las cuatro fachadas de la spec 025 están disponibles y bien tipadas."""
    # Arrange / Act
    certificados = CertificadosFacade(engine=motor)
    comportamientos = ComportamientosFacade(engine=motor)
    reportes = ReportesFacade(engine=motor)
    configuracion = ConfiguracionFacade(engine=motor)

    # Assert
    assert hasattr(certificados, "registrar_evento")
    assert hasattr(certificados, "validar_certificado")
    assert hasattr(comportamientos, "generar_reincidencias")
    assert hasattr(reportes, "ejecutar_reporte")
    assert hasattr(configuracion, "actualizar_registros_seguros")


def test_backup_service_reporta_version_y_estado(tmp_path: Path) -> None:
    """R-03: el estado de versión se consulta sin SQL crudo en la UI."""
    # Arrange
    ruta_db = tmp_path / "operadores.db"
    engine = create_engine(f"sqlite:///{ruta_db}", poolclass=NullPool)
    with engine.begin() as conexion:
        conexion.execute(
            text(
                "CREATE TABLE dim_version_bd (id_version INTEGER PRIMARY KEY AUTOINCREMENT, "
                "archivo_origen TEXT, fecha_restauracion TEXT)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO dim_version_bd (archivo_origen, fecha_restauracion) "
                "VALUES (:origen, :fecha)"
            ),
            {"origen": "05-10-2026_V1.db", "fecha": "2026-10-05 10:00:00"},
        )
    engine.dispose()
    directorio = tmp_path / "backups"
    directorio.mkdir()
    (directorio / "05-10-2026_V1.db").write_bytes(b"respaldo")
    servicio = BackupService(directorio=directorio, origen_db=ruta_db)

    # Act
    version = servicio.version_actual()
    estado = servicio.estado_version()

    # Assert
    assert version is not None
    assert version.archivo_origen == "05-10-2026_V1.db"
    assert estado is not None
    assert estado.actualizado is True


def test_estado_version_detecta_backup_nuevo(tmp_path: Path) -> None:
    """R-03: con la carga inicial y un respaldo nuevo, el badge avisa."""
    # Arrange
    ruta_db = tmp_path / "operadores.db"
    engine = create_engine(f"sqlite:///{ruta_db}", poolclass=NullPool)
    with engine.begin() as conexion:
        conexion.execute(
            text(
                "CREATE TABLE dim_version_bd (id_version INTEGER PRIMARY KEY AUTOINCREMENT, "
                "archivo_origen TEXT, fecha_restauracion TEXT)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO dim_version_bd (archivo_origen, fecha_restauracion) "
                "VALUES (:origen, :fecha)"
            ),
            {"origen": ORIGEN_BD_INICIAL, "fecha": "2026-10-05 10:00:00"},
        )
    engine.dispose()
    directorio = tmp_path / "backups"
    directorio.mkdir()
    (directorio / "05-10-2026_V1.db").write_bytes(b"respaldo")
    servicio = BackupService(directorio=directorio, origen_db=ruta_db)

    # Act
    estado = servicio.estado_version()

    # Assert
    assert estado is not None
    assert estado.actualizado is False


def test_residuos_legacy_erradicados() -> None:
    """R-03: ``init_db.py`` y ``INSTRUCCIONES_OPENCODE.md`` ya no existen."""
    # Arrange / Act / Assert
    assert not (RAIZ / "src" / "certificado_operadores" / "init_db.py").exists()
    assert not (RAIZ / "INSTRUCCIONES_OPENCODE.md").exists()


def test_pyproject_declara_altair() -> None:
    """R-04: ``altair`` queda declarado como dependencia del proyecto."""
    # Arrange
    contenido = RUTA_PYPROJECT.read_text(encoding="utf-8")

    # Act / Assert
    assert "altair" in contenido
