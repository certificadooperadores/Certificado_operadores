"""Servicios de seguridad de contraseñas (capa de infraestructura).

Encapsula el uso de ``bcrypt`` para que ni la interfaz ni el dominio dependan
directamente de una librería criptográfica concreta. El algoritmo se mantiene
según la spec 004 (bcrypt).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import bcrypt


def hashear_contrasena(contrasena: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano.

    Args:
        contrasena: Contraseña en texto plano ingresada por el usuario.

    Returns:
        El hash bcrypt codificado en UTF-8, listo para persistirse.
    """
    sal = bcrypt.gensalt()
    return bcrypt.hashpw(contrasena.encode("utf-8"), sal).decode("utf-8")


def verificar_contrasena(contrasena: str, hash_almacenado: str) -> bool:
    """Verifica una contraseña contra un hash bcrypt almacenado.

    Args:
        contrasena: Contraseña en texto plano a comprobar.
        hash_almacenado: Hash bcrypt previamente persistido.

    Returns:
        ``True`` si la contraseña coincide con el hash; ``False`` en caso
        contrario o si el hash almacenado no tiene un formato válido.
    """
    try:
        return bcrypt.checkpw(contrasena.encode("utf-8"), hash_almacenado.encode("utf-8"))
    except ValueError:
        return False
