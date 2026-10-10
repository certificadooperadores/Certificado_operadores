"""Repositorio de catálogos (capa de infraestructura, spec 007).

Encapsula **todo** el acceso a datos de los cinco catálogos del sistema:
``dim_empresa``, ``dim_vehiculo``, ``dim_impacto``, ``dim_comportamiento`` y
``dim_detalle_comportamiento``. Concentra las constantes SQL y la ejecución
contra el motor inyectado, de modo que la interfaz de usuario no conoce el
esquema ni el motor.

Todas las consultas usan parámetros enlazados (nunca SQL construido con datos
del usuario) y las mutaciones de impacto, comportamiento y detalle registran su
acción en ``log_auditoria`` dentro de la misma transacción, igual que la lógica
heredada. Las operaciones de empresa y vehículo preservan el comportamiento
original (sin auditoría).

La interfaz de usuario consume los DTOs que devuelve este repositorio.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from certificado_operadores.domain.models import VIGENCIA_ACTIVA

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine, RowMapping

LIMITE_DETALLES = 500
"""Número máximo de detalles de comportamiento que devuelve un listado."""

SEPARADOR_DESCRIPCION = "::"
"""Separador con el que se construye la descripción de un detalle."""

ESTADO_EMPRESA_ACTIVA = "Activo"
"""Etiqueta legible de una empresa activa."""

ESTADO_EMPRESA_INACTIVA = "Inactivo"
"""Etiqueta legible de una empresa inactiva."""

ACCION_CREAR_IMPACTO = "Crear Impacto"
"""Acción de auditoría al crear un nivel de impacto."""

ACCION_EDITAR_IMPACTO = "Editar Impacto"
"""Acción de auditoría al editar un nivel de impacto."""

ACCION_CREAR_COMPORTAMIENTO = "Crear Comportamiento"
"""Acción de auditoría al crear un tipo de comportamiento."""

ACCION_EDITAR_COMPORTAMIENTO = "Editar Comportamiento"
"""Acción de auditoría al editar un tipo de comportamiento."""

ACCION_CREAR_DETALLE = "Crear Detalle Comportamiento"
"""Acción de auditoría al crear un detalle de comportamiento."""

ACCION_EDITAR_DETALLE = "Editar Detalle Comportamiento"
"""Acción de auditoría al editar un detalle de comportamiento."""


@dataclass(frozen=True)
class EmpresaInfo:
    """Empresa transportadora (``dim_empresa``) para la tabla de la UI.

    Attributes:
        id_empresa: Identificador de la empresa.
        nombre_empresa: Nombre de la empresa.
        id_vigencia: Vigencia de la empresa (activa o inactiva).
    """

    id_empresa: int
    nombre_empresa: str
    id_vigencia: int

    @property
    def estado(self) -> str:
        """Etiqueta legible de la vigencia (``Activo`` o ``Inactivo``)."""
        if self.id_vigencia == VIGENCIA_ACTIVA:
            return ESTADO_EMPRESA_ACTIVA
        return ESTADO_EMPRESA_INACTIVA


@dataclass(frozen=True)
class VehiculoInfo:
    """Vehículo (``dim_vehiculo``) para la tabla de la UI.

    Attributes:
        id_vehiculo: Identificador del vehículo.
        nombre_vehiculo: Nombre o placa del vehículo.
    """

    id_vehiculo: int
    nombre_vehiculo: str


@dataclass(frozen=True)
class ImpactoInfo:
    """Nivel de impacto (``dim_impacto``) para la tabla de la UI.

    Attributes:
        id_impacto: Identificador del nivel de impacto.
        impacto: Nombre del nivel de impacto.
        maximo: Número máximo de ocurrencias permitidas.
        dias_maximo: Días de reinicio del contador de ocurrencias.
    """

    id_impacto: int
    impacto: str
    maximo: int
    dias_maximo: int


@dataclass(frozen=True)
class ComportamientoInfo:
    """Tipo de comportamiento (``dim_comportamiento``) con su impacto.

    Attributes:
        id_comportamiento: Identificador del comportamiento.
        comportamiento: Descripción del comportamiento.
        id_impacto: Identificador del impacto asociado (puede ser ``None``).
        impacto: Nombre del impacto asociado, o cadena vacía si no tiene.
    """

    id_comportamiento: int
    comportamiento: str
    id_impacto: int | None
    impacto: str


@dataclass(frozen=True)
class DetalleComportamientoInfo:
    """Detalle de comportamiento (``dim_detalle_comportamiento``) con su tipo.

    Attributes:
        id_jerarquia: Identificador del detalle (clave primaria).
        fuente: Fuente del registro (jerarquía, PQRS o movilidad).
        descripcion_comportamiento: Descripción compuesta del detalle.
        tipo: Tipo del detalle.
        servicios: Servicios asociados.
        jerarquia_1: Primer nivel de jerarquía.
        jerarquia_2: Segundo nivel de jerarquía (opcional).
        jerarquia_3: Tercer nivel de jerarquía (opcional).
        jerarquia_4: Cuarto nivel de jerarquía (opcional).
        id_comportamiento: Identificador del comportamiento asociado.
        comportamiento: Nombre del comportamiento asociado.
    """

    id_jerarquia: int
    fuente: str
    descripcion_comportamiento: str
    tipo: str
    servicios: str
    jerarquia_1: str
    jerarquia_2: str | None
    jerarquia_3: str | None
    jerarquia_4: str | None
    id_comportamiento: int | None
    comportamiento: str


@dataclass(frozen=True)
class DatosDetalleComportamiento:
    """Datos de entrada para crear o actualizar un detalle de comportamiento.

    La descripción compuesta (``descripcion_comportamiento``) no se recibe: el
    repositorio la construye a partir de ``tipo``, ``servicios`` y las
    jerarquías con :func:`construir_descripcion_comportamiento`.

    Attributes:
        fuente: Fuente del registro.
        tipo: Tipo del detalle.
        servicios: Servicios asociados.
        jerarquia_1: Primer nivel de jerarquía.
        jerarquia_2: Segundo nivel de jerarquía (opcional).
        jerarquia_3: Tercer nivel de jerarquía (opcional).
        jerarquia_4: Cuarto nivel de jerarquía (opcional).
        id_comportamiento: Identificador del comportamiento asociado.
    """

    fuente: str
    tipo: str
    servicios: str
    jerarquia_1: str
    jerarquia_2: str | None
    jerarquia_3: str | None
    jerarquia_4: str | None
    id_comportamiento: int


# --- Fragmentos y sentencias SQL (parámetros enlazados, sin concatenar datos) -
_COLUMNAS_DETALLE = """
    d.id_jerarquia, d.fuente, d.descripcion_comportamiento, d.tipo, d.servicios,
    d.jerarquia_1, d.jerarquia_2, d.jerarquia_3, d.jerarquia_4,
    c.id_comportamiento AS comp_id, c.comportamiento
