"""Fixtures compartidas para las pruebas.

Coloca este archivo en ``tests/conftest.py``. pytest lo descubre automáticamente.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


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
