"""Repositorio de usuarios del sistema (capa de infraestructura).

Encapsula **todo** el acceso a datos de la tabla ``dim_usuarios`` (y el registro
de auditoría) mediante SQLAlchemy. Concentra las constantes SQL y la ejecución
contra el motor inyectado, devolviendo DTOs de dominio para que la interfaz no
conozca el esquema ni el motor.

Todas las consultas usan conexiones administradas por contexto y parámetros
enlazados (nunca SQL construido con datos del usuario).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from certificado_operadores.domain.usuarios import CredencialesUsuario, UsuarioInfo

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine, RowMapping


# --- Consultas SQL (parámetros enlazados, sin concatenar datos) -------------
_SQL_LISTAR = text(
    """
    SELECT id_usuario, usuario, rol, estado, fecha_registro
    FROM dim_usuarios
    ORDER BY id_usuario
    """
)

_SQL_OBTENER = text(
    """
    SELECT id_usuario, usuario, rol, estado, fecha_registro
    FROM dim_usuarios
    WHERE usuario = :usuario
    """
)

_SQL_EXISTE = text("SELECT COUNT(*) FROM dim_usuarios WHERE usuario = :usuario")

# Consulta de credenciales: incluye el hash (dato sensible) solo para la capa de
# autenticación; nunca se devuelve a la vista como ``UsuarioInfo``.
_SQL_CREDENCIALES = text(
    """
    SELECT usuario, password_hash, rol, estado
    FROM dim_usuarios
    WHERE usuario = :usuario
    """
)

_SQL_CREAR = text(
    """
    INSERT INTO dim_usuarios (usuario, password_hash, rol, estado)
    VALUES (:usuario, :password_hash, :rol, :estado)
    """
)

_SQL_ACTUALIZAR_CON_PASSWORD = text(
    """
    UPDATE dim_usuarios
    SET rol = :rol, estado = :estado, password_hash = :password_hash
    WHERE usuario = :usuario
    """
)

_SQL_ACTUALIZAR_SIN_PASSWORD = text(
    """
    UPDATE dim_usuarios
    SET rol = :rol, estado = :estado
    WHERE usuario = :usuario
    """
)

_SQL_AUDITORIA = text(
    """
    INSERT INTO log_auditoria (usuario, accion, detalles)
    VALUES (:usuario, :accion, :detalles)
    """
)


def _mapear_usuario(fila: RowMapping) -> UsuarioInfo:
    """Mapea una fila de ``dim_usuarios`` al DTO de dominio.

    Args:
        fila: Fila devuelta por SQLAlchemy.

    Returns:
        El :class:`UsuarioInfo` construido a partir de la fila.
    """
    return UsuarioInfo(
        id_usuario=int(fila["id_usuario"]),
        usuario=str(fila["usuario"]),
        rol=str(fila["rol"]),
        estado=str(fila["estado"]),
        fecha_registro=str(fila["fecha_registro"] or ""),
    )


def _mapear_credenciales(fila: RowMapping) -> CredencialesUsuario:
    """Mapea una fila de credenciales al DTO de dominio.

    Args:
        fila: Fila devuelta por SQLAlchemy con ``usuario``, ``password_hash``,
            ``rol`` y ``estado``.

    Returns:
        El :class:`CredencialesUsuario` construido a partir de la fila.
    """
    return CredencialesUsuario(
        usuario=str(fila["usuario"]),
        password_hash=str(fila["password_hash"]),
        rol=str(fila["rol"]),
        estado=str(fila["estado"]),
    )


class UsuariosRepository:
    """Repositorio de cuentas de usuario sobre la base de datos.

    Concentra toda la ejecución de SQLAlchemy. El motor se inyecta (por defecto
    se resuelve de forma perezosa desde
    :func:`certificado_operadores.db.get_engine`) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa el repositorio.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._engine = engine

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado al repositorio (inyectado o por defecto)."""
        if self._engine is None:
            # Import perezoso: evita cargar Streamlit cuando las pruebas inyectan motor.
            from certificado_operadores.db import get_engine

            self._engine = get_engine()
        return self._engine

    def listar_usuarios(self) -> list[UsuarioInfo]:
        """Lista todas las cuentas de usuario ordenadas por identificador.

        Returns:
            La lista de :class:`UsuarioInfo`; vacía si no hay usuarios.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR).mappings().all()
        return [_mapear_usuario(fila) for fila in filas]

    def obtener_usuario(self, usuario: str) -> UsuarioInfo | None:
        """Consulta una cuenta de usuario por su nombre.

        Args:
            usuario: Nombre de usuario a buscar.

        Returns:
            El :class:`UsuarioInfo` correspondiente, o ``None`` si no existe.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_OBTENER, {"usuario": usuario}).mappings().first()
        return None if fila is None else _mapear_usuario(fila)

    def obtener_para_autenticacion(self, usuario: str) -> CredencialesUsuario | None:
        """Consulta las credenciales de una cuenta para validar el inicio de sesión.

        Consulta parametrizada y de solo lectura que devuelve el hash y el estado
        necesarios para autenticar; la comparación de la contraseña ocurre en la
        capa de seguridad (``bcrypt``), nunca aquí.

        Args:
            usuario: Nombre de usuario a buscar.

        Returns:
            El :class:`CredencialesUsuario` correspondiente, o ``None`` si la
            cuenta no existe.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(_SQL_CREDENCIALES, {"usuario": usuario}).mappings().first()
        return None if fila is None else _mapear_credenciales(fila)

    def existe_usuario(self, usuario: str) -> bool:
        """Indica si una cuenta con ese nombre ya existe.

        Args:
            usuario: Nombre de usuario a buscar.

        Returns:
            ``True`` si ya existe una cuenta con ese nombre.
        """
        with self.motor.connect() as conexion:
            total = conexion.execute(_SQL_EXISTE, {"usuario": usuario}).scalar_one()
        return int(total) > 0

    def crear_usuario(self, usuario: str, password_hash: str, rol: str, estado: str) -> None:
        """Inserta una nueva cuenta de usuario.

        Args:
            usuario: Nombre de usuario único.
            password_hash: Contraseña ya hasheada (bcrypt).
            rol: Rol asignado a la cuenta.
            estado: Estado inicial de la cuenta.
        """
        with self.motor.begin() as conexion:
            conexion.execute(
                _SQL_CREAR,
                {
                    "usuario": usuario,
                    "password_hash": password_hash,
                    "rol": rol,
                    "estado": estado,
                },
            )

    def actualizar_usuario(
        self, usuario: str, rol: str, estado: str, password_hash: str | None = None
    ) -> None:
        """Actualiza rol, estado y, opcionalmente, la contraseña de una cuenta.

        Args:
            usuario: Nombre de la cuenta a modificar.
            rol: Nuevo rol.
            estado: Nuevo estado.
            password_hash: Nuevo hash de contraseña; si es ``None`` se conserva
                la contraseña actual.
        """
        parametros = {"usuario": usuario, "rol": rol, "estado": estado}
        sentencia = _SQL_ACTUALIZAR_SIN_PASSWORD
        if password_hash is not None:
            sentencia = _SQL_ACTUALIZAR_CON_PASSWORD
            parametros["password_hash"] = password_hash
        with self.motor.begin() as conexion:
            conexion.execute(sentencia, parametros)

    def registrar_auditoria(self, usuario: str, accion: str, detalles: str) -> None:
        """Registra una acción en el log de auditoría.

        Args:
            usuario: Usuario que ejecuta la acción.
            accion: Nombre de la acción realizada.
            detalles: Detalle libre de la acción.
        """
        with self.motor.begin() as conexion:
            conexion.execute(
                _SQL_AUDITORIA,
                {"usuario": usuario, "accion": accion, "detalles": detalles},
            )
