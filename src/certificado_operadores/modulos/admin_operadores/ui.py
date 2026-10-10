"""Interfaz Streamlit del módulo de administración de operadores.

Capa de presentación pura (spec 003): captura la cédula, delega la búsqueda en
:class:`~certificado_operadores.facade.OperadoresFacade` y autocompleta el
formulario con el DTO :class:`~certificado_operadores.domain.models.OperadorInfo`.
No contiene sentencias de base de datos, ni conoce el motor ni el esquema:
toda interacción con datos pasa por el Facade.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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

from certificado_operadores.domain.models import OperadorInfo  # noqa: E402
from certificado_operadores.facade import OperadoresFacade  # noqa: E402

GENEROS: tuple[str, ...] = ("", "M", "F", "OTRO")
"""Opciones de género aceptadas por el formulario."""

ESTADO_CREACION = "CREACION"
"""Estado del formulario cuando la cédula no tiene operador asociado."""

ESTADO_ACTUALIZACION = "ACTUALIZACION"
"""Estado del formulario cuando el operador ya existe y se autocompleta."""


def parsear_cedula(texto: str) -> int | None:
    """Convierte el texto ingresado en una cédula numérica.

    Args:
        texto: Contenido del campo de cédula.

    Returns:
        La cédula como entero positivo si el texto es un número válido, o
        ``None`` si está vacío, no es numérico o es cero.
    """
    limpio = (texto or "").strip()
    if not limpio.isdigit():
        return None
    numero = int(limpio)
    return numero if numero > 0 else None


def construir_valores_formulario(operador: OperadorInfo | None) -> dict[str, Any]:
    """Traduce el resultado del Facade a valores para autocompletar el formulario.

    Función pura (sin Streamlit ni base de datos) que centraliza el mapeo del
    DTO :class:`OperadorInfo` a los valores por defecto de la vista. Si el
    Facade devuelve ``None`` se reporta el estado de "Creación", cubriendo el
    caso de borde de la spec 003.

    Args:
        operador: Operador devuelto por el Facade, o ``None`` si no existe.

    Returns:
        Diccionario con los valores del formulario y el estado calculado.
    """
    if operador is None:
        return {
            "estado": ESTADO_CREACION,
            "nombres": "",
            "primer_apellido": "",
            "segundo_apellido": "",
            "genero": "",
            "codigo": None,
            "id_empresa": None,
            "nombre_empresa": "",
            "id_perfil_tipologia": None,
            "id_vigencia": None,
        }
    return {
        "estado": ESTADO_ACTUALIZACION,
        "nombres": operador.nombres,
        "primer_apellido": operador.primer_apellido,
        "segundo_apellido": operador.segundo_apellido,
        "genero": operador.genero,
        "codigo": operador.codigo,
        "id_empresa": operador.id_empresa,
        "nombre_empresa": operador.nombre_empresa,
        "id_perfil_tipologia": operador.id_perfil_tipologia,
        "id_vigencia": operador.id_vigencia,
    }


def _indice_genero(genero: str) -> int:
    """Devuelve el índice de la opción de género dentro de :data:`GENEROS`.

    Args:
        genero: Valor de género del operador (puede no estar en la lista).

    Returns:
        La posición en :data:`GENEROS`; cero si el valor no es reconocido.
    """
    return GENEROS.index(genero) if genero in GENEROS else 0


def _texto_opcional(valor: Any) -> str:
    """Convierte un identificador opcional a texto para mostrarlo en la vista.

    Args:
        valor: Valor escalar o ``None``.

    Returns:
        Cadena vacía si el valor es ``None``; su representación en caso contrario.
    """
    return "" if valor is None else str(valor)


def _render_encabezado() -> None:
    """Pinta el título, los estilos y la ayuda del módulo."""
    st.title("👨‍✈️ Administración de Operadores")
    st.markdown(
        "<style>input[type=number]::-webkit-outer-spin-button,"
        "input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}"
        "input[type=number]{-moz-appearance:textfield}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Consulta una cédula. Si el operador no existe, verás el estado de "
        "**Creación**; si ya existe, el formulario se autocompleta con sus datos."
    )


def _render_formulario(valores: dict[str, Any]) -> None:
    """Pinta el formulario autocompletado a partir de los valores resueltos.

    Args:
        valores: Diccionario producido por :func:`construir_valores_formulario`.
    """
    st.subheader("1. Datos Personales")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Nombres", value=str(valores["nombres"]))
        st.text_input("Primer Apellido", value=str(valores["primer_apellido"]))
        st.text_input("Segundo Apellido (Opcional)", value=str(valores["segundo_apellido"]))
    with col2:
        st.selectbox("Género", GENEROS, index=_indice_genero(str(valores["genero"])))
        st.text_input("Código de Operación", value=_texto_opcional(valores["codigo"]))

    st.subheader("2. Empresa y Tipología")
    col3, col4 = st.columns(2)
    with col3:
        st.text_input("Empresa", value=str(valores["nombre_empresa"]))
        st.text_input("ID Empresa", value=_texto_opcional(valores["id_empresa"]))
    with col4:
        st.text_input("ID Tipología", value=_texto_opcional(valores["id_perfil_tipologia"]))
        st.text_input("ID Vigencia", value=_texto_opcional(valores["id_vigencia"]))

    st.caption(
        "🔎 Vista de consulta y autocompletado (spec 003). La edición y el "
        "guardado se incorporan en un ciclo posterior."
    )


def _render_consulta(fachada: OperadoresFacade) -> None:
    """Captura la cédula, consulta el Facade y autocompleta el formulario.

    Args:
        fachada: Facade inyectado desde el punto de entrada de ``pages/``.
    """
    cedula = parsear_cedula(st.text_input("Número de Documento (Cédula)", key="cedula_oper"))
    if cedula is None:
        st.info("Ingresa una cédula numérica para consultar el operador.")
        return

    operador = fachada.obtener_operador_por_cedula(cedula)
    if operador is None:
        st.info("✨ Operador Nuevo. Estado: **Creación**.")
    else:
        st.success(f"Operador encontrado: **{operador.nombre_completo()}** (Actualización).")

    _render_formulario(construir_valores_formulario(operador))


def render_page(fachada: OperadoresFacade | None = None) -> None:
    """Renderiza la pestaña de administración de operadores.

    Args:
        fachada: Facade a usar. Si es ``None`` se construye uno con la
            configuración por defecto; inyectarlo facilita las pruebas.
    """
    _render_encabezado()
    _render_consulta(fachada or OperadoresFacade())
