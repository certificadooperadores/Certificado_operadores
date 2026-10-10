"""Pruebas de la corrección de registros (spec 006).

Cubren tres frentes: el repositorio ``EventosRepository`` contra una base SQLite
temporal (tipos de evento, búsqueda con filtros, lotes y mutaciones con
auditoría), las funciones puras de la UI y las verificaciones estáticas de los
criterios de aceptación: el paquete existe, la UI y la página no contienen SQL y
la página usa ``render_correccion_registros`` sin funciones inlined. Todas las
pruebas siguen el patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from certificado_operadores.domain.models import VIGENCIA_ACTIVA, VIGENCIA_ANULADA
from certificado_operadores.domain.usuarios import (
    ROL_ADMINISTRADOR,
    ROL_SUPER_ADMINISTRADOR,
)
from certificado_operadores.infra.eventos_repository import (
    ACCION_ANULAR_LOTE,
    ACCION_ANULAR_REGISTROS,
    ACCION_ELIMINAR_LOTE,
    ACCION_ELIMINAR_REGISTROS,
    ACCION_REACTIVAR_LOTE,
    ACCION_REACTIVAR_REGISTROS,
    EventoInfo,
    EventosRepository,
    FiltroEventos,
    LoteInfo,
    TipoEventoInfo,
)
from certificado_operadores.modulos.correccion_registros import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "1_Configuracion.py"
_RUTA_HEREDADO = _RUTA_UI.parents[1] / "3_Modificacion_Tablas.py"

_LOTE_CORTO = "2026-01-10 08:15"
_LOTE_MEDIO = "2026-01-10 09:40"
_LOTE_TARDIO = "2026-02-05 09:40"

# --- Esquema mínimo para las pruebas del repositorio ------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_tipo_evento (
        id_tipo_evento INTEGER PRIMARY KEY,
        nombre_evento TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE dim_persona (
        id_persona INTEGER PRIMARY KEY,
        nombres TEXT,
        primer_apellido TEXT
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY,
        id_persona INTEGER NOT NULL
    );
    """,
    """
    CREATE TABLE fact_eventos_operador (
        id_hecho_evento INTEGER PRIMARY KEY,
        id_codigo INTEGER NOT NULL,
        id_tipo_evento INTEGER NOT NULL,
        fecha_registro TEXT NOT NULL,
        id_vigencia INTEGER NOT NULL
    );
    """,
    """
    CREATE TABLE log_auditoria (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        accion TEXT NOT NULL,
        detalles TEXT,
        fecha_registro TEXT
    );
    """,
)

_TIPOS = ((1, "Certificación"), (2, "Reactivación"), (7, "Cancelación"))

_EVENTOS = (
    # (id, id_codigo, id_tipo_evento, fecha_registro, id_vigencia)
    (1, 5001, 1, "2026-01-10 08:15:00", VIGENCIA_ACTIVA),
    (2, 5001, 2, "2026-01-10 08:15:30", VIGENCIA_ANULADA),
    (3, 5002, 1, "2026-01-10 09:40:00", VIGENCIA_ACTIVA),
    (4, 5002, 7, "2026-02-05 09:40:10", VIGENCIA_ACTIVA),
)


def _crear_esquema(motor: Engine) -> None:
    """Crea las tablas mínimas de eventos, dimensiones y auditoría.

    Args:
        motor: Motor SQLAlchemy donde se crea el esquema.
    """
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar_datos(motor: Engine) -> None:
    """Inserta tipos de evento, personas, códigos y eventos de ejemplo.

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_tipo_evento VALUES (:id, :nombre)"),
            [{"id": tipo, "nombre": nombre} for tipo, nombre in _TIPOS],
        )
        conexion.execute(
            text("INSERT INTO dim_persona VALUES (:id, :nombres, :apellido)"),
            [
                {"id": 1001, "nombres": "Ana", "apellido": "Pérez"},
                {"id": 1002, "nombres": "Luis", "apellido": "Rojas"},
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_codigo VALUES (:id_codigo, :id_persona)"),
            [
                {"id_codigo": 5001, "id_persona": 1001},
                {"id_codigo": 5002, "id_persona": 1002},
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador VALUES (:id, :codigo, :tipo, :fecha, :vigencia)"
            ),
            [
                {
                    "id": identificador,
                    "codigo": codigo,
                    "tipo": tipo,
                    "fecha": fecha,
                    "vigencia": vigencia,
                }
                for identificador, codigo, tipo, fecha, vigencia in _EVENTOS
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Engine:
    """Motor SQLite temporal con esquema y datos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_eventos.db'}")
    _crear_esquema(motor)
    _sembrar_datos(motor)
    return motor


@pytest.fixture
def repositorio(motor_sqlite: Engine) -> EventosRepository:
    """Repositorio de eventos configurado con el motor SQLite de prueba."""
    return EventosRepository(engine=motor_sqlite)


