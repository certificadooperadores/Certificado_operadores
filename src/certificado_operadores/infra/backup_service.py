"""Servicio de copias de seguridad de la base SQLite (capa de infraestructura).

Encapsula la **gestión física** de los respaldos —crear una copia segura de la
base de datos, listarlos, proteger/desproteger y eliminarlos— sin que la
interfaz conozca el sistema de archivos ni el motor de datos. El directorio
destino y la ruta de la base de origen son **configurables** (variables de
entorno con valores por defecto relativos), de modo que no existen rutas
absolutas quemadas como el heredado ``/Backups``.

La copia se realiza con la API de respaldo de :mod:`sqlite3`, que genera un
archivo consistente aunque haya escrituras en curso; si el origen no fuera una
base SQLite válida se degrada a una copia de archivo (``shutil.copy2``).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DIRECTORIO_POR_DEFECTO = "backups"
"""Subcarpeta relativa de respaldos cuando no se configura otra."""

VARIABLE_ENTORNO_DIRECTORIO = "BACKUPS_DIR"
"""Variable de entorno para configurar el directorio de respaldos."""

VARIABLE_ENTORNO_ORIGEN = "BACKUP_DB_PATH"
"""Variable de entorno para configurar la base de datos de origen."""

EXTENSION_BACKUP = ".db"
"""Extensión de los respaldos (copia binaria de la base SQLite)."""

SUFIJO_PROTEGIDO = ".protegido"
"""Sufijo que marca un respaldo como protegido (no eliminable)."""

FORMATO_FECHA = "%d-%m-%Y"
"""Formato de fecha usado en el nombre versionado de cada respaldo."""

SEPARADOR_VERSION = "_V"
"""Separador entre la fecha y el número de versión en el nombre."""

_PATRON_VERSION = re.compile(r"_V(\d+)$")


class BackupError(RuntimeError):
    """Error controlado al crear o manipular un respaldo."""


class BackupProtegidoError(BackupError):
    """Se intenta eliminar un respaldo marcado como protegido."""


@dataclass(frozen=True)
class BackupInfo:
    """Metadatos de un archivo de respaldo.

    Attributes:
        nombre: Nombre del archivo dentro del directorio de respaldos.
        ruta: Ruta absoluta del archivo.
        tamano_bytes: Tamaño del archivo en bytes.
        fecha_modificacion: Fecha de última modificación del archivo.
        protegido: ``True`` si el respaldo está protegido contra borrado.
    """

    nombre: str
    ruta: Path
    tamano_bytes: int
    fecha_modificacion: datetime
    protegido: bool

    @property
    def tamano_mb(self) -> float:
        """Tamaño del respaldo en megabytes, redondeado a dos decimales."""
        return round(self.tamano_bytes / (1024 * 1024), 2)


def _copiar_con_sqlite(origen: Path, destino: Path) -> None:
    """Copia una base SQLite usando su API de respaldo (copia consistente).

    Args:
        origen: Ruta de la base de datos que se desea respaldar.
        destino: Ruta del archivo de respaldo a crear.

    Raises:
        sqlite3.DatabaseError: Si el origen no es una base SQLite válida.
    """
    conexion_origen = sqlite3.connect(str(origen))
    try:
        conexion_destino = sqlite3.connect(str(destino))
        try:
            conexion_origen.backup(conexion_destino)
        finally:
            conexion_destino.close()
    finally:
        conexion_origen.close()


class BackupService:
    """Servicio único de gestión de respaldos de la base de datos.

    Agrupa las operaciones de copia de seguridad sobre el sistema de archivos.
    El directorio, la base de origen y el reloj se inyectan para facilitar las
    pruebas y eliminar valores quemados.
    """

    def __init__(
        self,
        directorio: Path | str | None = None,
        origen_db: Path | str | None = None,
        reloj: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Inicializa el servicio.

        Args:
            directorio: Carpeta donde se guardan los respaldos. Si es ``None``
                se resuelve con la variable de entorno ``BACKUPS_DIR`` o, en su
                defecto, con la subcarpeta relativa ``backups``.
            origen_db: Ruta de la base de datos a respaldar. Si es ``None`` se
                resuelve con ``BACKUP_DB_PATH`` o con la base local configurada.
            reloj: Función que devuelve la fecha y hora actuales (inyectable).
        """
        self._directorio = Path(directorio) if directorio is not None else None
        self._origen_db = Path(origen_db) if origen_db is not None else None
        self._reloj = reloj

    @property
    def directorio(self) -> Path:
        """Directorio de respaldos (inyectado, por entorno o por defecto)."""
        if self._directorio is not None:
            return self._directorio
        return Path(os.getenv(VARIABLE_ENTORNO_DIRECTORIO, DIRECTORIO_POR_DEFECTO))

    @property
    def origen_db(self) -> Path:
        """Ruta de la base de datos de origen (inyectada o configurada)."""
        if self._origen_db is not None:
            return self._origen_db
        configurado = os.getenv(VARIABLE_ENTORNO_ORIGEN)
        if configurado:
            return Path(configurado)
        # Import perezoso: evita cargar Streamlit cuando se inyecta el origen.
        from certificado_operadores.db import DB_PATH

        return Path(DB_PATH)

    def listar_backups(self) -> list[BackupInfo]:
        """Lista los respaldos existentes, del más reciente al más antiguo.

        Returns:
            La lista de :class:`BackupInfo`; vacía si el directorio no existe o
            no contiene respaldos.
        """
        directorio = self.directorio
        if not directorio.is_dir():
            return []
        respaldos = [
            self._describir(archivo)
            for archivo in directorio.iterdir()
            if archivo.is_file() and archivo.name.endswith(EXTENSION_BACKUP)
        ]
        return sorted(respaldos, key=lambda respaldo: respaldo.fecha_modificacion, reverse=True)

    def crear_backup(self) -> BackupInfo:
        """Crea una copia versionada de la base de datos actual.

        Returns:
            Los metadatos del respaldo recién creado.

        Raises:
            FileNotFoundError: Si la base de datos de origen no existe.
            BackupError: Si la copia falla por un error del sistema de archivos.
        """
        origen = self.origen_db
        if not origen.is_file():
            raise FileNotFoundError(f"No existe la base de datos de origen: {origen}")

        directorio = self.directorio
        directorio.mkdir(parents=True, exist_ok=True)
        destino = directorio / self._siguiente_nombre()
        self._copiar(origen, destino)
        return self._describir(destino)

    def proteger(self, nombre: str) -> BackupInfo:
        """Marca un respaldo como protegido (no eliminable).

        Args:
            nombre: Nombre del respaldo a proteger.

        Returns:
            Los metadatos del respaldo protegido.

        Raises:
            FileNotFoundError: Si el respaldo no existe.
        """
        ruta = self._ruta(nombre)
        if SUFIJO_PROTEGIDO in nombre:
            return self._describir(ruta)
        destino = ruta.with_name(self._nombre_protegido(nombre))
        ruta.rename(destino)
        return self._describir(destino)

    def desproteger(self, nombre: str) -> BackupInfo:
        """Quita la protección de un respaldo para permitir su borrado.

        Args:
            nombre: Nombre del respaldo a desproteger.

        Returns:
            Los metadatos del respaldo desprotegido.

        Raises:
            FileNotFoundError: Si el respaldo no existe.
        """
        ruta = self._ruta(nombre)
        destino = ruta.with_name(self._nombre_desprotegido(nombre))
        if destino.name == ruta.name:
            return self._describir(ruta)
        ruta.rename(destino)
        return self._describir(destino)

    def eliminar(self, nombre: str) -> None:
        """Elimina físicamente un respaldo desprotegido.

        Args:
            nombre: Nombre del respaldo a eliminar.

        Raises:
            FileNotFoundError: Si el respaldo no existe.
            BackupProtegidoError: Si el respaldo está protegido.
        """
        ruta = self._ruta(nombre)
        if SUFIJO_PROTEGIDO in nombre:
            raise BackupProtegidoError(f"El respaldo protegido no se puede eliminar: {nombre}")
        ruta.unlink()

    def _ruta(self, nombre: str) -> Path:
        """Devuelve la ruta de un respaldo existente o falla si no existe.

        Args:
            nombre: Nombre del respaldo.

        Returns:
            La ruta absoluta del respaldo.

        Raises:
            FileNotFoundError: Si el archivo no existe en el directorio.
        """
        ruta = self.directorio / nombre
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el respaldo: {nombre}")
        return ruta

    def _describir(self, archivo: Path) -> BackupInfo:
        """Construye los metadatos de un archivo de respaldo.

        Args:
            archivo: Ruta del archivo de respaldo.

        Returns:
            El :class:`BackupInfo` con tamaño, fecha y estado de protección.
        """
        estadisticas = archivo.stat()
        return BackupInfo(
            nombre=archivo.name,
            ruta=archivo,
            tamano_bytes=estadisticas.st_size,
            fecha_modificacion=datetime.fromtimestamp(estadisticas.st_mtime),
            protegido=SUFIJO_PROTEGIDO in archivo.name,
        )

    def _copiar(self, origen: Path, destino: Path) -> None:
        """Copia la base al destino usando SQLite y con respaldo de archivo.

        Args:
            origen: Base de datos de origen.
            destino: Archivo de respaldo a crear.

        Raises:
            BackupError: Si la copia falla por un error del sistema de archivos.
        """
        try:
            _copiar_con_sqlite(origen, destino)
        except sqlite3.DatabaseError:
            try:
                shutil.copy2(origen, destino)
            except OSError as error:
                raise BackupError(f"No se pudo copiar el respaldo: {error}") from error

    def _siguiente_nombre(self) -> str:
        """Calcula el nombre versionado del próximo respaldo del día.

        Returns:
            El nombre con el formato ``DD-MM-AAAA_Vn.db``.
        """
        fecha = self._reloj().strftime(FORMATO_FECHA)
        versiones = [
            version
            for respaldo in self.listar_backups()
            if respaldo.nombre.startswith(fecha)
            for version in (self._version_de(respaldo.nombre),)
            if version is not None
        ]
        siguiente = max(versiones, default=0) + 1
        return f"{fecha}{SEPARADOR_VERSION}{siguiente}{EXTENSION_BACKUP}"

    def _version_de(self, nombre: str) -> int | None:
        """Extrae el número de versión del nombre de un respaldo.

        Args:
            nombre: Nombre del respaldo.

        Returns:
            La versión encontrada, o ``None`` si el nombre no la incluye.
        """
        base = nombre.removesuffix(EXTENSION_BACKUP).removesuffix(SUFIJO_PROTEGIDO)
        coincidencia = _PATRON_VERSION.search(base)
        return int(coincidencia.group(1)) if coincidencia else None

    @staticmethod
    def _nombre_protegido(nombre: str) -> str:
        """Devuelve el nombre de un respaldo marcado como protegido.

        Args:
            nombre: Nombre original del respaldo.

        Returns:
            El nombre con el sufijo ``.protegido`` antes de la extensión.
        """
        base = nombre.removesuffix(EXTENSION_BACKUP)
        return f"{base}{SUFIJO_PROTEGIDO}{EXTENSION_BACKUP}"

    @staticmethod
    def _nombre_desprotegido(nombre: str) -> str:
        """Devuelve el nombre de un respaldo sin el sufijo de protección.

        Args:
            nombre: Nombre original del respaldo.

        Returns:
            El nombre sin el sufijo ``.protegido``.
        """
        base = nombre.removesuffix(EXTENSION_BACKUP).removesuffix(SUFIJO_PROTEGIDO)
        return f"{base}{EXTENSION_BACKUP}"


__all__ = [
    "DIRECTORIO_POR_DEFECTO",
    "EXTENSION_BACKUP",
    "FORMATO_FECHA",
    "SEPARADOR_VERSION",
    "SUFIJO_PROTEGIDO",
    "VARIABLE_ENTORNO_DIRECTORIO",
    "VARIABLE_ENTORNO_ORIGEN",
    "BackupError",
    "BackupInfo",
    "BackupProtegidoError",
    "BackupService",
]
