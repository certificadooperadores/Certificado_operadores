"""Servicios de seguridad de contraseñas y sesiones (capa de infraestructura).

Encapsula el uso de ``bcrypt`` para el hashing de contraseñas y la firma
criptográfica HMAC-SHA256 de los tokens de sesión, de modo que ni la interfaz ni
el dominio dependan directamente de una librería criptográfica concreta. El
algoritmo de contraseñas se mantiene según la spec 004 (bcrypt) y los tokens
según la spec 013 (HMAC-SHA256 con caducidad por inactividad).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

import bcrypt

# --- Constantes de la sesión (spec 013) --------------------------------------
SEGUNDOS_INACTIVIDAD_SESION: int = 1200
"""Caducidad de la sesión por inactividad: 20 minutos (1200 segundos)."""

VARIABLE_ENTORNO_CLAVE_SESION = "SECRET_KEY_SESION"
"""Variable de entorno que sobreescribe la clave de firma de los tokens."""

CLAVE_SESION_POR_DEFECTO = "certificado-operadores-clave-sesion-local"
"""Clave de firma por defecto, sustituible por ``SECRET_KEY_SESION``.

No es una credencial de servicio: es el valor de respaldo para desarrollo. En
producción debe definirse ``SECRET_KEY_SESION`` en el entorno.
"""

CLAVE_PAYLOAD_USUARIO = "usuario"
"""Nombre de la clave del usuario dentro del payload del token."""

CLAVE_PAYLOAD_ROL = "rol"
"""Nombre de la clave del rol dentro del payload del token."""

CLAVE_PAYLOAD_TIMESTAMP = "timestamp_actividad"
"""Nombre de la marca de tiempo (UNIX) de actividad dentro del payload."""

MOTIVO_VALIDO = "valido"
"""Motivo devuelto por :func:`validar_token_sesion` cuando el token es válido."""

MOTIVO_EXPIRADO = "expirado"
"""Motivo devuelto cuando el token superó el tiempo máximo de inactividad."""

MOTIVO_INVALIDO = "invalido"
"""Motivo devuelto cuando el token está vacío, manipulado o mal formado."""

SEPARADOR_TOKEN = "."
"""Separador entre el payload codificado en Base64 y la firma hexadecimal."""


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


def _clave_sesion() -> bytes:
    """Devuelve la clave de firma de los tokens como bytes.

    Se lee en cada llamada (no al importar) para permitir que ``SECRET_KEY_SESION``
    se configure por entorno y que las pruebas puedan inyectarla.

    Returns:
        La clave de firma codificada en UTF-8.
    """
    clave = os.environ.get(VARIABLE_ENTORNO_CLAVE_SESION, CLAVE_SESION_POR_DEFECTO)
    return clave.encode("utf-8")


def _firmar(payload_codificado: str) -> str:
    """Calcula la firma HMAC-SHA256 de un payload ya codificado.

    Args:
        payload_codificado: Cadena Base64 URL-safe del payload del token.

    Returns:
        La firma como cadena hexadecimal.
    """
    return hmac.new(_clave_sesion(), payload_codificado.encode("utf-8"), hashlib.sha256).hexdigest()


def generar_token_sesion(usuario: str, rol: str, timestamp: float | None = None) -> str:
    """Genera un token de sesión autocontenido y firmado con HMAC-SHA256.

    El token tiene el formato ``<payload_b64>.<firma_hex>`` donde el payload es el
    JSON con ``usuario``, ``rol`` y ``timestamp_actividad`` codificado en Base64
    URL-safe. La firma impide falsificar el usuario o el rol (RNF-01).

    Args:
        usuario: Nombre de la cuenta autenticada.
        rol: Rol de la cuenta autenticada.
        timestamp: Marca de tiempo UNIX de la actividad. Si es ``None`` se usa el
            instante actual; se inyecta para facilitar las pruebas.

    Returns:
        El token de sesión listo para viajar en la URL.
    """
    momento = time.time() if timestamp is None else timestamp
    payload = {
        CLAVE_PAYLOAD_USUARIO: usuario,
        CLAVE_PAYLOAD_ROL: rol,
        CLAVE_PAYLOAD_TIMESTAMP: momento,
    }
    crudo = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_codificado = base64.urlsafe_b64encode(crudo).decode("ascii")
    return f"{payload_codificado}{SEPARADOR_TOKEN}{_firmar(payload_codificado)}"


def validar_token_sesion(
    token: str,
    tiempo_max: int = SEGUNDOS_INACTIVIDAD_SESION,
    ahora: float | None = None,
) -> tuple[bool, str | None, str | None, str]:
    """Valida un token de sesión y comprueba su caducidad por inactividad.

    Verifica primero la firma HMAC con comparación en tiempo constante; si la
    firma no coincide (token manipulado o mal formado) devuelve motivo
    ``invalido``. Con la firma correcta, comprueba que
    ``ahora - timestamp_actividad <= tiempo_max``; si se superó, devuelve motivo
    ``expirado``. En cualquier caso de éxito devuelve ``valido``.

    Args:
        token: Token de sesión a validar.
        tiempo_max: Máximo de segundos de inactividad permitidos (por defecto
            1200, equivalente a 20 minutos).
        ahora: Marca de tiempo UNIX de referencia. Si es ``None`` se usa el
            instante actual; se inyecta para facilitar las pruebas.

    Returns:
        Una tupla ``(es_valido, usuario, rol, motivo)``. ``usuario`` y ``rol``
        son ``None`` cuando el token no es válido, y ``motivo`` es uno de
        ``valido``, ``expirado`` o ``invalido``.
    """
    if not token or not isinstance(token, str):
        return False, None, None, MOTIVO_INVALIDO

    partes = token.split(SEPARADOR_TOKEN)
    if len(partes) != 2:
        return False, None, None, MOTIVO_INVALIDO

    payload_codificado, firma = partes
    if not hmac.compare_digest(firma, _firmar(payload_codificado)):
        return False, None, None, MOTIVO_INVALIDO

    try:
        crudo = base64.urlsafe_b64decode(payload_codificado.encode("ascii"))
        payload = json.loads(crudo.decode("utf-8"))
        usuario = payload[CLAVE_PAYLOAD_USUARIO]
        rol = payload[CLAVE_PAYLOAD_ROL]
        marca = float(payload[CLAVE_PAYLOAD_TIMESTAMP])
    except (KeyError, TypeError, ValueError):
        return False, None, None, MOTIVO_INVALIDO

    momento = time.time() if ahora is None else ahora
    if momento - marca > tiempo_max:
        return False, None, None, MOTIVO_EXPIRADO
    return True, str(usuario), str(rol), MOTIVO_VALIDO