def _vigencia_de(motor: Engine, identificador: int) -> int:
    """Devuelve la vigencia almacenada de un evento."""
    with motor.connect() as conexion:
        return int(
            conexion.execute(
                text("SELECT id_vigencia FROM fact_eventos_operador WHERE id_hecho_evento = :id"),
                {"id": identificador},
            ).scalar_one()
        )


def _total_eventos(motor: Engine) -> int:
    """Cuenta las filas de ``fact_eventos_operador``."""
    with motor.connect() as conexion:
        return int(
            conexion.execute(text("SELECT COUNT(*) FROM fact_eventos_operador")).scalar_one()
        )


def _auditoria(motor: Engine) -> list[tuple[str, str]]:
    """Devuelve las acciones de auditoría registradas como pares (acción, detalle)."""
    with motor.connect() as conexion:
        filas = conexion.execute(
            text("SELECT accion, detalles FROM log_auditoria ORDER BY id_log")
        ).all()
    return [(str(accion), str(detalles or "")) for accion, detalles in filas]


def _ids(eventos: Iterable[EventoInfo]) -> list[int]:
    """Extrae los identificadores de una lista de eventos."""
    return [evento.id_hecho_evento for evento in eventos]


# --- Repositorio: tipos de evento -------------------------------------------
def test_listar_tipos_evento_devuelve_dtos_ordenados(repositorio: EventosRepository) -> None:
    """El repositorio devuelve los tipos de evento ordenados por id."""
    # Arrange / Act
    tipos = repositorio.listar_tipos_evento()

    # Assert
    assert tipos == [
        TipoEventoInfo(1, "Certificación"),
        TipoEventoInfo(2, "Reactivación"),
        TipoEventoInfo(7, "Cancelación"),
    ]


# --- Repositorio: búsqueda con filtros (RF-01) ------------------------------
def test_buscar_eventos_sin_filtro_devuelve_todos(repositorio: EventosRepository) -> None:
    """RF-01: sin filtros se listan todos los eventos, del más reciente al más antiguo."""
    # Arrange / Act
    eventos = repositorio.buscar_eventos()

    # Assert
    assert _ids(eventos) == [4, 3, 2, 1]
    assert eventos[0].nombre == "Luis Rojas"
    assert eventos[0].estado == "Vigente"
    assert eventos[0].id_vigencia == VIGENCIA_ACTIVA


