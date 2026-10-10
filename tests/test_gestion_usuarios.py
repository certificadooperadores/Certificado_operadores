"""Pruebas de la gestión de usuarios (spec 004).

Cubren tres frentes: las reglas puras del dominio, la fachada
``UsuariosFacade`` contra una base SQLite temporal (alta, modificación,
permisos y autoinactivación) y las verificaciones estáticas de los criterios de
aceptación: el paquete existe, la UI no contiene SQL y la página
``1_Configuracion.py`` usa ``render_gestion_usuarios`` sin ``exec``. Todas las
pruebas siguen el patrón AAA (*Arrange · Act · Assert*).

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

from certificado_operadores.domain.usuarios import (
    ESTADO_ACTIVO,
    ESTADO_INACTIVO,
    MENSAJE_NO_INACTIVAR_PROPIO,
    MENSAJE_SIN_PERMISO_SUPER_ADMIN,
    MENSAJE_USUARIO_EXISTE,
    ROL_ADMINISTRADOR,
    ROL_GESTOR,
    ROL_SUPER_ADMINISTRADOR,
    UsuarioInfo,
    puede_inactivar_usuario,
    puede_modificar_usuario,
    roles_asignables,
)
from certificado_operadores.facade_usuarios import UsuariosFacade
from certificado_operadores.infra.seguridad import hashear_contrasena, verificar_contrasena
from certificado_operadores.modulos.gestion_usuarios import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "1_Configuracion.py"

# --- Esquema mínimo para las pruebas de la fachada --------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        rol TEXT NOT NULL,
        estado TEXT NOT NULL,
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
    """Crea las tablas mínimas de usuarios y auditoría."""
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta dos cuentas de ejemplo (una Super Administrador y una Gestor)."""
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO dim_usuarios "
                "(usuario, password_hash, rol, estado, fecha_registro) VALUES "
                "(:usuario, :password_hash, :rol, :estado, '2026-01-01')"
            ),
            [
                {
                    "usuario": "admin",
                    "password_hash": hashear_contrasena("admin123"),
                    "rol": ROL_SUPER_ADMINISTRADOR,
                    "estado": ESTADO_ACTIVO,
                },
                {
                    "usuario": "gestor",
                    "password_hash": hashear_contrasena("gestor123"),
                    "rol": ROL_GESTOR,
                    "estado": ESTADO_ACTIVO,
                },
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de prueba."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_usuarios.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar_datos(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def fachada(motor_sqlite: Engine) -> UsuariosFacade:
    """Fachada de usuarios configurada con el motor SQLite de prueba."""
    return UsuariosFacade(engine=motor_sqlite)


def _hash_almacenado(motor: Engine, usuario: str) -> str:
    """Devuelve el hash de contraseña guardado para un usuario."""
    with motor.connect() as conexion:
        fila = conexion.execute(
            text("SELECT password_hash FROM dim_usuarios WHERE usuario = :usuario"),
            {"usuario": usuario},
        ).scalar_one()
    return str(fila)


def _total_auditoria(motor: Engine) -> int:
    """Cuenta las filas del log de auditoría."""
    with motor.connect() as conexion:
        return int(conexion.execute(text("SELECT COUNT(*) FROM log_auditoria")).scalar_one())


# --- Reglas puras del dominio ------------------------------------------------
def test_roles_asignables_admin_no_puede_asignar_super_admin() -> None:
    """Un Administrador no puede asignar el rol Super Administrador."""
    # Arrange / Act
    roles = roles_asignables(ROL_ADMINISTRADOR)

    # Assert
    assert ROL_SUPER_ADMINISTRADOR not in roles
    assert ROL_GESTOR in roles
    assert ROL_ADMINISTRADOR in roles


def test_roles_asignables_super_admin_incluye_su_rol() -> None:
    """Un Super Administrador puede asignar su propio rol."""
    # Arrange / Act
    roles = roles_asignables(ROL_SUPER_ADMINISTRADOR)

    # Assert
    assert ROL_SUPER_ADMINISTRADOR in roles


def test_puede_modificar_usuario_super_admin() -> None:
    """Un Super Administrador sí puede modificar cuentas de Super Administrador."""
    # Arrange / Act
    permitido = puede_modificar_usuario(ROL_SUPER_ADMINISTRADOR, ROL_SUPER_ADMINISTRADOR)

    # Assert
    assert permitido is True


def test_puede_modificar_usuario_gestor_protegido() -> None:
    """Un Administrador no puede modificar cuentas de Super Administrador."""
    # Arrange / Act
    permitido = puede_modificar_usuario(ROL_ADMINISTRADOR, ROL_SUPER_ADMINISTRADOR)

    # Assert
    assert permitido is False


def test_puede_inactivar_propia_cuenta_se_bloquea() -> None:
    """Un usuario no puede inactivar su propia cuenta."""
    # Arrange / Act
    permitido = puede_inactivar_usuario("admin", "admin", ESTADO_INACTIVO)

    # Assert
    assert permitido is False


def test_puede_inactivar_otra_cuenta_se_permite() -> None:
    """Inactivar la cuenta de otro usuario está permitido."""
    # Arrange / Act
    permitido = puede_inactivar_usuario("admin", "gestor", ESTADO_INACTIVO)

    # Assert
    assert permitido is True


# --- Fachada: listado --------------------------------------------------------
def test_listar_usuarios_devuelve_dtos_ordenados(fachada: UsuariosFacade) -> None:
    """RF-01: el listado devuelve los usuarios como DTOs ordenados por id."""
    # Arrange / Act
    usuarios = fachada.listar_usuarios()

    # Assert
    assert [usuario.usuario for usuario in usuarios] == ["admin", "gestor"]
    assert all(isinstance(usuario, UsuarioInfo) for usuario in usuarios)
    assert usuarios[0].rol == ROL_SUPER_ADMINISTRADOR


# --- Fachada: creación -------------------------------------------------------
def test_crear_usuario_exitoso_hashea_y_audita(
    fachada: UsuariosFacade, motor_sqlite: Engine
) -> None:
    """RF-02: crea el usuario, guarda el hash bcrypt y registra auditoría."""
    # Arrange / Act
    resultado = fachada.crear_usuario(
        "  NuevoGESTOR ", "secreta123", ROL_GESTOR, usuario_solicitante="admin"
    )

    # Assert
    assert resultado.exito is True
    creado = fachada.obtener_usuario("nuevogestor")
    assert creado is not None
    assert creado.estado == ESTADO_ACTIVO
    hash_guardado = _hash_almacenado(motor_sqlite, "nuevogestor")
    assert hash_guardado != "secreta123"
    assert verificar_contrasena("secreta123", hash_guardado) is True
    assert _total_auditoria(motor_sqlite) == 1


def test_crear_usuario_duplicado_se_rechaza(fachada: UsuariosFacade) -> None:
    """RF-02: no se permite crear un usuario que ya existe."""
    # Arrange / Act
    resultado = fachada.crear_usuario("admin", "otra", ROL_GESTOR)

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_USUARIO_EXISTE


def test_crear_usuario_sin_campos_se_rechaza(fachada: UsuariosFacade) -> None:
    """RF-02: usuario y contraseña son obligatorios."""
    # Arrange / Act
    resultado = fachada.crear_usuario("", "", ROL_GESTOR)

    # Assert
    assert resultado.exito is False


# --- Fachada: modificación ---------------------------------------------------
def test_modificar_usuario_cambia_rol_estado_y_password(
    fachada: UsuariosFacade, motor_sqlite: Engine
) -> None:
    """RF-03: modifica rol, estado y contraseña de una cuenta existente."""
    # Arrange / Act
    resultado = fachada.modificar_usuario(
        "gestor",
        ROL_ADMINISTRADOR,
        ESTADO_INACTIVO,
        "nuevaClave",
        rol_solicitante=ROL_SUPER_ADMINISTRADOR,
        usuario_solicitante="admin",
    )

    # Assert
    assert resultado.exito is True
    modificado = fachada.obtener_usuario("gestor")
    assert modificado is not None
    assert modificado.rol == ROL_ADMINISTRADOR
    assert modificado.estado == ESTADO_INACTIVO
    assert verificar_contrasena("nuevaClave", _hash_almacenado(motor_sqlite, "gestor")) is True


def test_modificar_usuario_sin_password_conserva_la_actual(
    fachada: UsuariosFacade, motor_sqlite: Engine
) -> None:
    """RF-03: sin nueva contraseña se conserva el hash actual."""
    # Arrange
    hash_previo = _hash_almacenado(motor_sqlite, "gestor")

    # Act
    resultado = fachada.modificar_usuario(
        "gestor",
        ROL_ADMINISTRADOR,
        ESTADO_ACTIVO,
        rol_solicitante=ROL_SUPER_ADMINISTRADOR,
        usuario_solicitante="admin",
    )

    # Assert
    assert resultado.exito is True
    assert _hash_almacenado(motor_sqlite, "gestor") == hash_previo


def test_modificar_usuario_super_admin_sin_permiso(fachada: UsuariosFacade) -> None:
    """RF-03: solo Super Administrador modifica cuentas de Super Administrador."""
    # Arrange / Act
    resultado = fachada.modificar_usuario(
        "admin",
        ROL_GESTOR,
        ESTADO_ACTIVO,
        rol_solicitante=ROL_ADMINISTRADOR,
        usuario_solicitante="gestor",
    )

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_SIN_PERMISO_SUPER_ADMIN


def test_modificar_usuario_autoinactivacion_bloqueada(fachada: UsuariosFacade) -> None:
    """RF-03: un usuario no puede inactivar su propia cuenta."""
    # Arrange / Act
    resultado = fachada.modificar_usuario(
        "admin",
        ROL_SUPER_ADMINISTRADOR,
        ESTADO_INACTIVO,
        rol_solicitante=ROL_SUPER_ADMINISTRADOR,
        usuario_solicitante="admin",
    )

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_NO_INACTIVAR_PROPIO


def test_modificar_usuario_inexistente_se_rechaza(fachada: UsuariosFacade) -> None:
    """RF-03: modificar un usuario inexistente devuelve error."""
    # Arrange / Act
    resultado = fachada.modificar_usuario(
        "fantasma",
        ROL_GESTOR,
        ESTADO_ACTIVO,
        rol_solicitante=ROL_SUPER_ADMINISTRADOR,
        usuario_solicitante="admin",
    )

    # Assert
    assert resultado.exito is False


# --- UI: funciones puras -----------------------------------------------------
def _usuario_de_ejemplo() -> UsuarioInfo:
    """Construye un usuario de ejemplo como el que entrega el Facade."""
    return UsuarioInfo(
        id_usuario=1,
        usuario="admin",
        rol=ROL_SUPER_ADMINISTRADOR,
        estado=ESTADO_ACTIVO,
        fecha_registro="2026-01-01",
    )


def test_filas_usuarios_mapea_columnas_legibles() -> None:
    """La tabla de la UI expone columnas legibles."""
    # Arrange
    usuarios = [_usuario_de_ejemplo()]

    # Act
    filas = ui.filas_usuarios(usuarios)

    # Assert
    assert filas == [
        {
            "ID": 1,
            "Usuario": "admin",
            "Rol": ROL_SUPER_ADMINISTRADOR,
            "Estado": ESTADO_ACTIVO,
            "Registro": "2026-01-01",
        }
    ]


def test_nombres_usuarios_extrae_los_nombres() -> None:
    """El selector de edición recibe solo los nombres de usuario."""
    # Arrange / Act
    nombres = ui.nombres_usuarios([_usuario_de_ejemplo()])

    # Assert
    assert nombres == ["admin"]


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_gestion_usuarios_existe() -> None:
    """CA-01: el paquete expone ``render_gestion_usuarios``."""
    # Arrange / Act
    from certificado_operadores.modulos.gestion_usuarios import render_gestion_usuarios

    # Assert
    assert callable(render_gestion_usuarios)


def test_ui_no_contiene_sentencias_sql() -> None:
    """CA-03/RNF-01: la UI no contiene SQL ni acceso directo a la base de datos."""
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


def test_pagina_usa_render_gestion_usuarios() -> None:
    """CA-02/RNF-02: la página importa la función y no usa ``exec`` para la pestaña 1."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_gestion_usuarios" in contenido
    assert 'exec(open("modulos/1_Gestion_Usuarios.py").read()' not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")


def test_fachada_usa_el_hasheador_inyectado(
    motor_sqlite: Engine,
) -> None:
    """La fachada permite inyectar el hasheador (facilita las pruebas)."""
    # Arrange
    fachada = UsuariosFacade(engine=motor_sqlite, hasheador=lambda texto: f"hash:{texto}")

    # Act
    fachada.crear_usuario("invitado", "clave", ROL_GESTOR)

    # Assert
    assert _hash_almacenado(motor_sqlite, "invitado") == "hash:clave"
