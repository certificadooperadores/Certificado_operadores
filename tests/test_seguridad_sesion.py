"""Pruebas de la persistencia de sesión con tokens firmados (spec 013).

Cubren la generación, validación, caducidad (20 minutos = 1200 s) y renovación de
los tokens HMAC-SHA256 de ``infra.seguridad``, la orquestación de
``UsuariosFacade`` y la restauración/expiración de la sesión en la capa de UI
``ui_sesion`` (restauración desde la URL, renovación, refresco de datos y cierre
de sesión). Todas las pruebas siguen el patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from certificado_operadores import ui_sesion
from certificado_operadores.domain.usuarios import ROL_SUPER_ADMINISTRADOR
from certificado_operadores.facade_usuarios import UsuariosFacade
from certificado_operadores.infra.seguridad import (
    MOTIVO_EXPIRADO,
    MOTIVO_INVALIDO,
    MOTIVO_VALIDO,
    SEGUNDOS_INACTIVIDAD_SESION,
    VARIABLE_ENTORNO_CLAVE_SESION,
    generar_token_sesion,
    validar_token_sesion,
)

_ROL = ROL_SUPER_ADMINISTRADOR
_MARCA_BASE = 1_000_000.0
_RUTA_INICIO = Path(__file__).resolve().parents[1] / "src" / "certificado_operadores" / "Inicio.py"
_RUTA_PAGINAS = _RUTA_INICIO.parent / "pages"
_RUTA_UI_SESION = Path(ui_sesion.__file__).resolve()

_PAGINAS = ("1_Configuracion.py", "2_Administracion_Operadores.py", "3_Reportes.py")


@pytest.fixture
def fachada() -> UsuariosFacade:
    """Fachada de usuarios sobre un motor SQLite en memoria."""
    return UsuariosFacade(engine=create_engine("sqlite:///:memory:"))


# --- Tokens: generación y validación (spec 013) ------------------------------
def test_token_valido_dentro_de_los_20_minutos() -> None:
    """CA-01: un token con menos de 20 minutos de inactividad es válido."""
    # Arrange
    token = generar_token_sesion("admin", _ROL, timestamp=_MARCA_BASE)

    # Act
    valido, usuario, rol, motivo = validar_token_sesion(token, ahora=_MARCA_BASE + 1199)

    # Assert
    assert valido is True
    assert usuario == "admin"
    assert rol == _ROL
    assert motivo == MOTIVO_VALIDO


def test_token_valido_justo_en_el_limite_de_1200_segundos() -> None:
    """CA-01: exactamente 1200 segundos de inactividad aún es válido."""
    # Arrange
    token = generar_token_sesion("admin", _ROL, timestamp=_MARCA_BASE)

    # Act
    valido, _, _, motivo = validar_token_sesion(
        token, ahora=_MARCA_BASE + SEGUNDOS_INACTIVIDAD_SESION
    )

    # Assert
    assert SEGUNDOS_INACTIVIDAD_SESION == 1200
    assert valido is True
    assert motivo == MOTIVO_VALIDO


def test_token_expira_pasados_1201_segundos() -> None:
    """CA-01: un token con más de 20 minutos de inactividad se declara expirado."""
    # Arrange
    token = generar_token_sesion("admin", _ROL, timestamp=_MARCA_BASE)

    # Act
    valido, usuario, rol, motivo = validar_token_sesion(token, ahora=_MARCA_BASE + 1201)

    # Assert
    assert valido is False
    assert usuario is None
    assert rol is None
    assert motivo == MOTIVO_EXPIRADO


def test_token_manipulado_en_la_firma_se_rechaza() -> None:
    """RNF-01: alterar la firma invalida el token (imposible falsificar)."""
    # Arrange
    token = generar_token_sesion("admin", _ROL, timestamp=_MARCA_BASE)
    payload, firma = token.split(".")
    firma_alterada = ("0" if firma[0] != "0" else "1") + firma[1:]

    # Act
    valido, usuario, rol, motivo = validar_token_sesion(
        f"{payload}.{firma_alterada}", ahora=_MARCA_BASE
    )

    # Assert
    assert valido is False
    assert usuario is None and rol is None
    assert motivo == MOTIVO_INVALIDO


def test_token_manipulado_en_el_payload_se_rechaza() -> None:
    """RNF-01: cambiar el rol sin re-firmar invalida el token."""
    # Arrange
    token = generar_token_sesion("admin", _ROL, timestamp=_MARCA_BASE)
    payload, firma = token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))
    datos["rol"] = "Super Administrador falsificado"
    payload_alterado = base64.urlsafe_b64encode(
        json.dumps(datos, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")

    # Act
    valido, _, _, motivo = validar_token_sesion(f"{payload_alterado}.{firma}", ahora=_MARCA_BASE)

    # Assert
    assert valido is False
    assert motivo == MOTIVO_INVALIDO


@pytest.mark.parametrize("token", ["", "sin-punto", "a.b.c", "###.###"])
def test_tokens_mal_formados_se_rechazan(token: str) -> None:
    """CA-01: tokens vacíos, mal formados o corruptos se rechazan."""
    # Arrange / Act
    valido, usuario, rol, motivo = validar_token_sesion(token)

    # Assert
    assert valido is False
    assert usuario is None and rol is None
    assert motivo == MOTIVO_INVALIDO


def test_token_firmado_con_otra_clave_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    """RNF-01: la firma depende de la clave secreta configurada."""
    # Arrange
    monkeypatch.setenv(VARIABLE_ENTORNO_CLAVE_SESION, "clave-a")
    token = generar_token_sesion("admin", _ROL, timestamp=_MARCA_BASE)

    # Act
    monkeypatch.setenv(VARIABLE_ENTORNO_CLAVE_SESION, "clave-b")
    valido, _, _, motivo = validar_token_sesion(token, ahora=_MARCA_BASE)

    # Assert
    assert valido is False
    assert motivo == MOTIVO_INVALIDO


# --- Fachada: generación y renovación ----------------------------------------
def test_fachada_genera_token_valido(fachada: UsuariosFacade) -> None:
    """CA-02: la fachada emite tokens válidos sin exponer criptografía."""
    # Arrange / Act
    token = fachada.generar_token_sesion("admin", _ROL)

    # Assert
    valido, usuario, rol, motivo = validar_token_sesion(token)
    assert valido is True
    assert usuario == "admin"
    assert rol == _ROL
    assert motivo == MOTIVO_VALIDO


def test_fachada_valida_y_renueva_token(fachada: UsuariosFacade) -> None:
    """CA-02: un token vigente se valida y se devuelve renovado."""
    # Arrange
    token = generar_token_sesion("admin", _ROL, timestamp=time.time() - 60)

    # Act
    es_valido, usuario, rol, nuevo_token = fachada.validar_y_renovar_sesion(token)

    # Assert
    assert es_valido is True
    assert usuario == "admin"
    assert rol == _ROL
    assert nuevo_token
    valido_nuevo, usuario_nuevo, rol_nuevo, motivo = validar_token_sesion(nuevo_token)
    assert valido_nuevo is True
    assert usuario_nuevo == "admin"
    assert rol_nuevo == _ROL
    assert motivo == MOTIVO_VALIDO


def test_fachada_rechaza_token_expirado(fachada: UsuariosFacade) -> None:
    """CA-04: un token expirado no se renueva y vuelve todo en ``None``."""
    # Arrange
    token = generar_token_sesion(
        "admin", _ROL, timestamp=time.time() - (SEGUNDOS_INACTIVIDAD_SESION + 1)
    )

    # Act
    resultado = fachada.validar_y_renovar_sesion(token)

    # Assert
    assert resultado == (False, None, None, None)


def test_fachada_rechaza_token_manipulado(fachada: UsuariosFacade) -> None:
    """CA-04: un token inválido se rechaza sin emitir uno nuevo."""
    # Arrange / Act
    resultado = fachada.validar_y_renovar_sesion("token-invalido")

    # Assert
    assert resultado == (False, None, None, None)


# --- UI: dobles de prueba ----------------------------------------------------
class _FachadaFalsa(UsuariosFacade):
    """Doble de :class:`UsuariosFacade` que registra tokens y resultados.

    No invoca el constructor real (evita tocar la base de datos): solo sobreescribe
    los métodos de sesión que consume la capa de UI.
    """

    def __init__(self, resultado: tuple[bool, str | None, str | None, str | None]) -> None:
        """Guarda el resultado que devolverá la validación."""
        self.resultado = resultado
        self.tokens_validados: list[str] = []
        self.tokens_generados: list[tuple[str, str]] = []

    def validar_y_renovar_sesion(
        self, token: str
    ) -> tuple[bool, str | None, str | None, str | None]:
        """Registra el token recibido y devuelve el resultado configurado."""
        self.tokens_validados.append(token)
        return self.resultado

    def generar_token_sesion(self, usuario: str, rol: str) -> str:
        """Devuelve un token renovado predecible para las aserciones."""
        self.tokens_generados.append((usuario, rol))
        return f"renovado-{usuario}-{rol}"


class _StreamlitFalso:
    """Doble mínimo de ``streamlit`` para probar la gestión de sesión."""

    def __init__(
        self,
        session_state: dict[str, object] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> None:
        """Inicializa el estado y los *query params* simulados."""
        self.session_state = dict(session_state or {})
        self.query_params = dict(query_params or {})
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def warning(self, mensaje: str) -> None:
        """Registra un aviso."""
        self.warnings.append(mensaje)

    def error(self, mensaje: str) -> None:
        """Registra un error."""
        self.errors.append(mensaje)


class _CacheFalso:
    """Doble de ``st.cache_data`` / ``st.cache_resource`` que registra el ``clear``."""

    def __init__(self) -> None:
        """Inicializa la caché como no limpiada."""
        self.limpiada = False

    def clear(self) -> None:
        """Marca la caché como limpiada."""
        self.limpiada = True


class _StreamlitLateralFalso(_StreamlitFalso):
    """Doble de ``streamlit`` para los controles de la barra lateral."""

    def __init__(self, clics: dict[str, bool]) -> None:
        """Configura los botones que simulan estar pulsados."""
        super().__init__(session_state={"usuario": "admin", "rol": _ROL})
        self.sidebar = self
        self._clics = clics
        self.cache_data = _CacheFalso()
        self.cache_resource = _CacheFalso()
        self.botones: list[str] = []
        self.rerun_llamado = False
        self.switch_pagina: str | None = None

    def caption(self, *args: object, **kwargs: object) -> None:
        """Ignora el caption de usuario y rol."""

    def button(self, etiqueta: str, **kwargs: object) -> bool:
        """Registra la etiqueta y devuelve si fue pulsada."""
        self.botones.append(etiqueta)
        return self._clics.get(etiqueta, False)

    def rerun(self) -> None:
        """Registra que se solicitó un rerender."""
        self.rerun_llamado = True

    def switch_page(self, pagina: str) -> None:
        """Registra la página a la que se redirige."""
        self.switch_pagina = pagina


# --- UI: gestión de sesión ---------------------------------------------------
def test_gestionar_sesion_restaura_desde_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-03: un token vigente en la URL restaura la sesión y se renueva."""
    # Arrange
    st_falso = _StreamlitFalso(query_params={ui_sesion.CLAVE_QUERY_SESION: "token-viejo"})
    fachada = _FachadaFalsa((True, "admin", _ROL, "token-renovado"))
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    activa = ui_sesion.gestionar_sesion_activa(fachada)

    # Assert
    assert activa is True
    assert st_falso.session_state[ui_sesion.CLAVE_ESTADO_LOGGED_IN] is True
    assert st_falso.session_state[ui_sesion.CLAVE_ESTADO_USUARIO] == "admin"
    assert st_falso.session_state[ui_sesion.CLAVE_ESTADO_ROL] == _ROL
    assert st_falso.query_params[ui_sesion.CLAVE_QUERY_SESION] == "token-renovado"
    assert fachada.tokens_validados == ["token-viejo"]


