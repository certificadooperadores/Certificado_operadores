"""Fixtures compartidas para las pruebas.

Coloca este archivo en ``tests/conftest.py``. pytest lo descubre automáticamente.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# --- Configuración de la sesión de pruebas ----------------------------------
NOMBRE_DIR_TEMPORAL_PRUEBAS = f"certificado-operadores-pytest-{os.getpid()}"
"""Subcarpeta propia bajo el directorio temporal del sistema para ``tmp_path``.

Se usa un ``basetemp`` con PID para evitar colisiones y ``PermissionError`` en
Windows al limpiar sesiones anteriores concurrentes o bloqueadas.
"""


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Fija un directorio base temporal propio antes de crear el de pytest.

    Respeta un ``--basetemp`` indicado por el usuario y, en su defecto, usa una
    subcarpeta bajo el temporal del sistema (nunca una ruta absoluta quemada).

    Args:
        config: Configuración de la sesión de pytest.
    """
    if config.option.basetemp is None:
        config.option.basetemp = Path(tempfile.gettempdir()) / NOMBRE_DIR_TEMPORAL_PRUEBAS


@pytest.fixture
def usuario() -> dict[str, str]:
    """Devuelve un usuario de ejemplo para las pruebas."""
    return {"nombre": "Ana", "rol": "admin"}


@pytest.fixture
def repo_en_memoria() -> Iterator[dict[str, str]]:
    """Repositorio falso en memoria (fake) para no tocar la base de datos."""
    datos: dict[str, str] = {}
    yield datos
    datos.clear()
