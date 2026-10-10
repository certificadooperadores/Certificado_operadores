"""Fachada de casos de uso de usuarios (patrón Facade).

Expone las operaciones de lectura y mutación de cuentas —listar, autenticar,
crear y modificar— delegando toda la persistencia en
:class:`~certificado_operadores.infra.usuarios_repository.UsuariosRepository` y
aplicando las reglas puras del dominio. La UI (incluida Streamlit) debe invocar
**únicamente** esta fachada:

    UI → Facade → Dominio → Infraestructura

La fachada no ejecuta SQL ni conoce el esquema: solo orquesta.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from certificado_operadores.domain.usuarios import (
    ESTADO_ACTIVO,
    MENSAJE_CAMPOS_OBLIGATORIOS,
    MENSAJE_CONTRASENA_INCORRECTA,
    MENSAJE_LOGIN_EXITOSO,
    MENSAJE_NO_INACTIVAR_PROPIO,
    MENSAJE_SIN_PERMISO_SUPER_ADMIN,
    MENSAJE_USUARIO_ACTUALIZADO,
    MENSAJE_USUARIO_CREADO,
    MENSAJE_USUARIO_EXISTE,
    MENSAJE_USUARIO_INACTIVO,
    MENSAJE_USUARIO_NO_EXISTE,
    ResultadoAutenticacion,
    ResultadoOperacion,
    UsuarioInfo,
    puede_inactivar_usuario,
    puede_modificar_usuario,
)
from certificado_operadores.infra.seguridad import hashear_contrasena, verificar_contrasena
from certificado_operadores.infra.usuarios_repository import UsuariosRepository

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class UsuariosFacade:
    """Fachada única de gestión de usuarios del sistema.

    Agrupa los casos de uso de cuentas de usuario, de modo que ninguna vista
    conozca el motor, el SQL ni el esquema. Delega la totalidad del acceso a
    datos en :class:`UsuariosRepository` y aplica las reglas de autorización del
    dominio. El motor y la función de hashing se inyectan para facilitar las
    pruebas.
    """

    def __init__(
        self,
        engine: Engine | None = None,
        hasheador: Callable[[str], str] = hashear_contrasena,
        verificador: Callable[[str, str], bool] = verificar_contrasena,
    ) -> None:
        """Inicializa la fachada.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
            hasheador: Función que convierte una contraseña en texto plano a su
                hash. Por defecto usa ``bcrypt``.
            verificador: Función que compara una contraseña en texto plano con un
                hash almacenado. Por defecto usa ``bcrypt``; se inyecta para
                facilitar las pruebas.
        """
        self._repositorio = UsuariosRepository(engine)
        self._hasheador = hasheador
        self._verificador = verificador

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado a la fachada (inyectado o por defecto)."""
        return self._repositorio.motor

    def listar_usuarios(self) -> list[UsuarioInfo]:
        """Lista todas las cuentas de usuario del sistema.

        Returns:
            La lista de :class:`UsuarioInfo` ordenada por identificador.
        """
        return self._repositorio.listar_usuarios()

    def obtener_usuario(self, usuario: str) -> UsuarioInfo | None:
        """Consulta una cuenta de usuario por su nombre.

        Args:
            usuario: Nombre de usuario a buscar.

        Returns:
            El :class:`UsuarioInfo` correspondiente, o ``None`` si no existe.
        """
        return self._repositorio.obtener_usuario(usuario)

    def autenticar(self, usuario: str, contrasena: str) -> ResultadoAutenticacion:
        """Autentica una cuenta a partir de sus credenciales.

        Orquesta el caso de uso de inicio de sesión: valida los campos
        obligatorios, recupera las credenciales seguras del repositorio, verifica
        que la cuenta esté activa y compara la contraseña con el hash almacenado
        mediante la capa de seguridad. No expone el hash ni ejecuta SQL.

        Args:
            usuario: Nombre de usuario ingresado.
            contrasena: Contraseña en texto plano ingresada.

        Returns:
            El :class:`ResultadoAutenticacion`; ``exito`` es ``True`` solo si la
            cuenta existe, está activa y la contraseña coincide. En ese caso,
            ``rol`` contiene el rol de la cuenta autenticada.
        """
        if not usuario or not contrasena:
            return ResultadoAutenticacion(False, MENSAJE_CAMPOS_OBLIGATORIOS)

        credenciales = self._repositorio.obtener_para_autenticacion(usuario)
        if credenciales is None:
            return ResultadoAutenticacion(False, MENSAJE_USUARIO_NO_EXISTE)
        if credenciales.estado != ESTADO_ACTIVO:
            return ResultadoAutenticacion(False, MENSAJE_USUARIO_INACTIVO)
        if not self._verificador(contrasena, credenciales.password_hash):
            return ResultadoAutenticacion(False, MENSAJE_CONTRASENA_INCORRECTA)
        return ResultadoAutenticacion(True, MENSAJE_LOGIN_EXITOSO, credenciales.rol)

    def crear_usuario(
        self, usuario: str, contrasena: str, rol: str, *, usuario_solicitante: str = ""
    ) -> ResultadoOperacion:
        """Crea una nueva cuenta con validación de existencia previa.

        Normaliza el nombre (minúsculas, sin espacios extremos), valida que los
        campos obligatorios estén presentes, comprueba que el usuario no exista
        y persiste la contraseña hasheada con ``bcrypt``.

        Args:
            usuario: Nombre de usuario propuesto.
            contrasena: Contraseña en texto plano.
            rol: Rol a asignar.
            usuario_solicitante: Usuario que ejecuta la acción (para auditoría).

        Returns:
            El :class:`ResultadoOperacion` con el mensaje para la interfaz.
        """
        usuario_normalizado = (usuario or "").strip().lower()
        if not usuario_normalizado or not contrasena:
            return ResultadoOperacion(False, MENSAJE_CAMPOS_OBLIGATORIOS)
        if self._repositorio.existe_usuario(usuario_normalizado):
            return ResultadoOperacion(False, MENSAJE_USUARIO_EXISTE)

        self._repositorio.crear_usuario(
            usuario_normalizado,
            self._hasheador(contrasena),
            rol,
            ESTADO_ACTIVO,
        )
        if usuario_solicitante:
            self._repositorio.registrar_auditoria(
                usuario_solicitante,
                "Crear Usuario",
                f"Usuario: {usuario_normalizado}, Rol: {rol}",
            )
        return ResultadoOperacion(True, MENSAJE_USUARIO_CREADO)

    def modificar_usuario(
        self,
        usuario: str,
        rol: str,
        estado: str,
        contrasena: str | None = None,
        *,
        rol_solicitante: str = "",
        usuario_solicitante: str = "",
    ) -> ResultadoOperacion:
        """Modifica rol, estado y, opcionalmente, la contraseña de una cuenta.

        Aplica las reglas de negocio: solo un ``Super Administrador`` puede
        modificar (o asignar) cuentas con ese rol, y ningún usuario puede
        inactivar su propia cuenta.

        Args:
            usuario: Nombre de la cuenta a modificar.
            rol: Nuevo rol.
            estado: Nuevo estado.
            contrasena: Nueva contraseña en texto plano; si es ``None`` o vacía
                se conserva la actual.
            rol_solicitante: Rol de quien ejecuta la operación.
            usuario_solicitante: Usuario que ejecuta la operación (para auditoría
                y regla de autoinactivación).

        Returns:
            El :class:`ResultadoOperacion` con el mensaje para la interfaz.
        """
        objetivo = self._repositorio.obtener_usuario(usuario)
        if objetivo is None:
            return ResultadoOperacion(False, MENSAJE_USUARIO_NO_EXISTE)
        if not puede_modificar_usuario(rol_solicitante, objetivo.rol):
            return ResultadoOperacion(False, MENSAJE_SIN_PERMISO_SUPER_ADMIN)
        if not puede_modificar_usuario(rol_solicitante, rol):
            return ResultadoOperacion(False, MENSAJE_SIN_PERMISO_SUPER_ADMIN)
        if not puede_inactivar_usuario(usuario_solicitante, usuario, estado):
            return ResultadoOperacion(False, MENSAJE_NO_INACTIVAR_PROPIO)

        hash_nuevo = self._hasheador(contrasena) if contrasena else None
        self._repositorio.actualizar_usuario(usuario, rol, estado, hash_nuevo)
        if usuario_solicitante:
            self._repositorio.registrar_auditoria(
                usuario_solicitante,
                "Modificar Usuario",
                f"Usuario: {usuario}, Nuevo rol: {rol}, Estado: {estado}",
            )
        return ResultadoOperacion(True, MENSAJE_USUARIO_ACTUALIZADO)


__all__ = ["UsuariosFacade"]
