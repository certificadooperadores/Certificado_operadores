"""Prueba de ejemplo: patrón AAA y docstrings en español.

Coloca este archivo en ``tests/test_ejemplo.py`` y adáptalo a tu dominio.
"""

from __future__ import annotations


def sumar(a: int, b: int) -> int:
    """Suma dos enteros.

    Args:
        a: Primer entero.
        b: Segundo entero.

    Returns:
        La suma de ``a`` y ``b``.
    """
    return a + b


def test_suma_dos_enteros() -> None:
    """La suma de dos enteros devuelve su total."""
    # Arrange
    a, b = 2, 3

    # Act
    resultado = sumar(a, b)

    # Assert
    assert resultado == 5


def test_suma_con_negativos() -> None:
    """La suma con un número negativo resta."""
    # Arrange
    a, b = 5, -3

    # Act
    resultado = sumar(a, b)

    # Assert
    assert resultado == 2
