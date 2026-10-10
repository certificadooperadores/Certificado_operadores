"""Pruebas de la corrección de registros (spec 015).

Cubren cuatro frentes: el repositorio ``EventosRepository`` contra una base
SQLite temporal (búsqueda con filtros y mutaciones de la spec 006, más el
listado y las mutaciones genéricas por tabla de la spec 015), las funciones
puras de la UI, el catálogo de tablas soportadas y las verificaciones estáticas
de los criterios de aceptación: el paquete existe, la UI organiza la corrección
en sub-pestañas por tabla, no contiene SQL ni filtros externos masivos, usa la
tabla interactiva con selección múltiple y expone los botones de acción. Todas
las pruebas siguen el patrón AAA (*Arrange · Act · Assert*).

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
    ACCION_ANULAR_REGISTROS,
    ACCION_ELIMINAR_LOTE,
    ACCION_ELIMINAR_REGISTROS,
    ACCION_REACTIVAR_LOTE,
    ACCION_REACTIVAR_REGISTROS,
    TABLAS_CORRECCION,
    DefinicionTabla,
    EventoInfo,
    EventosRepository,
    FiltroEventos,
    LoteInfo,
    RegistroInfo,
    TipoEventoInfo,
)
from certificado_operadores.modulos.correccion_registros import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "1_Configuracion.py"
_RUTA_HEREDADO = _RUTA_UI.parents[1] / "3_Modificacion_Tablas.py"

_LOTE_CORTO = "2026-01-10 08:15"
_LOTE_MEDIO = "2026-01-10 09:40"
_LOTE_TARDIO = "2026-02-05 09:40"

CLAVES_TABLAS = ("eventos", "licencias", "comportamientos", "operadores")
ETIQUETAS_TABLAS = ("Eventos", "Licencias", "Comportamientos", "Operadores")

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
        primer_apellido TEXT,
        segundo_apellido TEXT,
        genero TEXT,
        id_vigencia INTEGER
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
    CREATE TABLE fact_licencias (
        id_hecho_licencia INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        tipo TEXT,
        vencimiento TEXT,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE fact_comportamiento (
        id_hecho_comportamiento INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        fuente TEXT,
        descripcion_comportamiento TEXT,
        fecha_evento TEXT,
        id_vigencia INTEGER NOT NULL,
        fecha_registro TEXT
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

_LICENCIAS = (
    # (id, id_codigo, tipo, vencimiento, id_vigencia, fecha_registro)
    (1, 5001, "C3", "2030-01-01", VIGENCIA_ACTIVA, "2026-01-10 08:00:00"),
    (2, 5002, "C2", "2031-01-01", VIGENCIA_ANULADA, "2026-02-01 08:00:00"),
)

_COMPORTAMIENTOS = (
    # (id, id_codigo, fuente, descripcion, fecha_evento, id_vigencia, fecha_registro)
    (1, 5001, "PQRS", "Exceso de velocidad", "2026-01-05", VIGENCIA_ACTIVA, "2026-01-10"),
    (2, 5002, "Operativo", "Alta sin cinturón", "2026-02-05", VIGENCIA_ACTIVA, "2026-02-06"),
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
    """Inserta tipos, personas, códigos y registros de ejemplo.

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_tipo_evento VALUES (:id, :nombre)"),
            [{"id": tipo, "nombre": nombre} for tipo, nombre in _TIPOS],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_persona "
                "(id_persona, nombres, primer_apellido, segundo_apellido, genero, id_vigencia) "
                "VALUES (:id, :nombres, :apellido, :segundo, :genero, :vigencia)"
            ),
            [
                {
                    "id": 1001,
                    "nombres": "Ana",
                    "apellido": "Pérez",
                    "segundo": "Gómez",
                    "genero": "F",
                    "vigencia": VIGENCIA_ACTIVA,
                },
                {
                    "id": 1002,
                    "nombres": "Luis",
                    "apellido": "Rojas",
                    "segundo": "",
                    "genero": "M",
                    "vigencia": VIGENCIA_ACTIVA,
                },
                {
                    "id": 1003,
                    "nombres": "Marta",
                    "apellido": "López",
                    "segundo": "Díaz",
                    "genero": "F",
                    "vigencia": VIGENCIA_ANULADA,
                },
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_codigo (id_codigo, id_persona) VALUES (:id_codigo, :id_persona)"),
            [
                {"id_codigo": 5001, "id_persona": 1001},
                {"id_codigo": 5002, "id_persona": 1002},
                {"id_codigo": 5003, "id_persona": 1003},
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador "
                "(id_hecho_evento, id_codigo, id_tipo_evento, fecha_registro, id_vigencia) "
                "VALUES (:id, :codigo, :tipo, :fecha, :vigencia)"
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
        conexion.execute(
            text(
                "INSERT INTO fact_licencias "
                "(id_hecho_licencia, id_codigo, tipo, vencimiento, id_vigencia, fecha_registro) "
                "VALUES (:id, :codigo, :tipo, :vencimiento, :vigencia, :fecha)"
            ),
            [
                {
                    "id": identificador,
                    "codigo": codigo,
                    "tipo": tipo,
                    "vencimiento": vencimiento,
                    "vigencia": vigencia,
                    "fecha": fecha,
                }
                for identificador, codigo, tipo, vencimiento, vigencia, fecha in _LICENCIAS
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_comportamiento "
                "(id_hecho_comportamiento, id_codigo, fuente, descripcion_comportamiento, "
                "fecha_evento, id_vigencia, fecha_registro) "
                "VALUES (:id, :codigo, :fuente, :descripcion, :fecha_evento, :vigencia, :fecha)"
            ),
            [
                {
                    "id": identificador,
                    "codigo": codigo,
                    "fuente": fuente,
                    "descripcion": descripcion,
                    "fecha_evento": fecha_evento,
                    "vigencia": vigencia,
                    "fecha": fecha,
                }
                for (
                    identificador,
                    codigo,
                    fuente,
                    descripcion,
                    fecha_evento,
                    vigencia,
                    fecha,
                ) in _COMPORTAMIENTOS
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


def _vigencia_de(motor: Engine, tabla: str, columna: str, identificador: int) -> int:
    """Devuelve la vigencia almacenada de un registro de cualquier tabla."""
    with motor.connect() as conexion:
        return int(
            conexion.execute(
                text(f"SELECT id_vigencia FROM {tabla} WHERE {columna} = :id"),
                {"id": identificador},
            ).scalar_one()
        )


def _total(motor: Engine, tabla: str) -> int:
    """Cuenta las filas de una tabla."""
    with motor.connect() as conexion:
        return int(conexion.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar_one())


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


def _definicion(clave: str) -> DefinicionTabla:
    """Devuelve la definición del catálogo para una clave."""
    return next(definicion for definicion in TABLAS_CORRECCION if definicion.clave == clave)


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


# --- Repositorio: búsqueda con filtros (spec 006) ---------------------------
def test_buscar_eventos_sin_filtro_devuelve_todos(repositorio: EventosRepository) -> None:
    """RF-01: sin filtros se listan todos los eventos, del más reciente al más antiguo."""
    # Arrange / Act
    eventos = repositorio.buscar_eventos()

    # Assert
    assert _ids(eventos) == [4, 3, 2, 1]
    assert eventos[0].nombre == "Luis Rojas"
    assert eventos[0].estado == "Vigente"


def test_buscar_eventos_filtra_por_codigo(repositorio: EventosRepository) -> None:
    """RF-01: el filtro por código limita los eventos del operador."""
    # Arrange
    filtro = FiltroEventos(codigo=5001)

    # Act
    eventos = repositorio.buscar_eventos(filtro)

    # Assert
    assert _ids(eventos) == [2, 1]


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
    filtro = FiltroEventos(fecha_desde=date(2026, 1, 10), fecha_hasta=date(2026, 1, 31))

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


# --- Repositorio: lotes (spec 006) ------------------------------------------
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


def test_reactivar_lote_afecta_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: reactivar el lote actualiza todos sus eventos y audita."""
    # Act
    afectados = repositorio.reactivar_lote(_LOTE_CORTO, "admin")

    # Assert
    assert afectados == 2
    assert _vigencia_de(motor_sqlite, "fact_eventos_operador", "id_hecho_evento", 2) == (
        VIGENCIA_ACTIVA
    )
    assert _auditoria(motor_sqlite) == [(ACCION_REACTIVAR_LOTE, f"Lote:{_LOTE_CORTO}")]


# --- Repositorio: mutaciones individuales con auditoría (spec 006) ----------
def test_reactivar_registros_cambia_vigencia_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: reactivar actualiza la vigencia y registra la auditoría."""
    # Act
    afectados = repositorio.reactivar_registros([2], "admin")

    # Assert
    assert afectados == 1
    assert _vigencia_de(motor_sqlite, "fact_eventos_operador", "id_hecho_evento", 2) == (
        VIGENCIA_ACTIVA
    )
    assert _auditoria(motor_sqlite) == [(ACCION_REACTIVAR_REGISTROS, "IDs: 2")]


def test_anular_registros_cambia_vigencia_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: anular actualiza la vigencia de todos los ids y audita."""
    # Act
    afectados = repositorio.anular_registros([1, 3], "admin")

    # Assert
    assert afectados == 2
    assert _auditoria(motor_sqlite) == [(ACCION_ANULAR_REGISTROS, "IDs: 1,3")]


def test_eliminar_registros_borra_fisicamente_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-03: eliminar borra la fila y registra la auditoría."""
    # Act
    afectados = repositorio.eliminar_registros([4], "admin")

    # Assert
    assert afectados == 1
    assert _total(motor_sqlite, "fact_eventos_operador") == 3
    assert _auditoria(motor_sqlite) == [(ACCION_ELIMINAR_REGISTROS, "IDs: 4")]


def test_eliminar_lote_borra_todo_el_lote(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """RF-02: eliminar el lote borra sus eventos y audita."""
    # Act
    afectados = repositorio.eliminar_lote(_LOTE_TARDIO, "admin")

    # Assert
    assert afectados == 1
    assert _auditoria(motor_sqlite) == [(ACCION_ELIMINAR_LOTE, f"Lote:{_LOTE_TARDIO}")]


# --- Catálogo de tablas (spec 015) ------------------------------------------
def test_catalogo_tablas_expone_las_cuatro_tablas() -> None:
    """CA-01: el catálogo declara las cuatro tablas en el orden de las sub-pestañas."""
    # Arrange / Act
    claves = tuple(definicion.clave for definicion in TABLAS_CORRECCION)
    etiquetas = tuple(definicion.etiqueta for definicion in TABLAS_CORRECCION)

    # Assert
    assert claves == CLAVES_TABLAS
    assert etiquetas == ETIQUETAS_TABLAS


# --- Repositorio: listado genérico por tabla (spec 015) ---------------------
def test_listar_registros_eventos_mapea_filas(repositorio: EventosRepository) -> None:
    """CA-03: el listado genérico de eventos devuelve filas con etiquetas legibles."""
    # Act
    registros = repositorio.listar_registros("eventos")

    # Assert
    assert [registro.id_registro for registro in registros] == [4, 3, 2, 1]
    assert registros[0].datos["Nombre"] == "Luis Rojas"
    assert registros[0].datos["Evento"] == "Cancelación"
    assert registros[0].estado == "Vigente"
    assert registros[2].estado == "Anulado"


def test_listar_registros_licencias(repositorio: EventosRepository) -> None:
    """CA-01: la tabla de licencias expone sus columnas propias."""
    # Act
    registros = repositorio.listar_registros("licencias")

    # Assert
    assert [registro.id_registro for registro in registros] == [2, 1]
    assert registros[1].datos["Tipo"] == "C3"
    assert registros[1].datos["Cédula"] == 1001
    assert registros[0].estado == "Anulado"


def test_listar_registros_comportamientos(repositorio: EventosRepository) -> None:
    """CA-01: la tabla de comportamientos expone su fuente y descripción."""
    # Act
    registros = repositorio.listar_registros("comportamientos")

    # Assert
    assert [registro.id_registro for registro in registros] == [2, 1]
    assert registros[0].datos["Fuente"] == "Operativo"
    assert registros[1].datos["Descripción"] == "Exceso de velocidad"


def test_listar_registros_operadores(repositorio: EventosRepository) -> None:
    """CA-01: la tabla de operadores lista personas con su vigencia."""
    # Act
    registros = repositorio.listar_registros("operadores")

    # Assert
    assert [registro.id_registro for registro in registros] == [1001, 1002, 1003]
    assert registros[0].datos["Nombres"] == "Ana"
    assert registros[0].datos["Primer apellido"] == "Pérez"
    assert registros[2].estado == "Anulado"


def test_listar_registros_respeta_el_limite(repositorio: EventosRepository) -> None:
    """El listado genérico no devuelve más filas que el límite indicado."""
    # Act
    registros = repositorio.listar_registros("eventos", limite=2)

    # Assert
    assert [registro.id_registro for registro in registros] == [4, 3]


def test_listar_registros_clave_desconocida_lanza(repositorio: EventosRepository) -> None:
    """Una tabla fuera del catálogo produce un error explícito."""
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        repositorio.listar_registros("inexistente")


# --- Repositorio: mutaciones genéricas por tabla (spec 015) -----------------
def test_mutar_vigencia_reactiva_los_ids(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-04: reactivar cambia la vigencia a activa y audita con la tabla."""
    # Act
    afectados = repositorio.mutar_vigencia("licencias", [2], VIGENCIA_ACTIVA, "admin")

    # Assert
    assert afectados == 1
    assert _vigencia_de(motor_sqlite, "fact_licencias", "id_hecho_licencia", 2) == VIGENCIA_ACTIVA
    assert _auditoria(motor_sqlite) == [("Reactivar Licencias", "IDs: 2")]


def test_mutar_vigencia_anula_los_ids(repositorio: EventosRepository, motor_sqlite: Engine) -> None:
    """CA-04: anular cambia la vigencia a inactiva y audita."""
    # Act
    afectados = repositorio.mutar_vigencia("operadores", [1001, 1002], VIGENCIA_ANULADA, "admin")

    # Assert
    assert afectados == 2
    assert _vigencia_de(motor_sqlite, "dim_persona", "id_persona", 1001) == VIGENCIA_ANULADA
    assert _auditoria(motor_sqlite) == [("Anular Operadores", "IDs: 1001,1002")]


def test_eliminar_registros_tabla_borra_fisicamente_y_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """CA-04: eliminar borra el registro de la tabla y audita."""
    # Act
    afectados = repositorio.eliminar_registros_tabla("comportamientos", [2], "admin")

    # Assert
    assert afectados == 1
    assert _total(motor_sqlite, "fact_comportamiento") == 1
    assert _auditoria(motor_sqlite) == [("Eliminar Comportamientos", "IDs: 2")]


def test_mutar_vigencia_sin_ids_no_afecta_ni_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: una selección vacía no ejecuta SQL ni deja auditoría."""
    # Arrange / Act
    afectados = repositorio.mutar_vigencia("eventos", [], VIGENCIA_ACTIVA, "admin")

    # Assert
    assert afectados == 0
    assert _auditoria(motor_sqlite) == []


def test_eliminar_registros_tabla_sin_ids_no_afecta_ni_audita(
    repositorio: EventosRepository, motor_sqlite: Engine
) -> None:
    """Caso de borde: eliminar con una selección vacía no ejecuta SQL."""
    # Arrange / Act
    afectados = repositorio.eliminar_registros_tabla("operadores", [], "admin")

    # Assert
    assert afectados == 0
    assert _total(motor_sqlite, "dim_persona") == 3
    assert _auditoria(motor_sqlite) == []


# --- UI: funciones puras -----------------------------------------------------
def test_filas_registros_mapea_columnas_y_estado() -> None:
    """La tabla de la UI expone la columna ID, las visibles y el estado."""
    # Arrange
    registro = RegistroInfo(
        id_registro=2,
        id_vigencia=VIGENCIA_ANULADA,
        datos={
            "Código": 5002,
            "Cédula": 1002,
            "Nombre": "Luis Rojas",
            "Tipo": "C2",
            "Vencimiento": "2031-01-01",
        },
    )

    # Act
    filas = ui.filas_registros(_definicion("licencias"), [registro])

    # Assert
    assert filas == [
        {
            "ID": 2,
            "Código": 5002,
            "Cédula": 1002,
            "Nombre": "Luis Rojas",
            "Tipo": "C2",
            "Vencimiento": "2031-01-01",
            "Estado": "Anulado",
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


def test_ids_seleccionados_traduce_indices_y_descarta_invalidos() -> None:
    """Los índices de la tabla se traducen a IDs, ignorando los fuera de rango."""
    # Arrange
    registros = [
        RegistroInfo(10, VIGENCIA_ACTIVA, {}),
        RegistroInfo(20, VIGENCIA_ACTIVA, {}),
    ]

    # Act / Assert
    assert ui.ids_seleccionados(registros, [1, 0]) == [20, 10]
    assert ui.ids_seleccionados(registros, [5]) == []


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


def test_ui_organiza_la_correccion_en_subtabs_por_tabla() -> None:
    """CA-01: la UI construye las sub-pestañas a partir del catálogo de tablas."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "st.tabs(" in contenido
    assert "for definicion in TABLAS_CORRECCION" in contenido
    claves = {definicion.clave for definicion in TABLAS_CORRECCION}
    etiquetas = {definicion.etiqueta for definicion in TABLAS_CORRECCION}
    assert claves == set(CLAVES_TABLAS)
    assert etiquetas == set(ETIQUETAS_TABLAS)


def test_ui_usa_tabla_interactiva_con_seleccion_multiple() -> None:
    """CA-03: la tabla habilita la selección múltiple nativa de Streamlit."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert 'on_select="rerun"' in contenido
    assert 'selection_mode="multi-row"' in contenido
    assert "use_container_width=True" in contenido


def test_ui_no_renderiza_filtros_externos_masivos() -> None:
    """CA-02: la UI no levanta formularios de filtros por fuera de la tabla."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    for widget in ("st.text_input", "st.selectbox", "st.date_input", "st.multiselect"):
        assert widget not in contenido


def test_ui_expone_botones_de_accion_compactos() -> None:
    """CA-04: la UI ofrece los botones de cambio de estado y eliminación."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert ui.ETIQUETA_REACTIVAR in contenido
    assert ui.ETIQUETA_ANULAR in contenido
    assert ui.ETIQUETA_ELIMINAR in contenido
    assert "mutar_vigencia(" in contenido
    assert "eliminar_registros_tabla(" in contenido


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
