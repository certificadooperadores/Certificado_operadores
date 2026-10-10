"""Pruebas de la autenticación y el login (spec 011).

Cubren el caso de uso ``UsuariosFacade.autenticar`` contra una base SQLite
temporal (éxito, contraseña incorrecta, usuario inexistente e inactivo), el
método de credenciales del repositorio y los criterios de aceptación estáticos
del punto de entrada ``Inicio.py``: sin SQL, sin acceso directo a la base de
datos y sin criptografía, delegando en ``UsuariosFacade``. Todas las pruebas
siguen el patrón AAA (*Arrange · Act · Assert*).

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
    MENSAJE_CAMPOS_OBLIGATORIOS,
    MENSAJE_CONTRASENA_INCORRECTA,
    MENSAJE_LOGIN_EXITOSO,
    MENSAJE_USUARIO_INACTIVO,
    MENSAJE_USUARIO_NO_EXISTE,
    ROL_GESTOR,
    ROL_SUPER_ADMINISTRADOR,
    CredencialesUsuario,
    ResultadoAutenticacion,
)
from certificado_operadores.facade_usuarios import UsuariosFacade
from certificado_operadores.infra.seguridad import hashear_contrasena
from certificado_operadores.infra.usuarios_repository import UsuariosRepository

_RUTA_INICIO = Path(__file__).resolve().parents[1] / "src" / "certificado_operadores" / "Inicio.py"

# --- Esquema mínimo para las pruebas de autenticación ------------------------
_ESQUEMA = """
    CREATE TABLE dim_usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        rol TEXT NOT NULL,
        estado TEXT NOT NULL,
        fecha_registro TEXT
    );
"""


def _crear_esquema(motor: Engine) -> None:
    """Crea la tabla mínima de usuarios."""
    with motor.begin() as conexion:
        conexion.execute(text(_ESQUEMA))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta tres cuentas: administrador activo, gestor activo e inactivo."""
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
                {
                    "usuario": "inactivo",
                    "password_hash": hashear_contrasena("clave123"),
                    "rol": ROL_GESTOR,
                    "estado": ESTADO_INACTIVO,
                },
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de prueba."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_autenticacion.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar_datos(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def fachada(motor_sqlite: Engine) -> UsuariosFacade:
    """Fachada de usuarios configurada con el motor SQLite de prueba."""
    return UsuariosFacade(engine=motor_sqlite)


# --- Fachada: autenticación --------------------------------------------------
def test_autenticar_exitoso_devuelve_rol(fachada: UsuariosFacade) -> None:
    """RF-01: credenciales válidas autentican y devuelven el rol."""
    # Arrange / Act
    resultado = fachada.autenticar("admin", "admin123")

    # Assert
    assert isinstance(resultado, ResultadoAutenticacion)
    assert resultado.exito is True
    assert resultado.mensaje == MENSAJE_LOGIN_EXITOSO
    assert resultado.rol == ROL_SUPER_ADMINISTRADOR


def test_autenticar_password_incorrecta(fachada: UsuariosFacade) -> None:
    """RF-04: una contraseña que no coincide reporta error."""
    # Arrange / Act
    resultado = fachada.autenticar("admin", "clave-mala")

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_CONTRASENA_INCORRECTA
    assert resultado.rol == ""


def test_autenticar_usuario_inexistente(fachada: UsuariosFacade) -> None:
    """RF-02: un usuario que no existe reporta error."""
    # Arrange / Act
    resultado = fachada.autenticar("fantasma", "cualquiera")

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_USUARIO_NO_EXISTE


def test_autenticar_usuario_inactivo_no_verifica_password(fachada: UsuariosFacade) -> None:
    """RF-03: una cuenta inactiva se rechaza aunque la contraseña sea correcta."""
    # Arrange / Act
    resultado = fachada.autenticar("inactivo", "clave123")

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_USUARIO_INACTIVO


def test_autenticar_campos_obligatorios(fachada: UsuariosFacade) -> None:
    """Los campos usuario y contraseña son obligatorios."""
    # Arrange / Act
    resultado = fachada.autenticar("", "")

    # Assert
    assert resultado.exito is False
    assert resultado.mensaje == MENSAJE_CAMPOS_OBLIGATORIOS


def test_autenticar_gestor_devuelve_su_rol(fachada: UsuariosFacade) -> None:
    """RF-01: el rol devuelto corresponde a la cuenta autenticada."""
    # Arrange / Act
    resultado = fachada.autenticar("gestor", "gestor123")

    # Assert
    assert resultado.exito is True
    assert resultado.rol == ROL_GESTOR


def test_autenticar_usa_el_verificador_inyectado(motor_sqlite: Engine) -> None:
    """La fachada permite inyectar el verificador (facilita las pruebas)."""
    # Arrange
    llamadas: list[tuple[str, str]] = []

    def verificador(contrasena: str, hash_almacenado: str) -> bool:
        llamadas.append((contrasena, hash_almacenado))
        return True

    fachada = UsuariosFacade(engine=motor_sqlite, verificador=verificador)

    # Act
    resultado = fachada.autenticar("admin", "lo-que-sea")

    # Assert
    assert resultado.exito is True
    assert llamadas and llamadas[0][0] == "lo-que-sea"


# --- Repositorio: credenciales ----------------------------------------------
def test_repositorio_obtener_para_autenticacion(motor_sqlite: Engine) -> None:
    """El repositorio devuelve las credenciales del usuario como DTO."""
    # Arrange
    repositorio = UsuariosRepository(engine=motor_sqlite)

    # Act
    credenciales = repositorio.obtener_para_autenticacion("admin")

    # Assert
    assert isinstance(credenciales, CredencialesUsuario)
    assert credenciales.usuario == "admin"
    assert credenciales.rol == ROL_SUPER_ADMINISTRADOR
    assert credenciales.estado == ESTADO_ACTIVO