def test_buscar_eventos_filtra_por_codigo(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por código limita los eventos del operador."""
    # Arrange
    filtro = FiltroEventos(codigo=5001)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [2, 1]


def test_buscar_eventos_filtra_por_cedula(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por cédula cruza ``dim_codigo`` y ``dim_persona``."""
    # Arrange
    filtro = FiltroEventos(cedula=1002)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [4, 3]


def test_buscar_eventos_filtra_por_tipo(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por tipo de evento deja solo ese tipo."""
    # Arrange
    filtro = FiltroEventos(id_tipo_evento=1)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [3, 1]


def test_buscar_eventos_filtra_por_vigencia(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por estado deja solo los eventos de esa vigencia."""
    # Arrange
    filtro = FiltroEventos(vigencia=VIGENCIA_ANULADA)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [2]
    assert eventos[0].estado == "Anulado"


def test_buscar_eventos_filtra_por_rango_de_fechas(repositorio: EventosRepository) -> None:
    """RF-01: el rango de fechas es inclusivo en ambos extremos."""
    # Arrange
    filtro = FiltroEventos(
        fecha_desde=date(2026, 1, 10),
        fecha_hasta=date(2026, 1, 31),
    )

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [3, 2, 1]


def test_buscar_eventos_respeta_el_limite(repositorio: EventosRepository) -> None:
    """RF-01: la búsqueda nunca devuelve más filas que el límite indicado."""
    # Arrange
    filtro = FiltroEventos(limite=2)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [4, 3]


# --- Repositorio: lotes (RF-02) ---------------------------------------------
def test_listar_lotes_agrupa_por_minuto(repositorio: EventosRepository) -> None:
    """RF-02: los lotes se agrupan por minuto de cargue, del más reciente al más antiguo."""
    # Arrange / Act
    lotes = repositorio.listar_lotes()

    # Assert
    assert lotes == [
        LoteInfo(_LOTE_TARDIO, 1),
        LoteInfo(_LOTE_MEDIO, 1),
        LoteInfo(_LOTE_CORTO, 2),
    ]


def test_listar_eventos_de_lote(repositorio: EventosRepository) -> None:
    """RF-02: el detalle del lote incluye solo los eventos de ese minuto."""
    # Act
    eventos = repositorio.listar_eventos_de_lote(_LOTE_CORTO)

    # Assert
    assert _ids(eventos) == [1, 2]
    assert {evento.estado for evento in eventos} == {"Vigente", "Anulado"}


# --- Repositorio: mutaciones con auditoría (CA-03) --------------------------
def test_reactivar_registros_cambia_vigencia_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: reactivar actualiza la vigencia y registra la auditoría."""
    # Act
    afectados = repositorio.reactivar_registros([2], "admin")

    # Assert
    assert afectados == 1
    assert _vigencia_de(motor_sqlite, 2) == VIGENCIA_ACTIVA
    assert _auditoria(motor_sqlite) == [(ACCION_REACTIVAR_REGISTROS, "IDs: 2")]


def test_anular_registros_cambia_vigencia_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: anular actualiza la vigencia de todos los ids y audita."""
    # Act
    afectados = repositorio.anular_registros([1, 3], "admin")

    # Assert
    assert afectados == 2
    assert _vigencia_de(motor_sqlite, 1) == VIGENCIA_ANULADA
    assert _vigencia_de(motor_sqlite, 3) == VIGENCIA_ANULADA
    assert _auditoria(motor_sqlite) == [(ACCION_ANULAR_REGISTROS, "IDs: 1,3")]


def test_eliminar_registros_borra_fisicamente_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: eliminar borra la fila y registra la auditoría."""
    # Act
    afectados = repositorio.eliminar_registros([4], "admin")

    # Assert
    assert afectados == 1
    assert _total_eventos(motor_sqlite) == 3
    assert _auditoria(motor_sqlite) == [(ACCION_ELIMINAR_REGISTROS, "IDs: 4")]


def test_mutar_sin_ids_no_afecta_ni_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: una selección vacía no ejecuta SQL ni deja auditoría."""
    # Arrange / Act
    afectados = repositorio.reactivar_registros([], "admin")

    # Assert
    assert afectados == 0
    assert _auditoria(motor_sqlite) == []
    assert _total_eventos(motor_sqlite) == 4


def test_reactivar_lote_afecta_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: reactivar el lote actualiza todos sus eventos y audita."""
    # Act
    afectados = repositorio.reactivar_lote(_LOTE_CORTO, "admin")

    # Assert
    assert afectados == 2
    assert _vigencia_de(motor_sqlite, 1) == VIGENCIA_ACTIVA
    assert _vigencia_de(motor_sqlite, 2) == VIGENCIA_ACTIVA
    assert _auditoria(motor_sqlite) == [(ACCION_REACTIVAR_LOTE, f"Lote:{_LOTE_CORTO}")]


def test_anular_lote_afecta_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: anular el lote actualiza todos sus eventos y audita."""
    # Act
    afectados = repositorio.anular_lote(_LOTE_CORTO, "admin")

    # Assert
    assert afectados == 2
    assert _auditoria(motor_sqlite) == [(ACCION_ANULAR_LOTE, f"Lote:{_LOTE_CORTO}")]


def test_eliminar_lote_borra_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: eliminar el lote borra sus eventos y audita."""
    # Act
    afectados = repositorio.eliminar_lote(_LOTE_TARDIO, "admin")

    # Assert
    assert afectados == 1
    assert _total_eventos(motor_sqlite) == 3
    assert _auditoria(motor_sqlite) == [(ACCION_ELIMINAR_LOTE, f"Lote:{_LOTE_TARDIO}")]


def test_registrar_auditoria_persiste_la_accion(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """El repositorio expone el registro de auditoría de forma explícita."""
    # Act
    repositorio.registrar_auditoria("admin", "Acción Manual", "detalle")

    # Assert
    assert _auditoria(motor_sqlite) == [("Acción Manual", "detalle")]


# --- UI: funciones puras -----------------------------------------------------
def test_parsear_entero_positivo() -> None:
    """Los campos numéricos se traducen a enteros positivos o ``None``."""
    # Arrange / Act / Assert
    assert ui.parsear_entero_positivo("  5001 ") == 5001
    assert ui.parsear_entero_positivo("0") is None
    assert ui.parsear_entero_positivo("abc") is None
    assert ui.parsear_entero_positivo("") is None


def test_opciones_tipos_evento_antepone_todos() -> None:
    """El selector de tipo de evento incluye "Todos" al inicio."""
    # Arrange
    tipos = [TipoEventoInfo(1, "Certificación"), TipoEventoInfo(7, "Cancelación")]

    # Act / Assert
    assert ui.opciones_tipos_evento(tipos) == ["Todos", "1 - Certificación", "7 - Cancelación"]


def test_id_tipo_evento_desde_opcion() -> None:
    """La opción "Todos" no filtra; "id - nombre" traduce el id."""
    # Arrange / Act / Assert
    assert ui.id_tipo_evento_desde_opcion("Todos") is None
    assert ui.id_tipo_evento_desde_opcion("7 - Cancelación") == 7


def test_vigencia_desde_estado() -> None:
    """El estado legible se traduce a la vigencia de la base."""
    # Arrange / Act / Assert
    assert ui.vigencia_desde_estado("Vigente") == VIGENCIA_ACTIVA
    assert ui.vigencia_desde_estado("Anulado") == VIGENCIA_ANULADA
    assert ui.vigencia_desde_estado("Todos") is None


def test_construir_filtro_traduce_los_campos() -> None:
    """Los campos del formulario se traducen a un ``FiltroEventos``."""
    # Arrange / Act
    filtro = ui.construir_filtro(
        "5001", "1001", "1 - Certificación", "Anulado", date(2026, 1, 1), date(2026, 1, 31)
    )

    # Assert
    assert filtro == FiltroEventos(
        codigo=5001,
        cedula=1001,
        id_tipo_evento=1,
        vigencia=VIGENCIA_ANULADA,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
    )


def test_etiqueta_lote_y_lote_desde_etiqueta() -> None:
    """La etiqueta del lote es reversible."""
    # Arrange
    lote = LoteInfo(_LOTE_CORTO, 2)

    # Act
    etiqueta = ui.etiqueta_lote(lote)

    # Assert
    assert etiqueta == "2026-01-10 08:15 (2 reg.)"
    assert ui.lote_desde_etiqueta(etiqueta) == _LOTE_CORTO


def test_filas_eventos_mapea_columnas_legibles() -> None:
    """La tabla de la UI expone columnas legibles."""
    # Arrange
    evento = EventoInfo(
        id_hecho_evento=1,
        id_codigo=5001,
        cedula=1001,
        nombre="Ana Pérez",
        nombre_evento="Certificación",
        fecha="2026-01-10 08:15:00",
        id_vigencia=VIGENCIA_ACTIVA,
    )

    # Act
    filas = ui.filas_eventos([evento])

    # Assert
    assert filas == [
        {
            "ID": 1,
            "Código": 5001,
            "Cédula": 1001,
            "Nombre": "Ana Pérez",
            "Evento": "Certificación",
            "Fecha": "2026-01-10 08:15:00",
            "Estado": "Vigente",
        }
    ]


class _SeleccionFalsa:
    """Doble del objeto de selección de ``st.dataframe``."""

    def __init__(self, filas: list[int]) -> None:
        """Configura las filas seleccionadas."""
        self.selection = type("_Sel", (), {"rows": filas})()


def test_filas_seleccionadas_extrae_los_indices() -> None:
    """La selección de la tabla se traduce a índices enteros."""
    # Arrange / Act / Assert
    assert ui.filas_seleccionadas(_SeleccionFalsa([0, 2])) == [0, 2]
    assert ui.filas_seleccionadas(None) == []


def test_puede_eliminar_solo_super_admin() -> None:
    """Solo el rol Super Administrador puede eliminar registros."""
    # Arrange / Act / Assert
    assert ui.puede_eliminar(ROL_SUPER_ADMINISTRADOR) is True
    assert ui.puede_eliminar(ROL_ADMINISTRADOR) is False


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_correccion_registros_existe() -> None:
    """CA-01: el paquete expone ``render_correccion_registros``."""
    # Arrange / Act
    from certificado_operadores.modulos.correccion_registros import (
        render_correccion_registros,
    )

    # Assert
    assert callable(render_correccion_registros)


def test_ui_no_contiene_sql_ni_acceso_directo() -> None:
    """CA-02/RNF-01: la UI no contiene SQL ni acceso directo a la base de datos."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8").upper()
    patron = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")
    acceso_directo = ("RUN_QUERY", "RUN_TRANSACTION")

    # Act
    sentencias = patron.findall(contenido)
    directos = [palabra for palabra in acceso_directo if palabra in contenido]

    # Assert
    assert sentencias == []
    assert directos == []


def test_pagina_usa_render_correccion_registros_sin_funciones_inlined() -> None:
    """CA-02: la página importa la función y no contiene la corrección inlined."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_correccion_registros" in contenido
    assert "def modulo_correccion" not in contenido
    assert "def correccion_individual" not in contenido
    assert "def correccion_lote" not in contenido
    assert "run_query" not in contenido
    assert "run_transaction" not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")


def test_modulo_heredado_deprecado_sin_sql() -> None:
    """El módulo heredado quedó eliminado o deprecado sin SQL."""
    # Arrange / Act / Assert
    if not _RUTA_HEREDADO.exists():
        assert not _RUTA_HEREDADO.exists()
        return

    contenido = _RUTA_HEREDADO.read_text(encoding="utf-8").upper()
    patron = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|DROP)\s")

    assert "RENDER_CORRECCION_REGISTROS" in contenido
    assert patron.findall(contenido) == []
