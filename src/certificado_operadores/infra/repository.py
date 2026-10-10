"""Repositorio de operadores sobre SQLite (capa de infraestructura).

Encapsula **todo** el acceso a datos mediante SQLAlchemy: concentra las
constantes SQL y la ejecución de consultas contra el motor inyectado. Devuelve
instancias de los modelos de dominio (:class:`OperadorInfo`,
:class:`EstadoCertificado` y :class:`EstadisticasBasicas`) para que la capa de
aplicación no conozca el esquema ni el motor.

Todas las consultas usan conexiones administradas por contexto y parámetros
enlazados (nunca SQL construido con datos del usuario).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TextClause, bindparam, text
from sqlalchemy.exc import SQLAlchemyError

from certificado_operadores.domain.models import (
    TIPO_EVENTO_CANCELACION,
    TIPOS_EVENTO_CERTIFICADO,
    VIGENCIA_ACTIVA,
    VIGENCIA_ANULADA,
    EstadisticasBasicas,
    EstadoCertificado,
    OperadorInfo,
    RegistroOperador,
    calcular_estado_certificado,
)
from certificado_operadores.infra.reportes_repository import (
    EmpresaInfo,
    TipologiaInfo,
    construir_descripcion_tipologia,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


# --- Consultas SQL (parámetros enlazados, sin concatenar datos) -------------
_SQL_OPERADOR_BASE = """
    SELECT c.id_codigo, c.id_persona, p.nombres, p.primer_apellido,
           p.segundo_apellido, p.genero, c.id_empresa, e.nombre_empresa,
           c.id_perfil_tipologia, c.id_vigencia
    FROM dim_codigo AS c
    LEFT JOIN dim_persona AS p ON p.id_persona = c.id_persona
    LEFT JOIN dim_empresa AS e ON e.id_empresa = c.id_empresa
    WHERE {condicion}
    ORDER BY c.id_vigencia ASC, c.id_codigo ASC
    LIMIT 1
"""

_SQL_OPERADOR_POR_CEDULA = text(_SQL_OPERADOR_BASE.format(condicion="c.id_persona = :cedula"))
_SQL_OPERADOR_POR_CODIGO = text(_SQL_OPERADOR_BASE.format(condicion="c.id_codigo = :codigo"))

_SQL_ULTIMO_CERTIFICADO = text(
    """
    SELECT MAX(fecha_certificado) AS ultima
    FROM fact_eventos_operador
    WHERE id_codigo = :codigo
      AND id_tipo_evento IN :tipos
      AND fecha_certificado IS NOT NULL
      AND fecha_certificado <> ''
    """
).bindparams(bindparam("tipos", expanding=True))

_SQL_TIENE_CANCELACION = text(
    """
    SELECT COUNT(*) AS total
    FROM fact_eventos_operador
    WHERE id_codigo = :codigo AND id_tipo_evento = :tipo_cancelacion
    """
)

_SQL_PING = text("SELECT 1")

_SQL_TOTAL_OPERADORES = text("SELECT COUNT(*) FROM dim_codigo")
_SQL_OPERADORES_POR_VIGENCIA = text("SELECT COUNT(*) FROM dim_codigo WHERE id_vigencia = :vigencia")
_SQL_TOTAL_EMPRESAS = text("SELECT COUNT(*) FROM dim_empresa")
_SQL_TOTAL_LICENCIAS = text("SELECT COUNT(*) FROM fact_licencias")

# --- Guardado de operadores (spec 023) --------------------------------------
ACCION_CREAR_OPERADOR = "CREAR_OPERADOR"
"""Acción registrada en ``log_auditoria`` al persistir un operador."""

BASE_CODIGO_CONCESIONARIO = 10000
"""Base del rango numérico de códigos por concesionario (spec 024).