def test_repositorio_obtener_para_autenticacion_inexistente(motor_sqlite: Engine) -> None:
    """El repositorio devuelve ``None`` cuando el usuario no existe."""
    # Arrange
    repositorio = UsuariosRepository(engine=motor_sqlite)

    # Act
    credenciales = repositorio.obtener_para_autenticacion("fantasma")

    # Assert
    assert credenciales is None


# --- Inicialización resiliente (spec 012) ------------------------------------
def test_usuarios_repository_auto_crea_tablas_y_admin_en_motor_vacio(tmp_path: Path) -> None:
    """CA-01/CA-02: en un motor vacío se crean las tablas y se siembra ``admin``."""
    # Arrange
    motor = create_engine(f"sqlite:///{tmp_path / 'vacio_tablas.db'}", poolclass=NullPool)

    try:
        # Act
        repositorio = UsuariosRepository(engine=motor)
        administrador = repositorio.obtener_usuario("admin")

        # Assert
        assert administrador is not None
        assert administrador.usuario == "admin"
        assert administrador.rol == ROL_SUPER_ADMINISTRADOR
        assert administrador.estado == ESTADO_ACTIVO
        with motor.connect() as conexion:
            tablas = {
                fila[0]
                for fila in conexion.execute(
                    text("SELECT name FROM sqlite_master WHERE type = 'table'")
                )
            }
        assert "dim_usuarios" in tablas
        assert "log_auditoria" in tablas
    finally:
        motor.dispose()


def test_fachada_autentica_admin_sembrado_en_motor_vacio(tmp_path: Path) -> None:
    """CA-03/RF-04: la fachada autentica al ``admin`` sembrado sobre un motor nuevo."""
    # Arrange
    motor = create_engine(f"sqlite:///{tmp_path / 'vacio_fachada.db'}", poolclass=NullPool)

    try:
        # Act
        fachada = UsuariosFacade(engine=motor)
        resultado = fachada.autenticar("admin", "admin123")

        # Assert
        assert isinstance(resultado, ResultadoAutenticacion)
        assert resultado.exito is True
        assert resultado.mensaje == MENSAJE_LOGIN_EXITOSO
        assert resultado.rol == ROL_SUPER_ADMINISTRADOR
    finally:
        motor.dispose()


def test_asegurar_tablas_es_idempotente(tmp_path: Path) -> None:
    """RNF-02: invocar ``asegurar_tablas`` varias veces no duplica al administrador."""
    # Arrange
    motor = create_engine(f"sqlite:///{tmp_path / 'idempotente.db'}", poolclass=NullPool)
    repositorio = UsuariosRepository(engine=motor)

    try:
        # Act
        repositorio.asegurar_tablas()
        repositorio.asegurar_tablas()

        # Assert
        with motor.connect() as conexion:
            total = conexion.execute(text("SELECT COUNT(*) FROM dim_usuarios")).scalar_one()
        assert int(total) == 1
    finally:
        motor.dispose()


def test_log_auditoria_operativo_en_motor_vacio(tmp_path: Path) -> None:
    """RF-03: la tabla ``log_auditoria`` creada automáticamente admite escrituras."""
    # Arrange
    motor = create_engine(f"sqlite:///{tmp_path / 'auditoria.db'}", poolclass=NullPool)
    repositorio = UsuariosRepository(engine=motor)

    try:
        # Act
        repositorio.registrar_auditoria("admin", "Prueba", "detalle de prueba")

        # Assert
        with motor.connect() as conexion:
            total = conexion.execute(text("SELECT COUNT(*) FROM log_auditoria")).scalar_one()
        assert int(total) == 1
    finally:
        motor.dispose()


# --- Criterios de aceptación verificables ------------------------------------
def test_inicio_no_importa_base_de_datos_ni_criptografia() -> None:
    """CA-02/RNF-01: ``Inicio.py`` no accede a la BD ni a la criptografía."""
    # Arrange
    contenido = _RUTA_INICIO.read_text(encoding="utf-8")
    contenido_mayusculas = contenido.upper()
    patron_sql = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")

    # Act
    sentencias = patron_sql.findall(contenido_mayusculas)
    accesos_directos = ("RUN_QUERY", "RUN_TRANSACTION", "GET_ENGINE")

    # Assert
    assert sentencias == []
    assert "run_query" not in contenido
    assert "bcrypt" not in contenido
    assert all(acceso not in contenido_mayusculas for acceso in accesos_directos)


def test_inicio_delega_en_usuarios_facade() -> None:
    """CA-01/CA-02: el login invoca ``UsuariosFacade.autenticar``."""
    # Arrange
    contenido = _RUTA_INICIO.read_text(encoding="utf-8")

    # Act / Assert
    assert "UsuariosFacade" in contenido
    assert "autenticar(" in contenido


def test_inicio_persiste_sesion_solo_tras_exito() -> None:
    """RNF-02: la sesión se completa con los datos del resultado autenticado."""
    # Arrange
    contenido = _RUTA_INICIO.read_text(encoding="utf-8")

    # Act / Assert
    assert 'st.session_state["logged_in"] = True' in contenido
    assert 'st.session_state["rol"] = resultado.rol' in contenido


def test_inicio_compila_sin_errores_de_sintaxis() -> None:
    """CA-02: el punto de entrada es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_INICIO.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_INICIO), "exec")
