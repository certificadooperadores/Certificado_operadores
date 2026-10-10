"""Modelos y reglas de negocio del dominio de usuarios del sistema.

Capa de **dominio**: define los DTO :class:`UsuarioInfo`,
:class:`CredencialesUsuario` y :class:`ResultadoAutenticacion`, las constantes de
roles y estados, los mensajes de resultado (incluidos los del inicio de sesión) y
las reglas puras de autorización sobre las cuentas. No conoce SQLAlchemy, la base
de datos ni la interfaz gráfica:

    UI → Facade → Dominio → Infraestructura

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Constantes del dominio de usuarios -------------------------------------
ROL_SUPER_ADMINISTRADOR = "Super Administrador"
"""Rol con privilegios totales sobre la plataforma."""

ROL_ADMINISTRADOR = "Administrador"
"""Rol de administración sin privilegios sobre cuentas de Super Administrador."""

ROL_GESTOR = "Gestor"
"""Rol operativo básico de la plataforma."""

ROLES_ASIGNABLES_BASE: tuple[str, ...] = (ROL_GESTOR, ROL_ADMINISTRADOR)
"""Roles que puede asignar cualquier administrador."""

ESTADO_ACTIVO = "Activo"
"""Estado de una cuenta habilitada para iniciar sesión."""

ESTADO_INACTIVO = "Inactivo"
"""Estado de una cuenta deshabilitada."""

ESTADOS_USUARIO: tuple[str, ...] = (ESTADO_ACTIVO, ESTADO_INACTIVO)
"""Estados válidos de una cuenta de usuario."""

# --- Mensajes de resultado (constantes, sin texto quemado en la UI) ---------
MENSAJE_CAMPOS_OBLIGATORIOS = "Usuario y contraseña son obligatorios."
MENSAJE_USUARIO_EXISTE = "El usuario ya existe."
MENSAJE_USUARIO_NO_EXISTE = "El usuario no existe."
MENSAJE_USUARIO_CREADO = "Usuario creado exitosamente. Recarga la página para actualizar la tabla."
MENSAJE_USUARIO_ACTUALIZADO = (
    "Usuario actualizado exitosamente. Recarga la página para ver los cambios."
)
MENSAJE_SIN_PERMISO_SUPER_ADMIN = (
    "No tienes permisos para modificar cuentas de Super Administrador."
)
MENSAJE_NO_INACTIVAR_PROPIO = "No puedes inactivar tu propio usuario."

# --- Mensajes de autenticación (inicio de sesión) ---------------------------
MENSAJE_LOGIN_EXITOSO = "Inicio de sesión exitoso."
"""Mensaje devuelto cuando las credenciales son válidas y la cuenta está activa."""

MENSAJE_USUARIO_INACTIVO = "El usuario está inactivo."
"""Mensaje devuelto cuando la cuenta existe pero no está habilitada."""

MENSAJE_CONTRASENA_INCORRECTA = "Contraseña incorrecta."
"""Mensaje devuelto cuando la contraseña no coincide con el hash almacenado."""


@dataclass(frozen=True)
class UsuarioInfo:
    """Datos de una cuenta de usuario del sistema (``dim_usuarios``)."""

    id_usuario: int
    usuario: str
    rol: str
    estado: str
    fecha_registro: str


@dataclass(frozen=True)
class ResultadoOperacion:
    """Resultado de una operación de escritura, con mensaje listo para la UI."""

    exito: bool
    mensaje: str


@dataclass(frozen=True)
class CredencialesUsuario:
    """Credenciales de una cuenta necesarias para validar el inicio de sesión.

    Se mantiene separado de :class:`UsuarioInfo` porque incluye el
    ``password_hash`` (dato sensible) y solo lo consume la capa de autenticación,
    nunca la vista.
    """

    usuario: str
    password_hash: str
    rol: str
    estado: str


@dataclass(frozen=True)
class ResultadoAutenticacion:
    """Resultado de intentar autenticar una cuenta del sistema.

    Attributes:
        exito: ``True`` si las credenciales son válidas y la cuenta está activa.
        mensaje: Mensaje listo para mostrar en la interfaz.
        rol: Rol de la cuenta autenticada; vacío si la autenticación falló.
    """

    exito: bool
    mensaje: str
    rol: str = ""


def roles_asignables(rol_solicitante: str) -> tuple[str, ...]:
    """Devuelve los roles que puede asignar un solicitante.

    Se aplica la regla de negocio: solo un ``Super Administrador`` puede asignar
    el rol ``Super Administrador``.

    Args:
        rol_solicitante: Rol de quien realiza la operación.

    Returns:
        Los roles asignables según el rol del solicitante.
    """
    if rol_solicitante == ROL_SUPER_ADMINISTRADOR:
        return (*ROLES_ASIGNABLES_BASE, ROL_SUPER_ADMINISTRADOR)
    return ROLES_ASIGNABLES_BASE


def puede_modificar_usuario(rol_solicitante: str, rol_objetivo: str) -> bool:
    """Indica si un solicitante puede modificar una cuenta con cierto rol.

    Regla de negocio: solo un ``Super Administrador`` puede modificar (o asignar)
    cuentas con el rol ``Super Administrador``.

    Args:
        rol_solicitante: Rol de quien realiza la operación.
        rol_objetivo: Rol actual o propuesto de la cuenta destino.

    Returns:
        ``True`` si la modificación está permitida; ``False`` en caso contrario.
    """
    return rol_objetivo != ROL_SUPER_ADMINISTRADOR or rol_solicitante == ROL_SUPER_ADMINISTRADOR


def puede_inactivar_usuario(
    usuario_solicitante: str, usuario_objetivo: str, estado_nuevo: str
) -> bool:
    """Indica si un solicitante puede dejar una cuenta en el estado propuesto.

    Regla de negocio: un usuario no puede inactivar su propia cuenta.

    Args:
        usuario_solicitante: Nombre del usuario que realiza la operación.
        usuario_objetivo: Nombre de la cuenta que se desea modificar.
        estado_nuevo: Estado propuesto para la cuenta destino.

    Returns:
        ``True`` si la operación está permitida; ``False`` si intenta inactivar
        su propia cuenta.
    """
    return not (usuario_solicitante == usuario_objetivo and estado_nuevo == ESTADO_INACTIVO)
