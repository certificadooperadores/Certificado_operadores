"""Pruebas de la administración de backups (spec 005).

Cubren el servicio de infraestructura ``BackupService`` contra un directorio y
una base SQLite temporales (crear copia versionada, listar, proteger,
desproteger y eliminar), las funciones puras de la UI y las verificaciones
estáticas de los criterios de aceptación: el paquete existe, la UI no contiene
operaciones de sistema de archivos ni SQL, y la página ``1_Configuracion.py``
usa ``render_administrar_backups`` sin ``exec``. Todas siguen el patrón AAA
(*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from certificado_operadores.infra.backup_service import (
    BackupInfo,
    BackupProtegidoError,
    BackupService,
)
from certificado_operadores.modulos.administrar_backups import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "1_Configuracion.py"

_FECHA_FIJA = datetime(2026, 10, 9, 10, 30, 0)
"""Fecha inyectada al servicio para que el versionado sea determinista."""


def _crear_origen(ruta: Path) -> None:
    """Crea una base SQLite de prueba con una tabla y una fila.

    Args:
        ruta: Ruta donde se creará la base de datos.
    """
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute("CREATE TABLE prueba (id INTEGER PRIMARY KEY, valor TEXT)")
        conexion.execute("INSERT INTO prueba (valor) VALUES ('hola')")
        conexion.commit()
    finally:
        conexion.close()


def _leer_valor(ruta: Path) -> str:
    """Lee el valor de la tabla ``prueba`` de una base SQLite.

    Args:
        ruta: Ruta de la base de datos a consultar.

    Returns:
        El valor almacenado en la primera fila de la tabla ``prueba``.
    """
    conexion = sqlite3.connect(str(ruta))
    try:
        return str(conexion.execute("SELECT valor FROM prueba").fetchone()[0])
    finally:
        conexion.close()


@pytest.fixture
def origen(tmp_path: Path) -> Path:
    """Base SQLite temporal que se usará como origen de los respaldos."""
    ruta = tmp_path / "operadores.db"
    _crear_origen(ruta)
    return ruta


@pytest.fixture
def servicio(tmp_path: Path, origen: Path) -> BackupService:
    """Servicio de backups con directorio, origen y reloj inyectados."""
    return BackupService(
        directorio=tmp_path / "backups",
        origen_db=origen,
        reloj=lambda: _FECHA_FIJA,
    )


# --- Servicio: creación ------------------------------------------------------
def test_crear_backup_versiona_y_copia_consistente(servicio: BackupService) -> None:
    """RF-02: el respaldo se nombra DD-MM-AAAA_V1.db y copia los datos."""
    # Arrange / Act
    respaldo = servicio.crear_backup()

    # Assert
    assert respaldo.nombre == "09-10-2026_V1.db"
    assert respaldo.protegido is False
    assert respaldo.tamano_bytes > 0
    assert respaldo.ruta.is_file()
    assert _leer_valor(respaldo.ruta) == "hola"


def test_crear_backup_incrementa_la_version(servicio: BackupService) -> None:
    """RF-02: un segundo respaldo del mismo día se versiona como V2."""
    # Arrange
    servicio.crear_backup()

    # Act
    segundo = servicio.crear_backup()

    # Assert
    assert segundo.nombre == "09-10-2026_V2.db"


def test_crear_backup_sin_origen_falla(tmp_path: Path) -> None:
    """RF-02: crear un respaldo sin base de origen lanza ``FileNotFoundError``."""
    # Arrange
    servicio = BackupService(directorio=tmp_path / "backups", origen_db=tmp_path / "no_existe.db")

    # Act / Assert
    with pytest.raises(FileNotFoundError):
        servicio.crear_backup()


def test_copia_de_archivo_no_sqlite_se_degrada(tmp_path: Path) -> None:
    """El servicio copia el archivo aunque no sea una base SQLite válida."""
    # Arrange
    origen = tmp_path / "respaldo.txt"
    origen.write_text("contenido plano", encoding="utf-8")
    servicio = BackupService(
        directorio=tmp_path / "backups", origen_db=origen, reloj=lambda: _FECHA_FIJA
    )

    # Act
    respaldo = servicio.crear_backup()

    # Assert
    assert respaldo.ruta.read_text(encoding="utf-8") == "contenido plano"


# --- Servicio: listado -------------------------------------------------------
def test_listar_sin_directorio_devuelve_vacio(tmp_path: Path) -> None:
    """RF-01: si el directorio no existe, el listado está vacío."""
    # Arrange
    servicio = BackupService(directorio=tmp_path / "inexistente", origen_db=tmp_path / "x.db")

    # Act / Assert
    assert servicio.listar_backups() == []


def test_listar_ordena_y_marca_estado(servicio: BackupService) -> None:
    """RF-01: el listado incluye nombre, tamaño, fecha y estado de protección."""
    # Arrange
    primero = servicio.crear_backup()
    segundo = servicio.crear_backup()
    servicio.proteger(primero.nombre)

    # Act
    respaldos = servicio.listar_backups()

    # Assert
    nombres = [respaldo.nombre for respaldo in respaldos]
    assert "09-10-2026_V1.protegido.db" in nombres
    assert segundo.nombre in nombres
    protegido = next(r for r in respaldos if r.protegido)
    assert protegido.nombre == "09-10-2026_V1.protegido.db"
    assert all(respaldo.tamano_bytes > 0 for respaldo in respaldos)


def test_directorio_respeta_variable_de_entorno(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """RNF-01: el directorio se resuelve desde la variable de entorno."""
    # Arrange
    destino = tmp_path / "configurado"
    monkeypatch.setenv("BACKUPS_DIR", str(destino))

    # Act
    servicio = BackupService(origen_db=tmp_path / "x.db")

    # Assert
    assert servicio.directorio == destino


# --- Servicio: proteger / desproteger ---------------------------------------
def test_proteger_y_desproteger_cambia_la_extension(servicio: BackupService) -> None:
    """RF-03: proteger añade ``.protegido`` y desproteger lo quita."""
    # Arrange
    respaldo = servicio.crear_backup()

    # Act
    protegido = servicio.proteger(respaldo.nombre)

    # Assert
    assert protegido.nombre == "09-10-2026_V1.protegido.db"
    assert protegido.protegido is True
    assert not (servicio.directorio / respaldo.nombre).exists()
    assert (servicio.directorio / protegido.nombre).exists()

    # Act
    desprotegido = servicio.desproteger(protegido.nombre)

    # Assert
    assert desprotegido.nombre == "09-10-2026_V1.db"
    assert desprotegido.protegido is False
    assert not (servicio.directorio / protegido.nombre).exists()


def test_proteger_dos_veces_es_idempotente(servicio: BackupService) -> None:
    """RF-03: proteger un respaldo ya protegido no cambia el nombre."""
    # Arrange
    respaldo = servicio.crear_backup()
    servicio.proteger(respaldo.nombre)

    # Act
    de_nuevo = servicio.proteger("09-10-2026_V1.protegido.db")

    # Assert
    assert de_nuevo.nombre == "09-10-2026_V1.protegido.db"


# --- Servicio: eliminación ---------------------------------------------------
def test_eliminar_desprotegido_borra_el_archivo(servicio: BackupService) -> None:
    """RF-04: un respaldo desprotegido se elimina físicamente."""
    # Arrange
    respaldo = servicio.crear_backup()

    # Act
    servicio.eliminar(respaldo.nombre)

    # Assert
    assert not respaldo.ruta.exists()
    assert servicio.listar_backups() == []


def test_eliminar_protegido_esta_prohibido(servicio: BackupService) -> None:
    """RF-04: un respaldo protegido no se puede eliminar."""
    # Arrange
    respaldo = servicio.crear_backup()
    protegido = servicio.proteger(respaldo.nombre)

    # Act / Assert
    with pytest.raises(BackupProtegidoError):
        servicio.eliminar(protegido.nombre)
    assert protegido.ruta.exists()


def test_eliminar_inexistente_falla(servicio: BackupService) -> None:
    """RF-04: eliminar un respaldo inexistente lanza ``FileNotFoundError``."""
    # Arrange / Act / Assert
    with pytest.raises(FileNotFoundError):
        servicio.eliminar("no_existe.db")


# --- UI: funciones puras -----------------------------------------------------
def test_filas_backups_mapea_columnas_legibles() -> None:
    """La tabla de la UI expone columnas legibles."""
    # Arrange
    respaldo = BackupInfo(
        nombre="09-10-2026_V1.db",
        ruta=Path("backups/09-10-2026_V1.db"),
        tamano_bytes=2 * 1024 * 1024,
        fecha_modificacion=_FECHA_FIJA,
        protegido=False,
    )

    # Act
    filas = ui.filas_backups([respaldo])

    # Assert
    assert filas == [
        {
            "Nombre del Archivo": "09-10-2026_V1.db",
            "Tamaño (MB)": 2.0,
            "Fecha de Modificación": "2026-10-09 10:30:00",
            "Estado": ui.ETIQUETA_DESPROTEGIDO,
        }
    ]


def test_filas_backups_marca_protegido() -> None:
    """La tabla distingue un respaldo protegido."""
    # Arrange
    respaldo = BackupInfo(
        nombre="09-10-2026_V1.protegido.db",
        ruta=Path("backups/09-10-2026_V1.protegido.db"),
        tamano_bytes=1024,
        fecha_modificacion=_FECHA_FIJA,
        protegido=True,
    )

    # Act
    filas = ui.filas_backups([respaldo])

    # Assert
    assert filas[0]["Estado"] == ui.ETIQUETA_PROTEGIDO


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_administrar_backups_existe() -> None:
    """CA-01: el paquete expone ``render_administrar_backups``."""
    # Arrange / Act
    from certificado_operadores.modulos.administrar_backups import render_administrar_backups

    # Assert
    assert callable(render_administrar_backups)


def test_ui_sin_operaciones_de_sistema_ni_sql() -> None:
    """CA-03/RNF-01: la UI no maneja archivos ni contiene SQL."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8").upper()
    operaciones = ("OS.REMOVE", "OS.RENAME", "OS.LISTDIR", "SHUTIL", "SQLITE3")
    patron_sql = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")
    acceso_directo = ("RUN_QUERY", "RUN_TRANSACTION")

    # Act
    encontradas = [operacion for operacion in operaciones if operacion in contenido]
    sentencias = patron_sql.findall(contenido)
    directos = [palabra for palabra in acceso_directo if palabra in contenido]

    # Assert
    assert encontradas == []
    assert sentencias == []
    assert directos == []


def test_pagina_usa_render_administrar_backups_sin_exec() -> None:
    """CA-02/RNF-02: la página importa la función y no usa ``exec`` para backups."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_administrar_backups" in contenido
    assert 'exec(open("modulos/2_Administrar_Backups.py")' not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")
