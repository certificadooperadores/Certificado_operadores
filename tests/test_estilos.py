"""Pruebas de los estilos institucionales de Metrocali (spec 023).

Verifican la paleta del tema global, la resolución del logo oficial y la
inyección de estilos (CSS y logo) con un doble de Streamlit. Todas las pruebas
siguen el patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from pathlib import Path

from certificado_operadores import estilos

_RUTA_CONFIG = Path(estilos.__file__).resolve().parents[2] / ".streamlit" / "config.toml"

_COLORES_CONFIG = (
    'primaryColor = "#046BD2"',
    'backgroundColor = "#FFFFFF"',
    'secondaryBackgroundColor = "#F8FAFC"',
    'textColor = "#111827"',
)


class _StreamlitFalso:
    """Doble mínimo de Streamlit que registra el CSS y el logo publicados."""

    def __init__(self) -> None:
        """Inicializa el registro de llamadas."""
        self.css: str | None = None
        self.logo_ruta: str | None = None

    def markdown(self, cuerpo: str, unsafe_allow_html: bool = False) -> None:
        """Registra el bloque CSS inyectado."""
        self.css = cuerpo

    def logo(self, ruta: str) -> None:
        """Registra la ruta del logo publicado."""
        self.logo_ruta = ruta


# --- CA-01: paleta del tema global ------------------------------------------
def test_config_declara_la_paleta_clara_oficial() -> None:
    """CA-01: el tema global usa los colores institucionales de Metrocali."""
    # Arrange
    contenido = _RUTA_CONFIG.read_text(encoding="utf-8")

    # Act / Assert
    for color in _COLORES_CONFIG:
        assert color in contenido


def test_css_ancho_fluido_sin_max_width() -> None:
    """CA-01 (spec 024): el contenedor principal no restringe el ancho a 1200px."""
    # Arrange
    css = estilos._CSS_METROCALI

    # Act / Assert
    assert "max-width: none;" in css
    assert "max-width: 1200px" not in css
    assert "padding-left: 2.5rem;" in css
    assert "padding-right: 2.5rem;" in css


# --- CA-02: logo institucional ----------------------------------------------
def test_ruta_logo_por_defecto_apunta_al_asset_oficial() -> None:
    """CA-02: la ruta por defecto es el logo oficial versionado."""
    # Arrange / Act
    ruta = estilos.ruta_logo()

    # Assert
    assert ruta.name == estilos.NOMBRE_ARCHIVO_LOGO
    assert ruta.exists()


def test_ruta_logo_respeta_la_variable_de_entorno(monkeypatch, tmp_path: Path) -> None:
    """La ruta del logo puede sobrescribirse por variable de entorno."""
    # Arrange
    personalizada = tmp_path / "otro.png"
    monkeypatch.setenv(estilos.VARIABLE_ENTORNO_LOGO, str(personalizada))

    # Act
    ruta = estilos.ruta_logo()

    # Assert
    assert ruta == personalizada


# --- Inyección de estilos ----------------------------------------------------
def test_inyectar_estilos_publica_css_y_logo(monkeypatch, tmp_path: Path) -> None:
    """La inyección aplica el CSS y muestra el logo en la barra lateral."""
    # Arrange
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"png")
    streamlit_falso = _StreamlitFalso()
    monkeypatch.setattr(estilos, "st", streamlit_falso)
    monkeypatch.setattr(estilos, "ruta_logo", lambda: logo)

    # Act
    estilos.inyectar_estilos_metrocali()

    # Assert
    assert streamlit_falso.css is not None
    assert estilos.COLOR_PRIMARIO in streamlit_falso.css
    assert estilos.COLOR_BORDE in streamlit_falso.css
    assert streamlit_falso.logo_ruta == str(logo)


def test_inyectar_estilos_sin_logo_no_publica_imagen(monkeypatch, tmp_path: Path) -> None:
    """Si el logo no existe, solo se inyecta el CSS sin fallar."""
    # Arrange
    streamlit_falso = _StreamlitFalso()
    monkeypatch.setattr(estilos, "st", streamlit_falso)
    monkeypatch.setattr(estilos, "ruta_logo", lambda: tmp_path / "no_existe.png")

    # Act
    estilos.inyectar_estilos_metrocali()

    # Assert
    assert streamlit_falso.css is not None
    assert streamlit_falso.logo_ruta is None
