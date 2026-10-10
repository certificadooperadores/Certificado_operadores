"""Pruebas de la interfaz de administración de operadores (spec 003).

Cubren las funciones puras que alimentan el formulario —sin depender de una
sesión de Streamlit ni de la base de datos— y las verificaciones estáticas de
los criterios de aceptación: la UI usa el Facade y no contiene sentencias de
base de datos. Todas las pruebas siguen el patrón AAA (*Arrange · Act · Assert*).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from certificado_operadores.domain.models import OperadorInfo
from certificado_operadores.facade import OperadoresFacade
from certificado_operadores.modulos.admin_operadores import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "2_Administracion_Operadores.py"


# --- parsear_cedula ---------------------------------------------------------
def test_parsear_cedula_numero_valido() -> None:
    """Un texto numérico se convierte en la cédula entera."""
    # Arrange
    texto = "  1002345  "

    # Act
    resultado = ui.parsear_cedula(texto)

    # Assert
    assert resultado == 1002345


def test_parsear_cedula_texto_vacio_devuelve_none() -> None:
    """Un campo vacío no produce cédula."""
    # Arrange / Act
    resultado = ui.parsear_cedula("   ")

    # Assert
    assert resultado is None


def test_parsear_cedula_texto_no_numerico_devuelve_none() -> None:
    """Un texto con letras no es una cédula válida."""
    # Arrange / Act
    resultado = ui.parsear_cedula("abc123")

    # Assert
    assert resultado is None


def test_parsear_cedula_cero_devuelve_none() -> None:
    """La cédula cero no es válida."""
    # Arrange / Act
    resultado = ui.parsear_cedula("0")

    # Assert
    assert resultado is None


# --- construir_valores_formulario -------------------------------------------
def test_construir_valores_estado_creacion_cuando_no_existe() -> None:
    """Sin operador (None) el formulario queda vacío y en estado Creación."""
    # Arrange / Act
    valores = ui.construir_valores_formulario(None)

    # Assert
    assert valores["estado"] == ui.ESTADO_CREACION
    assert valores["nombres"] == ""
    assert valores["primer_apellido"] == ""
    assert valores["codigo"] is None
    assert valores["id_empresa"] is None


def test_construir_valores_autocompleta_con_el_operador() -> None:
    """Con un operador del Facade el formulario se autocompleta."""
    # Arrange
    operador = OperadorInfo(
        codigo=5002,
        cedula=1002,
        nombres="Luis",
        primer_apellido="Rojas",
        segundo_apellido="Mora",
        genero="M",
        id_empresa=2,
        nombre_empresa="Bnm",
        id_perfil_tipologia=1,
        id_vigencia=1,
    )

    # Act
    valores = ui.construir_valores_formulario(operador)

    # Assert
    assert valores["estado"] == ui.ESTADO_ACTUALIZACION
    assert valores["nombres"] == "Luis"
    assert valores["primer_apellido"] == "Rojas"
    assert valores["segundo_apellido"] == "Mora"
    assert valores["genero"] == "M"
    assert valores["codigo"] == 5002
    assert valores["id_empresa"] == 2
    assert valores["nombre_empresa"] == "Bnm"


# --- Criterios de aceptación verificables (CA-01 y RNF-01) ------------------
def test_ui_importa_el_facade() -> None:
    """CA-01: la interfaz usa exactamente la clase OperadoresFacade."""
    # Arrange / Act
    facade_exportado = ui.OperadoresFacade

    # Assert
    assert facade_exportado is OperadoresFacade


def test_ui_no_contiene_sentencias_sql() -> None:
    """RNF-01: la interfaz no contiene sentencias SQL ni acceso directo a la BD."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8").upper()
    # Se busca la sentencia SQL (palabra + espacio), no cualquier subcadena:
    # ``st.selectbox`` o ``sys.path.append`` contienen "SELECT"/"INSERT" sin ser SQL.
    patron = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")
    acceso_directo = ("RUN_QUERY", "RUN_TRANSACTION")

    # Act
    sentencias = patron.findall(contenido)
    directos = [palabra for palabra in acceso_directo if palabra in contenido]

    # Assert
    assert sentencias == []
    assert directos == []