Cada concesionario ``id_empresa`` ocupa el rango ``[id_empresa * 10000,
(id_empresa + 1) * 10000)``: GIT (1) usa 10001-19999, ByN (2) 20001-29999, ETM
(3) 30001-39999 y Unimetro (4) 40001-49999.
"""

FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"
"""Formato de fecha y hora usado en las columnas de auditoría."""

_SQL_LISTAR_EMPRESAS = text(
    "SELECT id_empresa, nombre_empresa FROM dim_empresa ORDER BY id_empresa"
)

_SQL_LISTAR_TIPOLOGIAS = text(
    """
    SELECT id_perfil_tipologia, autoriza_articulado, autoriza_padron,
           autoriza_complementario, autoriza_auxiliar
    FROM dim_perfil_tipologia
    ORDER BY id_perfil_tipologia
    """
)

_SQL_CONTAR_OPERADOR_VIGENTE = text(
    """
    SELECT COUNT(*)
    FROM dim_codigo
    WHERE id_persona = :cedula AND id_vigencia = :vigencia
    """
)

_SQL_CONTAR_PERSONA = text("SELECT COUNT(*) FROM dim_persona WHERE id_persona = :cedula")

_SQL_INSERT_PERSONA = text(
    """
    INSERT INTO dim_persona
        (id_persona, primer_apellido, segundo_apellido, nombres, genero,
         id_vigencia, fecha_registro, usuario_registra)
    VALUES
        (:cedula, :primer_apellido, :segundo_apellido, :nombres, :genero,
         :vigencia, :fecha, :usuario)
    """
)

_SQL_ACTUALIZAR_PERSONA = text(
    """
    UPDATE dim_persona
    SET primer_apellido = :primer_apellido,
        segundo_apellido = :segundo_apellido,
        nombres = :nombres,
        genero = :genero,
        fecha_registro = :fecha,
        usuario_registra = :usuario
    WHERE id_persona = :cedula
    """
)

_SQL_SIGUIENTE_CODIGO = text(
    """
    SELECT COALESCE(MAX(id_codigo), :base) + 1
    FROM dim_codigo
    WHERE id_codigo >= :base AND id_codigo < :limite
    """
)

_SQL_INSERT_CODIGO = text(
    """
    INSERT INTO dim_codigo
        (id_codigo, id_persona, id_empresa, id_perfil_tipologia, id_vigencia,
         fecha_registro, usuario_registra)
    VALUES
        (:codigo, :cedula, :empresa, :tipologia, :vigencia, :fecha, :usuario)
    """
)

_SQL_INSERT_AUDITORIA = text(
    """
    INSERT INTO log_auditoria (usuario, accion, detalles)
    VALUES (:usuario, :accion, :detalles)
    """
)


def _contar(
    conexion: Connection, sentencia: TextClause, parametros: dict[str, int] | None = None
) -> int:
    """Ejecuta un ``COUNT(*)`` y devuelve el entero resultante.

    Args:
        conexion: Conexión SQLAlchemy activa.
        sentencia: Consulta ``COUNT`` parametrizable.
        parametros: Valores enlazados opcionales.

    Returns:
        El conteo como entero.
    """
    resultado = conexion.execute(sentencia, parametros or {}).scalar_one()
    return int(resultado)


class OperadoresRepository:
    """Repositorio de consultas de operadores sobre SQLite.

    Concentra toda la ejecución de SQLAlchemy. El motor se inyecta (por defecto
    se resuelve de forma perezosa desde
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

    def verificar_conexion(self) -> bool:
        """Verifica el estado de la conexión a la base de datos.

        Returns:
            ``True`` si se puede abrir una conexión y ejecutar una consulta
            trivial; ``False`` ante cualquier error de SQLAlchemy.
        """
        try:
            with self.motor.connect() as conexion:
                conexion.execute(_SQL_PING)
            return True
        except SQLAlchemyError:
            return False

    def obtener_operador_por_cedula(self, cedula: int) -> OperadorInfo | None:
        """Consulta un operador por su número de cédula.

        Args:
            cedula: Número de documento (``dim_persona.id_persona``).

        Returns:
            El operador vigente de menor código, o ``None`` si no existe.
        """
        return self._consultar_operador(_SQL_OPERADOR_POR_CEDULA, {"cedula": cedula})

    def obtener_operador_por_codigo(self, codigo: int) -> OperadorInfo | None:
        """Consulta un operador por su código de operación.

        Args:
            codigo: Código de operación (``dim_codigo.id_codigo``).

        Returns:
            El operador asociado, o ``None`` si no existe.
        """
        return self._consultar_operador(_SQL_OPERADOR_POR_CODIGO, {"codigo": codigo})

    def validar_certificado(self, codigo: int) -> EstadoCertificado:
        """Valida el certificado de idoneidad de un operador.

        Consulta la última certificación y la existencia de cancelaciones, y
        delega el cálculo del estado en la función pura de dominio
        :func:`calcular_estado_certificado`.

        Args:
            codigo: Código de operación del operador.

        Returns:
            El estado calculado del certificado.
        """
        with self.motor.connect() as conexion:
            ultima = conexion.execute(
                _SQL_ULTIMO_CERTIFICADO,
                {"codigo": codigo, "tipos": list(TIPOS_EVENTO_CERTIFICADO)},
            ).scalar_one()
            cancelaciones = conexion.execute(
                _SQL_TIENE_CANCELACION,
                {"codigo": codigo, "tipo_cancelacion": TIPO_EVENTO_CANCELACION},
            ).scalar_one()

        return calcular_estado_certificado(codigo, ultima, int(cancelaciones) > 0)

    def estadisticas_basicas(self) -> EstadisticasBasicas:
        """Calcula conteos generales de operadores, empresas y licencias.

        Returns:
            Las estadísticas básicas. Si el esquema aún no está cargado devuelve
            conteos en cero, en lugar de propagar el error, para no romper los
            tableros.
        """
        try:
            with self.motor.connect() as conexion:
                total = _contar(conexion, _SQL_TOTAL_OPERADORES)
                vigentes = _contar(
                    conexion, _SQL_OPERADORES_POR_VIGENCIA, {"vigencia": VIGENCIA_ACTIVA}
                )
                anulados = _contar(
                    conexion, _SQL_OPERADORES_POR_VIGENCIA, {"vigencia": VIGENCIA_ANULADA}
                )
                empresas = _contar(conexion, _SQL_TOTAL_EMPRESAS)
                licencias = _contar(conexion, _SQL_TOTAL_LICENCIAS)
        except SQLAlchemyError:
            return EstadisticasBasicas(0, 0, 0, 0, 0)
        return EstadisticasBasicas(total, vigentes, anulados, empresas, licencias)

    def listar_empresas(self) -> list[EmpresaInfo]:
        """Lista las empresas concesionarias oficiales ordenadas por id.

        Returns:
            Las empresas disponibles para el desplegable del formulario.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR_EMPRESAS).mappings().all()
        return [
            EmpresaInfo(
                id_empresa=int(fila["id_empresa"]),
                nombre_empresa=str(fila["nombre_empresa"] or ""),
            )
            for fila in filas
        ]

    def listar_tipologias(self) -> list[TipologiaInfo]:
        """Lista las tipologías de bus oficiales con su descripción legible.

        Returns:
            Las tipologías disponibles para el desplegable del formulario.
        """
        with self.motor.connect() as conexion:
            filas = conexion.execute(_SQL_LISTAR_TIPOLOGIAS).mappings().all()
        return [
            TipologiaInfo(
                id_perfil_tipologia=int(fila["id_perfil_tipologia"]),
                descripcion=construir_descripcion_tipologia(
                    int(fila["id_perfil_tipologia"]),
                    bool(fila["autoriza_articulado"]),
                    bool(fila["autoriza_padron"]),
                    bool(fila["autoriza_complementario"]),
                    bool(fila["autoriza_auxiliar"]),
                ),
            )
            for fila in filas
        ]

    def existe_operador_vigente(self, cedula: int) -> bool:
        """Indica si la cédula ya tiene un código de operación vigente.

        Args:
            cedula: Número de documento del operador.

        Returns:
            ``True`` si existe al menos un código vigente para la cédula.
        """
        with self.motor.connect() as conexion:
            total = conexion.execute(
                _SQL_CONTAR_OPERADOR_VIGENTE,
                {"cedula": cedula, "vigencia": VIGENCIA_ACTIVA},
            ).scalar_one()
        return int(total) > 0

    def siguiente_codigo(self, id_empresa: int) -> int:
        """Calcula el siguiente código de operación dentro del rango del concesionario.

        Cada concesionario tiene su propio bloque numérico de códigos (spec 024):
        el siguiente código se obtiene del máximo ya asignado dentro de
        ``[id_empresa * 10000, (id_empresa + 1) * 10000)``, de modo que GIT (1)
        arranca en 10001, ByN (2) en 20001, ETM (3) en 30001 y Unimetro (4) en
        40001.

        Args:
            id_empresa: Identificador del concesionario al que pertenece el código.

        Returns:
            El siguiente código libre del rango del concesionario.
        """
        with self.motor.connect() as conexion:
            return self._siguiente_codigo(conexion, id_empresa)

    def _siguiente_codigo(self, conexion: Connection, id_empresa: int) -> int:
        """Resuelve el siguiente código sobre una conexión ya abierta.

        Se usa dentro de la transacción de :meth:`crear_operador` para que el
        cálculo del código y su inserción sean atómicos.

        Args:
            conexion: Conexión SQLAlchemy activa (dentro de la transacción).
            id_empresa: Identificador del concesionario.

        Returns:
            El siguiente código libre del rango del concesionario.
        """
        base = int(id_empresa) * BASE_CODIGO_CONCESIONARIO
        limite = (int(id_empresa) + 1) * BASE_CODIGO_CONCESIONARIO
        resultado = conexion.execute(
            _SQL_SIGUIENTE_CODIGO, {"base": base, "limite": limite}
        ).scalar_one()
        return int(resultado)

    def crear_operador(self, registro: RegistroOperador, usuario: str = "") -> int:
        """Persiste un operador nuevo en ``dim_persona`` y ``dim_codigo``.

        Inserta (o actualiza si la persona ya existe) la fila de ``dim_persona``,
        asigna el siguiente código de operación en ``dim_codigo`` y registra la
        acción en ``log_auditoria`` dentro de la **misma transacción** para que
        el guardado sea atómico.

        Args:
            registro: Datos del operador capturados por la interfaz.
            usuario: Usuario que realiza el guardado (para auditoría).

        Returns:
            El código de operación asignado al operador.
        """
        fecha = datetime.now().strftime(FORMATO_FECHA_HORA)
        datos_persona = {
            "cedula": registro.cedula,
            "primer_apellido": registro.primer_apellido,
            "segundo_apellido": registro.segundo_apellido,
            "nombres": registro.nombres,
            "genero": registro.genero,
            "vigencia": registro.id_vigencia,
            "fecha": fecha,
            "usuario": usuario,
        }
        with self.motor.begin() as conexion:
            existe = conexion.execute(_SQL_CONTAR_PERSONA, {"cedula": registro.cedula}).scalar_one()
            if int(existe) > 0:
                conexion.execute(_SQL_ACTUALIZAR_PERSONA, datos_persona)
            else:
                conexion.execute(_SQL_INSERT_PERSONA, datos_persona)

            codigo = self._siguiente_codigo(conexion, registro.id_empresa)
            conexion.execute(
                _SQL_INSERT_CODIGO,
                {
                    "codigo": codigo,
                    "cedula": registro.cedula,
                    "empresa": registro.id_empresa,
                    "tipologia": registro.id_perfil_tipologia,
                    "vigencia": registro.id_vigencia,
                    "fecha": fecha,
                    "usuario": usuario,
                },
            )
            conexion.execute(
                _SQL_INSERT_AUDITORIA,
                {
                    "usuario": usuario,
                    "accion": ACCION_CREAR_OPERADOR,
                    "detalles": f"Cédula {registro.cedula} - código {codigo}",
                },
            )
        return codigo

    def _consultar_operador(
        self, sentencia: TextClause, parametros: dict[str, int]
    ) -> OperadorInfo | None:
        """Ejecuta una consulta de operador y mapea la fila al DTO de dominio.

        Args:
            sentencia: Sentencia SQLAlchemy parametrizada.
            parametros: Valores enlazados a la sentencia.

        Returns:
            El operador mapeado o ``None`` si no hay filas.
        """
        with self.motor.connect() as conexion:
            fila = conexion.execute(sentencia, parametros).mappings().first()
        if fila is None:
            return None
        return OperadorInfo(
            codigo=int(fila["id_codigo"]),
            cedula=int(fila["id_persona"]),
            nombres=str(fila["nombres"] or ""),
            primer_apellido=str(fila["primer_apellido"] or ""),
            segundo_apellido=str(fila["segundo_apellido"] or ""),
            genero=str(fila["genero"] or ""),
            id_empresa=int(fila["id_empresa"]),
            nombre_empresa=str(fila["nombre_empresa"] or ""),
            id_perfil_tipologia=int(fila["id_perfil_tipologia"]),
            id_vigencia=int(fila["id_vigencia"]),
        )