def test_gestionar_sesion_expirada_limpia_y_avisa(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-04: al expirar el token se limpia la URL y se avisa al usuario."""
    # Arrange
    st_falso = _StreamlitFalso(query_params={ui_sesion.CLAVE_QUERY_SESION: "expirado"})
    fachada = _FachadaFalsa((False, None, None, None))
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    activa = ui_sesion.gestionar_sesion_activa(fachada)

    # Assert
    assert activa is False
    assert st_falso.query_params == {}
    assert st_falso.warnings == [ui_sesion.MENSAJE_SESION_EXPIRADA]


def test_gestionar_sesion_sin_token_ni_estado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin sesión ni token no hay nada que restaurar."""
    # Arrange
    st_falso = _StreamlitFalso()
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    activa = ui_sesion.gestionar_sesion_activa(_FachadaFalsa((False, None, None, None)))

    # Assert
    assert activa is False


def test_gestionar_sesion_activa_renueva_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-01: una sesión activa renueva su token con la actividad reciente."""
    # Arrange
    st_falso = _StreamlitFalso(session_state={"logged_in": True, "usuario": "admin", "rol": _ROL})
    fachada = _FachadaFalsa((False, None, None, None))
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    activa = ui_sesion.gestionar_sesion_activa(fachada)

    # Assert
    assert activa is True
    assert st_falso.query_params[ui_sesion.CLAVE_QUERY_SESION] == f"renovado-admin-{_ROL}"
    assert fachada.tokens_generados == [("admin", _ROL)]


def test_controles_refrescar_limpia_cache_y_renueva(monkeypatch: pytest.MonkeyPatch) -> None:
    """CA-05/RF-04: el botón Refrescar limpia las cachés y recarga sin cerrar sesión."""
    # Arrange
    st_falso = _StreamlitLateralFalso({ui_sesion.ETIQUETA_REFRESCAR_DATOS: True})
    fachada = _FachadaFalsa((False, None, None, None))
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    ui_sesion.render_controles_sesion_lateral(fachada)

    # Assert
    assert st_falso.cache_data.limpiada is True
    assert st_falso.cache_resource.limpiada is True
    assert st_falso.rerun_llamado is True
    assert st_falso.query_params[ui_sesion.CLAVE_QUERY_SESION] == f"renovado-admin-{_ROL}"


def test_controles_cerrar_sesion_limpia_y_redirige(monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-03: Cerrar Sesión borra el estado, la URL y redirige al login."""
    # Arrange
    st_falso = _StreamlitLateralFalso({ui_sesion.ETIQUETA_CERRAR_SESION: True})
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    ui_sesion.render_controles_sesion_lateral()

    # Assert
    assert st_falso.session_state == {}
    assert st_falso.query_params == {}
    assert st_falso.switch_pagina == ui_sesion.PAGINA_INICIO


def test_controles_cerrar_sesion_en_inicio_refresca(monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-03: desde ``Inicio.py`` cerrar sesión refresca en lugar de redirigir."""
    # Arrange
    st_falso = _StreamlitLateralFalso({ui_sesion.ETIQUETA_CERRAR_SESION: True})
    monkeypatch.setattr(ui_sesion, "st", st_falso)

    # Act
    ui_sesion.render_controles_sesion_lateral(pagina_inicio=True)

    # Assert
    assert st_falso.rerun_llamado is True
    assert st_falso.switch_pagina is None


# --- Criterios de aceptación verificables ------------------------------------
def test_ui_sesion_no_contiene_sql() -> None:
    """RNF-02: ``ui_sesion`` no contiene SQL ni acceso directo a la base de datos."""
    # Arrange
    contenido = _RUTA_UI_SESION.read_text(encoding="utf-8")
    patron = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")

    # Act / Assert
    assert patron.findall(contenido.upper()) == []
    assert "run_query" not in contenido.lower()
    assert "bcrypt" not in contenido.lower()


def test_ui_sesion_incluye_refrescar_y_cerrar() -> None:
    """CA-05: el módulo define Refrescar Datos (con limpieza de caché) y Cerrar Sesión."""
    # Arrange
    contenido = _RUTA_UI_SESION.read_text(encoding="utf-8")

    # Act / Assert
    assert ui_sesion.ETIQUETA_REFRESCAR_DATOS in contenido
    assert ui_sesion.ETIQUETA_CERRAR_SESION in contenido
    assert "cache_data.clear()" in contenido
    assert "cache_resource.clear()" in contenido


def test_inicio_restaura_sesion_y_genera_token() -> None:
    """CA-03: ``Inicio.py`` gestiona la sesión y publica el token en la URL."""
    # Arrange
    contenido = _RUTA_INICIO.read_text(encoding="utf-8")

    # Act / Assert
    assert "gestionar_sesion_activa" in contenido
    assert "render_controles_sesion_lateral" in contenido
    assert "generar_token_sesion" in contenido
    assert 'st.query_params["session"]' in contenido


@pytest.mark.parametrize("nombre", _PAGINAS)
def test_paginas_usan_la_gestion_de_sesion(nombre: str) -> None:
    """CA-03/CA-04: las páginas restauran la sesión y pintan los controles."""
    # Arrange
    contenido = (_RUTA_PAGINAS / nombre).read_text(encoding="utf-8")

    # Act / Assert
    assert "gestionar_sesion_activa" in contenido
    assert "render_controles_sesion_lateral" in contenido