"""

_FROM_DETALLE = """
    FROM dim_detalle_comportamiento AS d
    LEFT JOIN dim_comportamiento AS c ON d.id_comportamiento = c.id_comportamiento
"""

_SQL_LISTAR_EMPRESAS = text(
    "SELECT id_empresa, nombre_empresa, id_vigencia FROM dim_empresa ORDER BY id_empresa"
)

_SQL_LISTAR_VEHICULOS = text(
    "SELECT id_vehiculo, nombre_vehiculo FROM dim_vehiculo ORDER BY id_vehiculo"
)

_SQL_LISTAR_IMPACTOS = text(
    "SELECT id_impacto, impacto, maximo, dias_maximo FROM dim_impacto ORDER BY id_impacto"
)

_SQL_LISTAR_COMPORTAMIENTOS = text(
    "SELECT c.id_comportamiento, c.comportamiento, c.id_impacto, i.impacto "
    "FROM dim_comportamiento AS c "
    "LEFT JOIN dim_impacto AS i ON c.id_impacto = i.id_impacto "
    "ORDER BY c.id_comportamiento"
)

_SQL_LISTAR_DETALLES = text(
    f"SELECT {_COLUMNAS_DETALLE} {_FROM_DETALLE} ORDER BY d.id_jerarquia LIMIT :limite"
)

_SQL_LISTAR_DETALLES_FUENTE = text(
    f"SELECT {_COLUMNAS_DETALLE} {_FROM_DETALLE} "
    f"WHERE d.fuente = :fuente ORDER BY d.id_jerarquia LIMIT :limite"
)

_SQL_INSERT_EMPRESA = text(
    "INSERT INTO dim_empresa (id_empresa, nombre_empresa, id_vigencia, usuario_registra) "
    "VALUES (:id, :nombre, :vigencia, :usuario)"
)

_SQL_CAMBIAR_VIGENCIA_EMPRESA = text(
    "UPDATE dim_empresa SET id_vigencia = :vigencia WHERE id_empresa = :id"
)

_SQL_RENOMBRAR_EMPRESA = text(
    "UPDATE dim_empresa SET nombre_empresa = :nombre WHERE id_empresa = :id"
)

_SQL_INSERT_VEHICULO = text(
    "INSERT INTO dim_vehiculo (id_vehiculo, nombre_vehiculo, usuario_registra) "
    "VALUES (:id, :nombre, :usuario)"
)

_SQL_RENOMBRAR_VEHICULO = text(
    "UPDATE dim_vehiculo SET nombre_vehiculo = :nombre WHERE id_vehiculo = :id"
)

_SQL_INSERT_IMPACTO = text(
    "INSERT INTO dim_impacto (id_impacto, impacto, maximo, dias_maximo, usuario_registra) "
    "VALUES (:id, :nombre, :maximo, :dias_maximo, :usuario)"
)

_SQL_ACTUALIZAR_IMPACTO = text(
    "UPDATE dim_impacto SET impacto = :nombre, maximo = :maximo, dias_maximo = :dias_maximo "
    "WHERE id_impacto = :id"
)

_SQL_INSERT_COMPORTAMIENTO = text(
    "INSERT INTO dim_comportamiento "
    "(id_comportamiento, comportamiento, id_impacto, usuario_registra) "
    "VALUES (:id, :nombre, :id_impacto, :usuario)"
)

_SQL_ACTUALIZAR_COMPORTAMIENTO = text(
    "UPDATE dim_comportamiento SET comportamiento = :nombre, id_impacto = :id_impacto "
    "WHERE id_comportamiento = :id"
)

_SQL_INSERT_DETALLE = text(
    "INSERT INTO dim_detalle_comportamiento "
    "(id_jerarquia, fuente, descripcion_comportamiento, tipo, servicios, "
    "jerarquia_1, jerarquia_2, jerarquia_3, jerarquia_4, id_comportamiento, usuario_registra) "
    "VALUES (:id, :fuente, :descripcion, :tipo, :servicios, "
    ":jerarquia_1, :jerarquia_2, :jerarquia_3, :jerarquia_4, :id_comportamiento, :usuario)"
)

_SQL_ACTUALIZAR_DETALLE = text(
    "UPDATE dim_detalle_comportamiento SET fuente = :fuente, tipo = :tipo, "
    "servicios = :servicios, jerarquia_1 = :jerarquia_1, jerarquia_2 = :jerarquia_2, "
    "jerarquia_3 = :jerarquia_3, jerarquia_4 = :jerarquia_4, "
    "descripcion_comportamiento = :descripcion, id_comportamiento = :id_comportamiento "
    "WHERE id_jerarquia = :id"
)

_SQL_AUDITORIA = text(
    "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:usuario, :accion, :detalles)"
)


def construir_descripcion_comportamiento(
    tipo: str,
    servicios: str,
    jerarquia_1: str,
    jerarquia_2: str | None = None,
    jerarquia_3: str | None = None,
    jerarquia_4: str | None = None,
) -> str:
    """Construye la descripción compuesta de un detalle de comportamiento.

    Une en minúsculas el tipo, los servicios y las jerarquías presentes con el
    separador :data:`SEPARADOR_DESCRIPCION`, omitiendo las jerarquías vacías.

    Args:
        tipo: Tipo del detalle.
        servicios: Servicios asociados.
        jerarquia_1: Primer nivel de jerarquía.
        jerarquia_2: Segundo nivel de jerarquía (opcional).
        jerarquia_3: Tercer nivel de jerarquía (opcional).
        jerarquia_4: Cuarto nivel de jerarquía (opcional).

    Returns:
        La descripción compuesta, por ejemplo ``"tipo::servicio::j1::j2"``.
    """
    partes = [tipo.lower(), servicios.lower(), jerarquia_1.lower()]
    for jerarquia in (jerarquia_2, jerarquia_3, jerarquia_4):
        if jerarquia:
            partes.append(jerarquia.lower())
    return SEPARADOR_DESCRIPCION.join(partes)


def _normalizar_opcional(texto: str | None) -> str | None:
    """Normaliza un campo de texto opcional a minúsculas o ``None``.

    Args:
        texto: Texto recibido del formulario.

    Returns:
        El texto en minúsculas, o ``None`` si está vacío.
    """
    limpio = (texto or "").strip()
    return limpio.lower() if limpio else None


def _mapear_empresa(fila: RowMapping) -> EmpresaInfo:
    """Mapea una fila de empresa al DTO de infraestructura."""
    return EmpresaInfo(
        id_empresa=int(fila["id_empresa"]),
        nombre_empresa=str(fila["nombre_empresa"] or ""),
        id_vigencia=int(fila["id_vigencia"]),
    )


def _mapear_vehiculo(fila: RowMapping) -> VehiculoInfo:
    """Mapea una fila de vehículo al DTO de infraestructura."""
    return VehiculoInfo(
        id_vehiculo=int(fila["id_vehiculo"]),
        nombre_vehiculo=str(fila["nombre_vehiculo"] or ""),
    )


def _mapear_impacto(fila: RowMapping) -> ImpactoInfo:
    """Mapea una fila de impacto al DTO de infraestructura."""
    return ImpactoInfo(
        id_impacto=int(fila["id_impacto"]),
        impacto=str(fila["impacto"] or ""),
        maximo=int(fila["maximo"] or 0),
        dias_maximo=int(fila["dias_maximo"] or 0),
    )


def _mapear_comportamiento(fila: RowMapping) -> ComportamientoInfo:
    """Mapea una fila de comportamiento (con su impacto) al DTO."""
    id_impacto = fila["id_impacto"]
    return ComportamientoInfo(
        id_comportamiento=int(fila["id_comportamiento"]),
        comportamiento=str(fila["comportamiento"] or ""),
        id_impacto=int(id_impacto) if id_impacto is not None else None,
        impacto=str(fila["impacto"] or ""),
    )


def _mapear_detalle(fila: RowMapping) -> DetalleComportamientoInfo:
    """Mapea una fila de detalle de comportamiento (con su tipo) al DTO."""
    id_comportamiento = fila["comp_id"]

    def _opcional(clave: str) -> str | None:
        valor = fila[clave]
        return str(valor) if valor is not None else None

    return DetalleComportamientoInfo(
        id_jerarquia=int(fila["id_jerarquia"]),
        fuente=str(fila["fuente"] or ""),
        descripcion_comportamiento=str(fila["descripcion_comportamiento"] or ""),
        tipo=str(fila["tipo"] or ""),
        servicios=str(fila["servicios"] or ""),
        jerarquia_1=str(fila["jerarquia_1"] or ""),
        jerarquia_2=_opcional("jerarquia_2"),
        jerarquia_3=_opcional("jerarquia_3"),
        jerarquia_4=_opcional("jerarquia_4"),
        id_comportamiento=int(id_comportamiento) if id_comportamiento is not None else None,
        comportamiento=str(fila["comportamiento"] or ""),
    )


class CatalogosRepository:
    """Repositorio de los cinco catálogos del sistema.

    Concentra toda la ejecución de SQLAlchemy de la gestión de catálogos. El
    motor se inyecta (por defecto se resuelve de forma perezosa desde
    :func:`certificado_operadores.db.get_engine`) para facilitar las pruebas.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        """Inicializa el repositorio.

        Args:
            engine: Motor SQLAlchemy a usar. Si es ``None`` se resuelve de forma
                perezosa con el motor local configurado en ``db``.
        """
        self._engine = engine

    @property
    def motor(self) -> Engine:
        """Motor SQLAlchemy asociado al repositorio (inyectado o por defecto)."""
        if self._engine is None:
            # Import perezoso: evita cargar Streamlit cuando las pruebas inyectan motor.
            from certificado_operadores.db import get_engine

            self._engine = get_engine()
        return self._engine

    # --- Empresas (RF-01) ---------------------------------------------------
    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas ordenadas por identificador.

        Returns:
            Las empresas del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR_EMPRESAS).mappings().all()
        return [_mapear_empresa(fila) for fila in filas]

    def crear_empresa(self, nombre: str, usuario: str) -> int:
        """Crea una empresa activa con el siguiente identificador disponible.

        Args:
            nombre: Nombre de la empresa (se almacena en mayúsculas).
            usuario: Usuario que registra la empresa.

        Returns:
            El identificador de la empresa creada.
        """
        nuevo_id = self._siguiente_id("dim_empresa", "id_empresa")
        parametros = {
            "id": nuevo_id,
            "nombre": nombre.upper(),
            "vigencia": VIGENCIA_ACTIVA,
            "usuario": usuario,
        }
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_INSERT_EMPRESA, parametros)
        return nuevo_id

    def cambiar_vigencia_empresa(self, id_empresa: int, vigencia: int) -> None:
        """Activa o inactiva una empresa cambiando su vigencia.

        Args:
            id_empresa: Identificador de la empresa.
            vigencia: Vigencia destino (activa o inactiva).
        """
        with self.motor.begin() as conexion:
            conexion.execute(
                _SQL_CAMBIAR_VIGENCIA_EMPRESA, {"vigencia": vigencia, "id": id_empresa}
            )

    def renombrar_empresa(self, id_empresa: int, nombre: str) -> None:
        """Renombra una empresa existente.

        Args:
            id_empresa: Identificador de la empresa.
            nombre: Nuevo nombre (se almacena en mayúsculas).
        """
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_RENOMBRAR_EMPRESA, {"nombre": nombre.upper(), "id": id_empresa})

    # --- Vehículos (RF-02) --------------------------------------------------
    def listar_vehiculos(self) -> list[VehiculoInfo]:
        """Lista los vehículos ordenados por identificador.

        Returns:
            Los vehículos del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR_VEHICULOS).mappings().all()
        return [_mapear_vehiculo(fila) for fila in filas]

    def crear_vehiculo(self, nombre: str, usuario: str) -> int:
        """Crea un vehículo con el siguiente identificador disponible.

        Args:
            nombre: Nombre o placa del vehículo (se almacena en mayúsculas).
            usuario: Usuario que registra el vehículo.

        Returns:
            El identificador del vehículo creado.
        """
        nuevo_id = self._siguiente_id("dim_vehiculo", "id_vehiculo")
        parametros = {"id": nuevo_id, "nombre": nombre.upper(), "usuario": usuario}
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_INSERT_VEHICULO, parametros)
        return nuevo_id

    def renombrar_vehiculo(self, id_vehiculo: int, nombre: str) -> None:
        """Renombra un vehículo existente.

        Args:
            id_vehiculo: Identificador del vehículo.
            nombre: Nuevo nombre (se almacena en mayúsculas).
        """
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_RENOMBRAR_VEHICULO, {"nombre": nombre.upper(), "id": id_vehiculo})

    # --- Impactos (RF-03) ---------------------------------------------------
    def listar_impactos(self) -> list[ImpactoInfo]:
        """Lista los niveles de impacto ordenados por identificador.

        Returns:
            Los niveles de impacto del catálogo.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR_IMPACTOS).mappings().all()
        return [_mapear_impacto(fila) for fila in filas]

    def crear_impacto(self, nombre: str, maximo: int, dias_maximo: int, usuario: str) -> int:
        """Crea un nivel de impacto y registra la auditoría.

        Args:
            nombre: Nombre del impacto (se almacena en mayúsculas).
            maximo: Número máximo de ocurrencias.
            dias_maximo: Días de reinicio del contador.
            usuario: Usuario que registra el impacto.

        Returns:
            El identificador del impacto creado.
        """
        nuevo_id = self._siguiente_id("dim_impacto", "id_impacto")
        parametros = {
            "id": nuevo_id,
            "nombre": nombre.upper(),
            "maximo": maximo,
            "dias_maximo": dias_maximo,
            "usuario": usuario,
        }
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_INSERT_IMPACTO, parametros)
            self._auditar(conexion, usuario, ACCION_CREAR_IMPACTO, f"Impacto: {nombre}")
        return nuevo_id

    def actualizar_impacto(
        self, id_impacto: int, nombre: str, maximo: int, dias_maximo: int, usuario: str
    ) -> None:
        """Actualiza un nivel de impacto y registra la auditoría.

        Args:
            id_impacto: Identificador del impacto.
            nombre: Nuevo nombre (se almacena en mayúsculas).
            maximo: Nuevo número máximo de ocurrencias.
            dias_maximo: Nuevos días de reinicio del contador.
            usuario: Usuario que edita el impacto.
        """
        parametros = {
            "id": id_impacto,
            "nombre": nombre.upper(),
            "maximo": maximo,
            "dias_maximo": dias_maximo,
        }
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_ACTUALIZAR_IMPACTO, parametros)
            self._auditar(conexion, usuario, ACCION_EDITAR_IMPACTO, f"ID: {id_impacto}")

    # --- Comportamientos (RF-04) --------------------------------------------
    def listar_comportamientos(self) -> list[ComportamientoInfo]:
        """Lista los comportamientos con el nombre de su impacto asociado.

        Returns:
            Los comportamientos ordenados por identificador.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR_COMPORTAMIENTOS).mappings().all()
        return [_mapear_comportamiento(fila) for fila in filas]

    def crear_comportamiento(self, descripcion: str, id_impacto: int, usuario: str) -> int:
        """Crea un comportamiento y registra la auditoría.

        Args:
            descripcion: Descripción del comportamiento (se almacena en minúsculas).
            id_impacto: Identificador del impacto asociado.
            usuario: Usuario que registra el comportamiento.

        Returns:
            El identificador del comportamiento creado.
        """
        nuevo_id = self._siguiente_id("dim_comportamiento", "id_comportamiento")
        parametros = {
            "id": nuevo_id,
            "nombre": descripcion.lower(),
            "id_impacto": id_impacto,
            "usuario": usuario,
        }
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_INSERT_COMPORTAMIENTO, parametros)
            self._auditar(
                conexion, usuario, ACCION_CREAR_COMPORTAMIENTO, f"Comportamiento: {descripcion}"
            )
        return nuevo_id

    def actualizar_comportamiento(
        self, id_comportamiento: int, descripcion: str, id_impacto: int, usuario: str
    ) -> None:
        """Actualiza un comportamiento y registra la auditoría.

        Args:
            id_comportamiento: Identificador del comportamiento.
            descripcion: Nueva descripción (se almacena en minúsculas).
            id_impacto: Nuevo identificador del impacto asociado.
            usuario: Usuario que edita el comportamiento.
        """
        parametros = {
            "id": id_comportamiento,
            "nombre": descripcion.lower(),
            "id_impacto": id_impacto,
        }
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_ACTUALIZAR_COMPORTAMIENTO, parametros)
            self._auditar(
                conexion, usuario, ACCION_EDITAR_COMPORTAMIENTO, f"ID: {id_comportamiento}"
            )

    # --- Detalles de comportamiento (RF-05) ---------------------------------
    def listar_detalles(
        self, fuente: str | None = None, limite: int = LIMITE_DETALLES
    ) -> list[DetalleComportamientoInfo]:
        """Lista los detalles de comportamiento, opcionalmente por fuente.

        Args:
            fuente: Fuente a filtrar. Si es ``None`` se listan todas.
            limite: Número máximo de filas a devolver.

        Returns:
            Los detalles ordenados por identificador.
        """
        if fuente is None:
            with self.motor.connect() as conexion:
                filas = conexion.execute(_SQL_LISTAR_DETALLES, {"limite": limite}).mappings().all()
        else:
            with self.motor.connect() as conexion:
                filas = (
                    conexion.execute(
                        _SQL_LISTAR_DETALLES_FUENTE, {"fuente": fuente, "limite": limite}
                    )
                    .mappings()
                    .all()
                )
        return [_mapear_detalle(fila) for fila in filas]

    def crear_detalle(self, datos: DatosDetalleComportamiento, usuario: str) -> int:
        """Crea un detalle de comportamiento y registra la auditoría.

        Args:
            datos: Datos del detalle a crear.
            usuario: Usuario que registra el detalle.

        Returns:
            El identificador del detalle creado.
        """
        nuevo_id = self._siguiente_id("dim_detalle_comportamiento", "id_jerarquia")
        descripcion = construir_descripcion_comportamiento(
            datos.tipo,
            datos.servicios,
            datos.jerarquia_1,
            datos.jerarquia_2,
            datos.jerarquia_3,
            datos.jerarquia_4,
        )
        parametros = self._parametros_detalle(datos)
        parametros["id"] = nuevo_id
        parametros["descripcion"] = descripcion
        parametros["usuario"] = usuario
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_INSERT_DETALLE, parametros)
            self._auditar(conexion, usuario, ACCION_CREAR_DETALLE, f"Desc: {descripcion}")
        return nuevo_id

    def actualizar_detalle(
        self, id_jerarquia: int, datos: DatosDetalleComportamiento, usuario: str
    ) -> None:
        """Actualiza un detalle de comportamiento y registra la auditoría.

        Args:
            id_jerarquia: Identificador del detalle.
            datos: Nuevos datos del detalle.
            usuario: Usuario que edita el detalle.
        """
        descripcion = construir_descripcion_comportamiento(
            datos.tipo,
            datos.servicios,
            datos.jerarquia_1,
            datos.jerarquia_2,
            datos.jerarquia_3,
            datos.jerarquia_4,
        )
        parametros = self._parametros_detalle(datos)
        parametros["id"] = id_jerarquia
        parametros["descripcion"] = descripcion
        with self.motor.begin() as conexion:
            conexion.execute(_SQL_ACTUALIZAR_DETALLE, parametros)
            self._auditar(conexion, usuario, ACCION_EDITAR_DETALLE, f"ID: {id_jerarquia}")

    def _siguiente_id(self, tabla: str, columna: str) -> int:
        """Calcula el siguiente identificador disponible de una tabla.

        Args:
            tabla: Nombre de la tabla (constante interna).
            columna: Columna de identificador (constante interna).

        Returns:
            ``MAX(columna) + 1`` o ``1`` si la tabla está vacía.
        """
        sentencia = text(f"SELECT COALESCE(MAX({columna}), 0) + 1 AS n FROM {tabla}")
        with self.motor.connect() as conexion:
            return int(conexion.execute(sentencia).scalar_one())

    @staticmethod
    def _parametros_detalle(datos: DatosDetalleComportamiento) -> dict[str, object]:
        """Traduce los datos del detalle a los parámetros enlazados del SQL.

        Args:
            datos: Datos del detalle.

        Returns:
            El diccionario de parámetros para las sentencias de inserción y
            actualización.
        """
        return {
            "fuente": datos.fuente,
            "tipo": datos.tipo.lower(),
            "servicios": datos.servicios.lower(),
            "jerarquia_1": datos.jerarquia_1.lower(),
            "jerarquia_2": _normalizar_opcional(datos.jerarquia_2),
            "jerarquia_3": _normalizar_opcional(datos.jerarquia_3),
            "jerarquia_4": _normalizar_opcional(datos.jerarquia_4),
            "id_comportamiento": datos.id_comportamiento,
        }

    @staticmethod
    def _auditar(conexion: Connection, usuario: str, accion: str, detalles: str) -> None:
        """Inserta una fila de auditoría usando la conexión de la transacción.

        Args:
            conexion: Conexión activa dentro de la transacción.
            usuario: Usuario que ejecuta la acción.
            accion: Nombre de la acción realizada.
            detalles: Detalle libre de la acción.
        """
        conexion.execute(
            _SQL_AUDITORIA,
            {"usuario": usuario, "accion": accion, "detalles": detalles},
        )


__all__ = [
    "ACCION_CREAR_COMPORTAMIENTO",
    "ACCION_CREAR_DETALLE",
    "ACCION_CREAR_IMPACTO",
    "ACCION_EDITAR_COMPORTAMIENTO",
    "ACCION_EDITAR_DETALLE",
    "ACCION_EDITAR_IMPACTO",
    "ESTADO_EMPRESA_ACTIVA",
    "ESTADO_EMPRESA_INACTIVA",
    "LIMITE_DETALLES",
    "SEPARADOR_DESCRIPCION",
    "CatalogosRepository",
    "ComportamientoInfo",
    "DatosDetalleComportamiento",
    "DetalleComportamientoInfo",
    "EmpresaInfo",
    "ImpactoInfo",
    "VehiculoInfo",
    "construir_descripcion_comportamiento",
]
