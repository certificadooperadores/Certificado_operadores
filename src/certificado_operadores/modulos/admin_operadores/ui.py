"""Interfaz Streamlit del módulo de administración de operadores (specs 003 y 023).

Capa de presentación pura: captura la cédula, delega la búsqueda en
:class:`~certificado_operadores.facade.OperadoresFacade` y presenta un formulario
horizontal con los datos personales y los desplegables oficiales de empresa y
tipología. El botón **Guardar Operador** invoca
:meth:`~certificado_operadores.facade.OperadoresFacade.guardar_operador`, que
valida duplicados y persiste a través del repositorio. No contiene sentencias de
base de datos, ni conoce el motor ni el esquema: toda interacción con datos pasa
por el Facade.

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

from certificado_operadores.domain.models import (  # noqa: E402
    OperadorInfo,
    RegistroOperador,
)
from certificado_operadores.facade import OperadoresFacade  # noqa: E402

# --- Textos de la vista (constantes con nombre, sin cadenas quemadas) -------
ENCABEZADO_TITULO = "Administración de Operadores"
"""Título principal de la vista, sin emojis informales."""

ENCABEZADO_SUBTITULO = "Registra y consulta los operadores del sistema MIO."
"""Subtítulo descriptivo en gris neutro."""

ETIQUETA_CEDULA = "Número de Documento (Cédula)"
"""Etiqueta del campo de búsqueda por cédula."""

ETIQUETA_CEDULA_FORMULARIO = "Cédula"
"""Etiqueta del campo de cédula dentro del formulario de guardado."""

ETIQUETA_CODIGO = "Código Operador"
"""Etiqueta del código de operación (solo lectura)."""

ETIQUETA_NOMBRES = "Nombres"
"""Etiqueta del campo de nombres."""

ETIQUETA_APELLIDOS = "Apellidos"
"""Etiqueta del campo de apellidos."""

ETIQUETA_GENERO = "Género"
"""Etiqueta del desplegable de género."""

ETIQUETA_EMPRESA = "Empresa Concesionaria"
"""Etiqueta del desplegable de empresas concesionarias oficiales."""

ETIQUETA_TIPOLOGIA = "Tipología de Bus"
"""Etiqueta del desplegable de tipologías oficiales."""

ETIQUETA_GUARDAR = "Guardar Operador"
"""Rótulo del botón corporativo de guardado."""

MENSAJE_CEDULA_INVALIDA = "Ingresa una cédula numérica para consultar el operador."
"""Aviso mostrado cuando no hay una cédula válida para consultar."""

MENSAJE_OPERADOR_NUEVO = "Operador nuevo. Estado: Creación."
"""Aviso mostrado cuando la cédula no tiene operador asociado."""

SEPARADOR_ETIQUETA = " - "
"""Separador usado al componer las etiquetas legibles de los catálogos."""

SIN_OPCIONES = "Sin opciones disponibles"
"""Opción de relleno cuando un catálogo oficial llega vacío."""

CLAVE_FORMULARIO = "form_operador"
"""Identificador estable del formulario de operadores."""

CLAVE_ESTADO_USUARIO = "usuario"
"""Clave de sesión con el usuario autenticado (para auditoría del guardado)."""

# --- Género: códigos almacenados y etiquetas legibles -----------------------
GENERO_MASCULINO = "Masculino"
"""Etiqueta legible del género masculino."""

GENERO_FEMENINO = "Femenino"
"""Etiqueta legible del género femenino."""

GENERO_OTRO = "Otro"
"""Etiqueta legible del género "otro"."""

GENEROS: tuple[str, ...] = (GENERO_MASCULINO, GENERO_FEMENINO, GENERO_OTRO)
"""Opciones del desplegable oficial de género."""

CODIGO_GENERO: dict[str, str] = {
    GENERO_MASCULINO: "M",
    GENERO_FEMENINO: "F",
    GENERO_OTRO: "OTRO",
}
"""Traduce la etiqueta del desplegable al código almacenado en la base."""

ETIQUETA_GENERO_POR_CODIGO: dict[str, str] = {
    "M": GENERO_MASCULINO,
    "F": GENERO_FEMENINO,
    "OTRO": GENERO_OTRO,
}
"""Traduce el código almacenado de vuelta a la etiqueta legible del formulario."""

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


def construir_valores_formulario(
    operador: OperadorInfo | None, cedula: int | None = None
) -> dict[str, Any]:
    """Traduce el resultado del Facade a valores para autocompletar el formulario.

    Función pura (sin Streamlit ni base de datos) que centraliza el mapeo del
    DTO :class:`OperadorInfo` a los valores por defecto de la vista. Si el
    Facade devuelve ``None`` se reporta el estado de "Creación", cubriendo el
    caso de borde de la spec 003.

    Args:
        operador: Operador devuelto por el Facade, o ``None`` si no existe.
        cedula: Cédula consultada, usada para precargar el formulario en el caso
            de un operador nuevo.

    Returns:
        Diccionario con los valores del formulario y el estado calculado.
    """
    if operador is None:
        return {
            "estado": ESTADO_CREACION,
            "cedula": _texto_opcional(cedula),
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
        "cedula": _texto_opcional(operador.cedula),
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


def construir_registro(datos: dict[str, Any]) -> RegistroOperador:
    """Convierte los valores del formulario en el DTO :class:`RegistroOperador`.

    Función pura (sin Streamlit) que normaliza el texto capturado por la vista y
    lo traduce al DTO que consume la fachada. Una cédula inválida se representa
    como ``0`` para que la validación de obligatorios de la fachada la rechace.

    Args:
        datos: Valores crudos del formulario.

    Returns:
        El registro tipado listo para :meth:`OperadoresFacade.guardar_operador`.
    """
    return RegistroOperador(
        cedula=parsear_cedula(str(datos.get("cedula", ""))) or 0,
        nombres=str(datos.get("nombres", "")).strip(),
        primer_apellido=str(datos.get("primer_apellido", "")).strip(),
        segundo_apellido=str(datos.get("segundo_apellido", "")).strip(),
        genero=str(datos.get("genero", "")).strip(),
        id_empresa=_a_entero(datos.get("id_empresa")),
        id_perfil_tipologia=_a_entero(datos.get("id_perfil_tipologia")),
        codigo=_a_entero_opcional(datos.get("codigo")),
    )


def _a_entero(valor: Any) -> int:
    """Convierte un identificador opcional del formulario a entero.

    Args:
        valor: Valor escalar o ``None``.

    Returns:
        El entero del valor, o ``0`` si es ``None``.
    """
    return int(valor) if valor is not None else 0


def _a_entero_opcional(valor: Any) -> int | None:
    """Convierte un identificador opcional a entero o ``None``.

    Args:
        valor: Valor escalar o ``None``.

    Returns:
        El entero del valor, o ``None`` si es ``None``.
    """
    return int(valor) if valor is not None else None


def _indice_genero(genero: str) -> int:
    """Devuelve el índice de la opción de género dentro de :data:`GENEROS`.

    Args:
        genero: Código de género del operador (``M``/``F``/``OTRO``).

    Returns:
        La posición en :data:`GENEROS`; cero si el valor no es reconocido.
    """
    etiqueta = ETIQUETA_GENERO_POR_CODIGO.get(genero, GENERO_MASCULINO)
    return GENEROS.index(etiqueta)


def _indice_opcion(catalogo: dict[str, int], valor: Any) -> int:
    """Devuelve el índice de la opción cuyo identificador coincide con ``valor``.

    Args:
        catalogo: Mapa ordenado ``etiqueta -> identificador``.
        valor: Identificador buscado.

    Returns:
        La posición de la opción coincidente; cero si no hay coincidencia.
    """
    for indice, identificador in enumerate(catalogo.values()):
        if valor is not None and identificador == int(valor):
            return indice
    return 0


def _texto_opcional(valor: Any) -> str:
    """Convierte un identificador opcional a texto para mostrarlo en la vista.

    Args:
        valor: Valor escalar o ``None``.

    Returns:
        Cadena vacía si el valor es ``None``; su representación en caso contrario.
    """
    return "" if valor is None else str(valor)


def _render_encabezado() -> None:
    """Pinta el título y el subtítulo descriptivo del módulo."""
    st.title(ENCABEZADO_TITULO)
    st.markdown(
        f'<p class="subtitulo-metrocali">{ENCABEZADO_SUBTITULO}</p>',
        unsafe_allow_html=True,
    )


def _render_formulario(valores: dict[str, Any], fachada: OperadoresFacade) -> None:
    """Pinta el formulario horizontal y persiste el operador al guardar.

    Organiza los datos personales en una sola fila (spec 023, R-03), ofrece los
    desplegables oficiales de empresa y tipología cargados desde la fachada y, al
    pulsar **Guardar Operador**, construye el :class:`RegistroOperador` y delega
    el guardado en :meth:`OperadoresFacade.guardar_operador`.

    Args:
        valores: Diccionario producido por :func:`construir_valores_formulario`.
        fachada: Facade inyectado, usado para cargar catálogos y guardar.
    """
    catalogo_empresas = {
        f"{empresa.id_empresa}{SEPARADOR_ETIQUETA}{empresa.nombre_empresa}": empresa.id_empresa
        for empresa in fachada.listar_empresas()
    }
    catalogo_tipologias = {
        tipologia.descripcion: tipologia.id_perfil_tipologia
        for tipologia in fachada.listar_tipologias()
    }

    with st.form(CLAVE_FORMULARIO):
        st.markdown("##### Datos Personales")
        col_codigo, col_cedula, col_nombres, col_apellidos, col_genero = st.columns(5)
        with col_codigo:
            st.text_input(
                ETIQUETA_CODIGO,
                value=_texto_opcional(valores["codigo"]),
                disabled=True,
            )
        with col_cedula:
            cedula = st.text_input(ETIQUETA_CEDULA_FORMULARIO, value=str(valores["cedula"]))
        with col_nombres:
            nombres = st.text_input(ETIQUETA_NOMBRES, value=str(valores["nombres"]))
        with col_apellidos:
            apellidos = st.text_input(ETIQUETA_APELLIDOS, value=str(valores["primer_apellido"]))
        with col_genero:
            genero = st.selectbox(
                ETIQUETA_GENERO, GENEROS, index=_indice_genero(str(valores["genero"]))
            )

        st.markdown("##### Empresa y Asignación")
        col_empresa, col_tipologia = st.columns(2)
        with col_empresa:
            etiqueta_empresa = st.selectbox(
                ETIQUETA_EMPRESA,
                list(catalogo_empresas) or [SIN_OPCIONES],
                index=_indice_opcion(catalogo_empresas, valores["id_empresa"]),
            )
        with col_tipologia:
            etiqueta_tipologia = st.selectbox(
                ETIQUETA_TIPOLOGIA,
                list(catalogo_tipologias) or [SIN_OPCIONES],
                index=_indice_opcion(catalogo_tipologias, valores["id_perfil_tipologia"]),
            )

        guardar = st.form_submit_button(ETIQUETA_GUARDAR, type="primary")

    if not guardar:
        return

    registro = construir_registro(
        {
            "codigo": valores["codigo"],
            "cedula": cedula,
            "nombres": nombres,
            "primer_apellido": apellidos,
            "segundo_apellido": valores["segundo_apellido"],
            "genero": CODIGO_GENERO.get(genero, ""),
            "id_empresa": catalogo_empresas.get(etiqueta_empresa),
            "id_perfil_tipologia": catalogo_tipologias.get(etiqueta_tipologia),
        }
    )
    resultado = fachada.guardar_operador(registro, st.session_state.get(CLAVE_ESTADO_USUARIO, ""))
    if resultado.exito:
        st.success(resultado.mensaje)
    else:
        st.error(resultado.mensaje)


def _render_consulta(fachada: OperadoresFacade) -> None:
    """Captura la cédula, consulta el Facade y autocompleta el formulario.

    Args:
        fachada: Facade inyectado desde el punto de entrada de ``pages/``.
    """
    cedula = parsear_cedula(st.text_input(ETIQUETA_CEDULA, key="cedula_oper"))
    if cedula is None:
        st.info(MENSAJE_CEDULA_INVALIDA)
        return

    operador = fachada.obtener_operador_por_cedula(cedula)
    if operador is None:
        st.info(MENSAJE_OPERADOR_NUEVO)
    else:
        st.success(f"Operador encontrado: {operador.nombre_completo()} (Actualización).")

    _render_formulario(construir_valores_formulario(operador, cedula), fachada)


def render_page(fachada: OperadoresFacade | None = None) -> None:
    """Renderiza la pestaña de administración de operadores.

    Args:
        fachada: Facade a usar. Si es ``None`` se construye uno con la
            configuración por defecto; inyectarlo facilita las pruebas.
    """
    _render_encabezado()
    _render_consulta(fachada or OperadoresFacade())


__all__ = [
    "CODIGO_GENERO",
    "ESTADO_ACTUALIZACION",
    "ESTADO_CREACION",
    "GENEROS",
    "construir_registro",
    "construir_valores_formulario",
    "parsear_cedula",
    "render_page",
]
