"""Interfaz Streamlit del módulo de gestión de usuarios.

Capa de presentación pura (spec 004): muestra el listado de cuentas y delega el
alta y la modificación en
:class:`~certificado_operadores.facade_usuarios.UsuariosFacade`. No contiene
sentencias de base de datos ni conoce el motor ni el esquema: toda interacción
con datos pasa por el Facade.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# --- Ajuste de ruta de importación -------------------------------------------
# Streamlit agrega al ``sys.path`` la carpeta del script principal
# (``src/certificado_operadores``), no su padre (``src``). Para importar el
# paquete ``certificado_operadores`` dentro de la app —sin depender del
# directorio de trabajo— se agrega ``src`` una sola vez. En las pruebas ya viene
# en el ``path`` (``pythonpath = ["src"]``), por lo que el ajuste es un no-op.
_RUTA_SRC = Path(__file__).resolve().parents[3]
if str(_RUTA_SRC) not in sys.path:
    sys.path.append(str(_RUTA_SRC))

from certificado_operadores.domain.usuarios import (  # noqa: E402
    ESTADOS_USUARIO,
    UsuarioInfo,
    roles_asignables,
)
from certificado_operadores.facade_usuarios import UsuariosFacade  # noqa: E402

AYUDA_CONTRASENA_OPCIONAL = "Deje en blanco si no desea cambiar la contraseña."
"""Texto de ayuda del campo de contraseña opcional del formulario de edición."""


def filas_usuarios(usuarios: list[UsuarioInfo]) -> list[dict[str, object]]:
    """Traduce los DTOs de usuario a filas para la tabla de Streamlit.

    Args:
        usuarios: Cuentas devueltas por el Facade.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": usuario.id_usuario,
            "Usuario": usuario.usuario,
            "Rol": usuario.rol,
            "Estado": usuario.estado,
            "Registro": usuario.fecha_registro,
        }
        for usuario in usuarios
    ]


def nombres_usuarios(usuarios: list[UsuarioInfo]) -> list[str]:
    """Extrae los nombres de usuario para el selector de edición.

    Args:
        usuarios: Cuentas devueltas por el Facade.

    Returns:
        La lista de nombres de usuario en el mismo orden recibido.
    """
    return [usuario.usuario for usuario in usuarios]


def _render_encabezado() -> None:
    """Pinta el título y la ayuda del módulo."""
    st.title("Gestión de Usuarios del Sistema")
    st.markdown("Administra los accesos, roles y contraseñas de la plataforma.")


def _render_listado(usuarios: list[UsuarioInfo]) -> None:
    """Muestra el listado de usuarios registrados.

    Args:
        usuarios: Cuentas devueltas por el Facade.
    """
    st.subheader("Usuarios Registrados")
    st.dataframe(filas_usuarios(usuarios), use_container_width=True)


def _render_alta(
    fachada: UsuariosFacade, roles_disponibles: tuple[str, ...], usuario_solicitante: str
) -> None:
    """Pinta y procesa el formulario de creación de usuarios.

    Args:
        fachada: Facade inyectado desde el punto de entrada.
        roles_disponibles: Roles que puede asignar el solicitante.
        usuario_solicitante: Usuario que ejecuta la acción (para auditoría).
    """
    st.subheader("Agregar Nuevo Usuario")
    with st.form("form_nuevo_usuario"):
        nuevo_usuario = st.text_input("Nombre de Usuario").strip().lower()
        nueva_contrasena = st.text_input("Contraseña", type="password")
        nuevo_rol = st.selectbox("Rol", roles_disponibles)

        if st.form_submit_button("Crear Usuario"):
            resultado = fachada.crear_usuario(
                nuevo_usuario,
                nueva_contrasena,
                nuevo_rol,
                usuario_solicitante=usuario_solicitante,
            )
            if resultado.exito:
                st.success(resultado.mensaje)
            else:
                st.error(resultado.mensaje)


def _render_modificacion(
    fachada: UsuariosFacade,
    usuarios: list[UsuarioInfo],
    roles_disponibles: tuple[str, ...],
    rol_solicitante: str,
    usuario_solicitante: str,
) -> None:
    """Pinta y procesa el formulario de modificación de usuarios.

    Args:
        fachada: Facade inyectado desde el punto de entrada.
        usuarios: Cuentas devueltas por el Facade.
        roles_disponibles: Roles que puede asignar el solicitante.
        rol_solicitante: Rol de quien ejecuta la operación.
        usuario_solicitante: Usuario que ejecuta la operación.
    """
    st.subheader("Modificar Usuario Existente")
    with st.form("form_mod_usuario"):
        usuario_seleccionado = st.selectbox("Seleccione Usuario", nombres_usuarios(usuarios))
        nuevo_rol = st.selectbox("Nuevo Rol", roles_disponibles)
        nuevo_estado = st.selectbox("Estado", ESTADOS_USUARIO)
        nueva_contrasena = st.text_input(
            "Nueva Contraseña (Opcional)",
            type="password",
            help=AYUDA_CONTRASENA_OPCIONAL,
        )

        if st.form_submit_button("Actualizar Usuario") and usuario_seleccionado:
            resultado = fachada.modificar_usuario(
                usuario_seleccionado,
                nuevo_rol,
                nuevo_estado,
                nueva_contrasena or None,
                rol_solicitante=rol_solicitante,
                usuario_solicitante=usuario_solicitante,
            )
            if resultado.exito:
                st.success(resultado.mensaje)
            else:
                st.error(resultado.mensaje)


def render_gestion_usuarios(fachada: UsuariosFacade | None = None) -> None:
    """Renderiza la pestaña completa de gestión de usuarios.

    Args:
        fachada: Facade a usar. Si es ``None`` se construye uno con la
            configuración por defecto; inyectarlo facilita las pruebas.
    """
    fachada = fachada or UsuariosFacade()
    rol_solicitante = st.session_state.get("rol", "")
    usuario_solicitante = st.session_state.get("usuario", "")

    _render_encabezado()
    usuarios = fachada.listar_usuarios()
    _render_listado(usuarios)

    st.markdown("---")
    columna_alta, columna_modificacion = st.columns(2)
    with columna_alta:
        _render_alta(fachada, roles_asignables(rol_solicitante), usuario_solicitante)
    with columna_modificacion:
        _render_modificacion(
            fachada,
            usuarios,
            roles_asignables(rol_solicitante),
            rol_solicitante,
            usuario_solicitante,
        )