def test_pagina_usa_el_facade_y_render_page() -> None:
    """CA-01: la página importa el Facade y delega en ``render_page``."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "OperadoresFacade" in contenido
    assert "render_page" in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """CA-03: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")


# --- RF-01 / RF-02 / caso de borde: flujo de consulta ------------------------
class _FachadaFalsa:
    """Doble de :class:`OperadoresFacade` que registra las cédulas consultadas."""

    def __init__(self, operador: OperadorInfo | None) -> None:
        """Guarda el resultado que debe devolver la búsqueda."""
        self._operador = operador
        self.cedulas: list[int] = []

    def obtener_operador_por_cedula(self, cedula: int) -> OperadorInfo | None:
        """Registra la cédula recibida y devuelve el operador configurado."""
        self.cedulas.append(cedula)
        return self._operador


class _StreamlitFalso:
    """Doble mínimo de ``streamlit`` que captura los mensajes mostrados."""

    def __init__(self, cedula: str) -> None:
        """Configura el texto que devolverá el campo de cédula."""
        self._cedula = cedula
        self.mensajes_info: list[str] = []
        self.mensajes_success: list[str] = []

    def text_input(self, etiqueta: str, key: str | None = None) -> str:
        """Devuelve siempre la cédula configurada."""
        return self._cedula

    def info(self, mensaje: str) -> None:
        """Registra un mensaje informativo."""
        self.mensajes_info.append(mensaje)

    def success(self, mensaje: str) -> None:
        """Registra un mensaje de éxito."""
        self.mensajes_success.append(mensaje)


def _operador_de_ejemplo() -> OperadorInfo:
    """Construye un operador de ejemplo como el que entrega el Facade."""
    return OperadorInfo(
        codigo=5002,
        cedula=1002,
        nombres="Luis",
        primer_apellido="Rojas",
        segundo_apellido="Mora",
        genero="M",
        id_empresa=2,
        nombre_empresa="Bnm",
        id_perfil_tipologia=1,
        id_vigencia=1,
    )


def test_render_consulta_delega_la_busqueda_en_el_facade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-01/RF-02: la UI consulta el Facade y autocompleta con el OperadorInfo."""
    # Arrange
    fachada = _FachadaFalsa(_operador_de_ejemplo())
    st_falso = _StreamlitFalso("1002")
    capturado: list[dict[str, Any]] = []
    monkeypatch.setattr(ui, "st", st_falso)
    monkeypatch.setattr(
        ui, "_render_formulario", lambda valores, fachada: capturado.append(valores)
    )

    # Act
    ui._render_consulta(fachada)  # ty: ignore[invalid-argument-type]

    # Assert
    assert fachada.cedulas == [1002]
    assert capturado[0]["estado"] == ui.ESTADO_ACTUALIZACION
    assert capturado[0]["nombres"] == "Luis"
    assert capturado[0]["nombre_empresa"] == "Bnm"
    assert st_falso.mensajes_success, "Debe anunciar que encontró al operador."


def test_render_consulta_muestra_creacion_cuando_no_existe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso de borde: sin operador el Facade devuelve None y la UI muestra Creación."""
    # Arrange
    fachada = _FachadaFalsa(None)
    st_falso = _StreamlitFalso("99999999")
    capturado: list[dict[str, Any]] = []
    monkeypatch.setattr(ui, "st", st_falso)
    monkeypatch.setattr(
        ui, "_render_formulario", lambda valores, fachada: capturado.append(valores)
    )

    # Act
    ui._render_consulta(fachada)  # ty: ignore[invalid-argument-type]

    # Assert
    assert fachada.cedulas == [99999999]
    assert capturado[0]["estado"] == ui.ESTADO_CREACION
    assert any("Creación" in mensaje for mensaje in st_falso.mensajes_info)


def test_render_consulta_no_consulta_sin_cedula_valida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Una cédula inválida no llega al Facade."""
    # Arrange
    fachada = _FachadaFalsa(None)
    st_falso = _StreamlitFalso("abc")
    monkeypatch.setattr(ui, "st", st_falso)
    monkeypatch.setattr(ui, "_render_formulario", lambda valores, fachada: None)

    # Act
    ui._render_consulta(fachada)  # ty: ignore[invalid-argument-type]

    # Assert
    assert fachada.cedulas == []
    assert st_falso.mensajes_info
