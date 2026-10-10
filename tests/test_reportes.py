"""Pruebas de reportes y exportaciones (spec 010).

Cubren tres frentes: el repositorio ``ReportesRepository`` contra una base SQLite
temporal (catálogos de filtros y ejecución de un reporte consolidado), las
funciones puras (construcción de condiciones/consultas, descripción de
tipologías y generación de Excel/CSV) y las verificaciones estáticas de los
criterios de aceptación: el paquete existe, la UI y la página no contienen SQL y
la página usa ``render_reportes`` sin ``exec``. Todas las pruebas siguen el
patrón AAA (*Arrange · Act · Assert*).

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from certificado_operadores.domain.models import TIPO_EVENTO_CANCELACION
from certificado_operadores.infra.reportes_repository import (
    ACCION_EXPORTAR_REPORTE,
    OPCIONES_ESTADO,
    ReportesRepository,
    SeleccionFiltros,
    construir_consulta,
    construir_descripcion_tipologia,
    generar_csv,
    generar_excel,
)
from certificado_operadores.modulos.reportes import ui

_RUTA_UI = Path(ui.__file__).resolve()
_RUTA_REPOSITORIO = _RUTA_UI.parents[2] / "infra" / "reportes_repository.py"
_RUTA_PAGINA = _RUTA_UI.parents[2] / "pages" / "3_Reportes.py"

_COLUMNAS_UTRYT = (
    "METROCALI ID",
    "DOCUMENTTYPEID",
    "DOCUMENTNUMBER",
    "DRIVERNAME",
    "LASTNAME",
    "LASTNAME2",
    "STATEID",
    "TRANSPORTCONTRATISTID",
    "REGISTERDATE",
    "TIPOLOGY",
)

_IDS_REPORTES = (
    "utryt",
    "operadores_empresa",
    "licencias_vencer",
    "eventos_tipo",
    "reincidencias",
    "comportamientos_operador",
    "certificados_vencer",
    "certificados_vencidos",
)

# Fechas relativas al día de ejecución para que los reportes de vencimiento sean
# deterministas: una licencia vigente, un certificado por vencer y uno vencido.
_HOY = date.today()
_VENCIMIENTO_LICENCIA = (_HOY + timedelta(days=365)).isoformat()
_CERTIFICADO_POR_VENCER = (_HOY - timedelta(days=365 * 3 - 30)).isoformat()
_CERTIFICADO_VENCIDO = (_HOY - timedelta(days=365 * 3 + 10)).isoformat()

# --- Esquema mínimo para las pruebas del repositorio ------------------------
_ESQUEMA = (
    """
    CREATE TABLE dim_empresa (
        id_empresa INTEGER PRIMARY KEY,
        nombre_empresa TEXT
    );
    """,
    """
    CREATE TABLE dim_perfil_tipologia (
        id_perfil_tipologia INTEGER PRIMARY KEY,
        autoriza_articulado INTEGER,
        autoriza_padron INTEGER,
        autoriza_complementario INTEGER,
        autoriza_auxiliar INTEGER
    );
    """,
    """
    CREATE TABLE dim_persona (
        id_persona INTEGER PRIMARY KEY,
        nombres TEXT,
        primer_apellido TEXT,
        segundo_apellido TEXT
    );
    """,
    """
    CREATE TABLE dim_codigo (
        id_codigo INTEGER PRIMARY KEY,
        id_persona INTEGER,
        id_vigencia INTEGER,
        id_empresa INTEGER,
        id_perfil_tipologia INTEGER,
        fecha_registro TEXT
    );
    """,
    """
    CREATE TABLE dim_tipo_evento (
        id_tipo_evento INTEGER PRIMARY KEY,
        nombre_evento TEXT
    );
    """,
    """
    CREATE TABLE dim_impacto (
        id_impacto INTEGER PRIMARY KEY,
        impacto TEXT
    );
    """,
    """
    CREATE TABLE dim_comportamiento (
        id_comportamiento INTEGER PRIMARY KEY,
        comportamiento TEXT
    );
    """,
    """
    CREATE TABLE fact_eventos_operador (
        id_hecho_evento INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        id_tipo_evento INTEGER,
        fecha_certificado TEXT,
        fecha_retiro TEXT,
        fecha_suspension TEXT,
        fecha_observacion TEXT,
        fecha_registro TEXT,
        observacion TEXT
    );
    """,
    """
    CREATE TABLE fact_licencias (
        id_hecho_licencia INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        tipo TEXT,
        vencimiento TEXT
    );
    """,
    """
    CREATE TABLE fact_comportamiento (
        id_hecho_comportamiento INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        id_jerarquia INTEGER,
        caso_bitacora_ticket TEXT,
        fecha_evento TEXT,
        vehiculo TEXT,
        ruta TEXT
    );
    """,
    """
    CREATE TABLE dim_detalle_comportamiento (
        id_jerarquia INTEGER PRIMARY KEY,
        descripcion_comportamiento TEXT
    );
    """,
    """
    CREATE TABLE fact_reincidencia (
        id_reincidencia INTEGER PRIMARY KEY,
        id_codigo INTEGER,
        id_impacto INTEGER,
        id_comportamiento INTEGER,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        determinacion_mc TEXT
    );
    """,
    """
    CREATE TABLE log_auditoria (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        accion TEXT NOT NULL,
        detalles TEXT
    );
    """,
)


def _crear_esquema(motor: Engine) -> None:
    """Crea las tablas mínimas de la vista de reportes.

    Args:
        motor: Motor SQLAlchemy donde se crea el esquema.
    """
    with motor.begin() as conexion:
        for sentencia in _ESQUEMA:
            conexion.execute(text(sentencia))


def _sembrar(motor: Engine) -> None:
    """Inserta catálogos y datos de ejemplo para las pruebas.

    Args:
        motor: Motor SQLAlchemy con el esquema ya creado.
    """
    with motor.begin() as conexion:
        conexion.execute(
            text("INSERT INTO dim_empresa VALUES (:id, :nombre)"),
            [{"id": 1, "nombre": "Empresa A"}, {"id": 2, "nombre": "Empresa B"}],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_perfil_tipologia (id_perfil_tipologia, "
                "autoriza_articulado, autoriza_padron, autoriza_complementario, "
                "autoriza_auxiliar) VALUES (:id, :art, :pad, :comp, :aux)"
            ),
            [
                {"id": 1, "art": 1, "pad": 1, "comp": 0, "aux": 0},
                {"id": 2, "art": 0, "pad": 0, "comp": 0, "aux": 0},
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_persona (id_persona, nombres, primer_apellido, "
                "segundo_apellido) VALUES (:id, :nombres, :apellido, :segundo)"
            ),
            [
                {"id": 9001, "nombres": "Ana", "apellido": "Pérez", "segundo": "Gómez"},
                {"id": 9002, "nombres": "Luis", "apellido": "Rojas", "segundo": "Díaz"},
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_codigo (id_codigo, id_persona, id_vigencia, "
                "id_empresa, id_perfil_tipologia, fecha_registro) "
                "VALUES (:id, :persona, 1, :empresa, :tipologia, '2026-01-01')"
            ),
            [
                {"id": 2001, "persona": 9001, "empresa": 1, "tipologia": 1},
                {"id": 2002, "persona": 9002, "empresa": 2, "tipologia": 2},
                {"id": 2003, "persona": 9001, "empresa": 1, "tipologia": 1},
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_tipo_evento VALUES (:id, :nombre)"),
            [
                {"id": 1, "nombre": "Certificación"},
                {"id": 7, "nombre": "Cancelación"},
            ],
        )
        conexion.execute(
            text("INSERT INTO dim_impacto VALUES (:id, :impacto)"),
            [{"id": 1, "impacto": "Grave"}, {"id": 2, "impacto": "Leve"}],
        )
        conexion.execute(
            text("INSERT INTO dim_comportamiento VALUES (:id, :nombre)"),
            [{"id": 10, "nombre": "Conducción temeraria"}],
        )
        conexion.execute(
            text(
                "INSERT INTO dim_detalle_comportamiento "
                "(id_jerarquia, descripcion_comportamiento) VALUES (:id, :desc)"
            ),
            [{"id": 10, "desc": "Conducción temeraria"}],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_licencias (id_hecho_licencia, id_codigo, tipo, "
                "vencimiento) VALUES (:id, :cod, :tipo, :venc)"
            ),
            [{"id": 1, "cod": 2001, "tipo": "C3", "venc": _VENCIMIENTO_LICENCIA}],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_comportamiento (id_hecho_comportamiento, id_codigo, "
                "id_jerarquia, caso_bitacora_ticket, fecha_evento, vehiculo, ruta) "
                "VALUES (:id, :cod, :jer, :caso, :fecha, :veh, :ruta)"
            ),
            [
                {
                    "id": 1,
                    "cod": 2001,
                    "jer": 10,
                    "caso": "TKT-001",
                    "fecha": "2026-01-05",
                    "veh": "ABC123",
                    "ruta": "R1",
                }
            ],
        )
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador (id_hecho_evento, id_codigo, "
                "id_tipo_evento, fecha_certificado, fecha_retiro, fecha_suspension, "
                "fecha_observacion, fecha_registro, observacion) VALUES "
                "(:id, :cod, :tipo, :cert, NULL, NULL, NULL, :registro, :obs)"
            ),
            [
                {
                    "id": 101,
                    "cod": 2001,
                    "tipo": 1,
                    "cert": _CERTIFICADO_POR_VENCER,
                    "registro": _CERTIFICADO_POR_VENCER,
                    "obs": "Certificación por vencer",
                },
                {
                    "id": 102,
                    "cod": 2002,
                    "tipo": 1,
                    "cert": _CERTIFICADO_VENCIDO,
                    "registro": _CERTIFICADO_VENCIDO,
                    "obs": "Certificación vencida",
                },
            ],
        )
        conexion.execute(
            text("INSERT INTO fact_reincidencia VALUES (:id, :cod, :imp, :comp, :fi, :ff, :det)"),
            [
                {
                    "id": 1,
                    "cod": 2001,
                    "imp": 1,
                    "comp": 10,
                    "fi": "2026-01-01",
                    "ff": "2026-01-02",
                    "det": "advertencia",
                }
            ],
        )


@pytest.fixture
def motor_sqlite(tmp_path: Path) -> Iterator[Engine]:
    """Motor SQLite temporal con esquema y datos de ejemplo."""
    motor = create_engine(f"sqlite:///{tmp_path / 'prueba_reportes.db'}", poolclass=NullPool)
    _crear_esquema(motor)
    _sembrar(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def repositorio(motor_sqlite: Engine) -> ReportesRepository:
    """Repositorio de reportes configurado con el motor SQLite de prueba."""
    return ReportesRepository(engine=motor_sqlite)


def _filas(motor: Engine, sentencia: str) -> list[tuple]:
    """Ejecuta una consulta de lectura y devuelve las filas como tuplas."""
    with motor.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(sentencia)).all()]


# --- RF-01: catálogos de filtros ---------------------------------------------
def test_listar_reportes(repositorio: ReportesRepository) -> None:
    """RF-01: los ocho reportes se exponen en orden con sus metadatos."""
    # Arrange / Act
    definiciones = repositorio.listar_reportes()

    # Assert
    assert tuple(definicion.id for definicion in definiciones) == _IDS_REPORTES
    assert all(definicion.nombre for definicion in definiciones)


def test_utryt_conserva_columnas(repositorio: ReportesRepository) -> None:
    """No-objetivo: el formato UTRYT no altera sus columnas requeridas."""
    # Arrange / Act
    definicion = next(d for d in repositorio.listar_reportes() if d.id == "utryt")

    # Assert
    assert definicion.columnas == _COLUMNAS_UTRYT


def test_listar_reportes_no_expone_la_consulta(repositorio: ReportesRepository) -> None:
    """RNF-01: las definiciones públicas no cargan sentencias SQL."""
    # Arrange / Act
    definicion = repositorio.listar_reportes()[0]

    # Assert
    assert not hasattr(definicion, "consulta")


def test_listar_empresas(repositorio: ReportesRepository) -> None:
    """RF-01: las empresas se listan ordenadas por identificador."""
    # Arrange / Act
    empresas = repositorio.listar_empresas()

    # Assert
    assert [(empresa.id_empresa, empresa.nombre_empresa) for empresa in empresas] == [
        (1, "Empresa A"),
        (2, "Empresa B"),
    ]


def test_listar_tipologias(repositorio: ReportesRepository) -> None:
    """RF-01: las tipologías se describen según sus autorizaciones."""
    # Arrange / Act
    tipologias = repositorio.listar_tipologias()

    # Assert
    assert [(tipologia.id_perfil_tipologia, tipologia.descripcion) for tipologia in tipologias] == [
        (1, "1 - Articulado, Padron"),
        (2, "2"),
    ]


def test_listar_estados(repositorio: ReportesRepository) -> None:
    """RF-01: las opciones de estado son las etiquetas esperadas."""
    # Arrange / Act / Assert
    assert repositorio.listar_estados() == list(OPCIONES_ESTADO)


def test_listar_tipos_evento(repositorio: ReportesRepository) -> None:
    """RF-01: los tipos de evento se listan en orden."""
    # Arrange / Act
    tipos = repositorio.listar_tipos_evento()

    # Assert
    assert [tipo.id_tipo_evento for tipo in tipos] == [1, 7]


def test_listar_impactos(repositorio: ReportesRepository) -> None:
    """RF-01: los impactos se listan en orden."""
    # Arrange / Act
    impactos = repositorio.listar_impactos()

    # Assert
    assert [impacto.impacto for impacto in impactos] == ["Grave", "Leve"]


def test_construir_descripcion_tipologia() -> None:
    """Las autorizaciones se traducen a la descripción legible."""
    # Arrange / Act / Assert
    assert (
        construir_descripcion_tipologia(1, True, False, True, False)
        == "1 - Articulado, Complementario"
    )
    assert construir_descripcion_tipologia(2, False, False, False, False) == "2"


# --- RF-02: condiciones y consultas de reportes ------------------------------
def test_construir_condiciones_utryt(repositorio: ReportesRepository) -> None:
    """RF-02: empresa, estado y tipología se traducen a condiciones enlazadas."""
    # Arrange
    seleccion = SeleccionFiltros(empresa=1, estado="Vigente", tipologia=2)

    # Act
    condiciones, parametros = repositorio.construir_condiciones("utryt", seleccion)

    # Assert
    assert condiciones == [
        "dc.id_empresa = :emp",
        "dc.id_vigencia = :est",
        "dc.id_perfil_tipologia = :tip",
    ]
    assert parametros == {"emp": 1, "est": 1, "tip": 2}


def test_construir_condiciones_sin_filtros(repositorio: ReportesRepository) -> None:
    """RF-02: sin selección no se agregan condiciones ni parámetros."""
    # Arrange / Act
    condiciones, parametros = repositorio.construir_condiciones(
        "certificados_vencidos", SeleccionFiltros()
    )

    # Assert
    assert condiciones == []
    assert parametros == {}


def test_construir_condiciones_estado_activo(repositorio: ReportesRepository) -> None:
    """RF-02: la actividad usa la subconsulta de cancelación parametrizada."""
    # Arrange / Act
    activos, params_activos = repositorio.construir_condiciones(
        "operadores_empresa", SeleccionFiltros(estado_activo="Activos")
    )
    cancelados, _ = repositorio.construir_condiciones(
        "operadores_empresa", SeleccionFiltros(estado_activo="Cancelados")
    )

    # Assert
    assert activos == [
        "dc.id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador "
        "WHERE id_tipo_evento = :cancelacion)"
    ]
    assert params_activos["cancelacion"] == TIPO_EVENTO_CANCELACION
    assert "IN (" in cancelados[0]
    assert "NOT IN (" not in cancelados[0]


def test_construir_condiciones_dias_vencer(repositorio: ReportesRepository) -> None:
    """RF-02: la ventana de vencimiento usa un parámetro enlazado."""
    # Arrange / Act
    condiciones, parametros = repositorio.construir_condiciones(
        "licencias_vencer", SeleccionFiltros(dias_vencer=30)
    )

    # Assert
    assert condiciones == [
        "DATE(l.vencimiento) BETWEEN DATE('now') AND DATE('now', '+' || :dias || ' days')"
    ]
    assert parametros == {"dias": 30}


def test_construir_condiciones_fecha_y_tipo(repositorio: ReportesRepository) -> None:
    """RF-02: el rango de fechas y el tipo de evento se enlazan como parámetros."""
    # Arrange
    seleccion = SeleccionFiltros(
        fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31), tipo_evento=1
    )

    # Act
    condiciones, parametros = repositorio.construir_condiciones("eventos_tipo", seleccion)

    # Assert
    assert condiciones[0].endswith("BETWEEN :fdesde AND :fhasta")
    assert parametros["fdesde"] == "2026-01-01"
    assert parametros["fhasta"] == "2026-01-31"
    assert parametros["tev"] == 1


def test_construir_condiciones_codigo_e_impacto(repositorio: ReportesRepository) -> None:
    """RF-02: el código de operador y el impacto se enlazan como parámetros."""
    # Arrange / Act
    cond_codigo, params_codigo = repositorio.construir_condiciones(
        "comportamientos_operador",
        SeleccionFiltros(codigo=2001, fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 2, 1)),
    )
    cond_impacto, params_impacto = repositorio.construir_condiciones(
        "reincidencias", SeleccionFiltros(impacto=2)
    )

    # Assert
    assert "f.id_codigo = :cod" in cond_codigo
    assert params_codigo["cod"] == 2001
    assert cond_impacto == ["r.id_impacto = :imp"]
    assert params_impacto == {"imp": 2}


def test_construir_condiciones_reporte_desconocido(repositorio: ReportesRepository) -> None:
    """RF-02: un identificador inexistente es un error explícito."""
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        repositorio.construir_condiciones("no_existe", SeleccionFiltros())


def test_construir_consulta() -> None:
    """La consulta base recibe las condiciones con AND."""
    # Arrange
    base = "SELECT 1 WHERE 1=1"

    # Act / Assert
    assert construir_consulta(base, []) == base
    assert construir_consulta(base, ["a = :x", "b = :y"]) == (
        "SELECT 1 WHERE 1=1 AND a = :x AND b = :y"
    )


def test_ejecutar_reporte_operadores_empresa(repositorio: ReportesRepository) -> None:
    """RF-02: se ejecuta el reporte y se filtran las filas por empresa."""
    # Arrange / Act
    resultado = repositorio.ejecutar_reporte("operadores_empresa", SeleccionFiltros(empresa=1))

    # Assert
    assert list(resultado.columns) == ["Empresa", "Tipologia", "Codigos"]
    assert resultado.to_dict(orient="records") == [
        {"Empresa": "Empresa A", "Tipologia": 1, "Codigos": 2}
    ]


def test_ejecutar_reporte_estado_activo(
    repositorio: ReportesRepository, motor_sqlite: Engine
) -> None:
    """RF-02/CA-03: el filtro de actividad usa la subconsulta del repositorio."""
    # Arrange
    with motor_sqlite.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO fact_eventos_operador (id_hecho_evento, id_codigo, "
                "id_tipo_evento) VALUES (1, 2001, 7)"
            )
        )

    # Act
    activos = repositorio.ejecutar_reporte(
        "operadores_empresa", SeleccionFiltros(estado_activo="Activos")
    )
    cancelados = repositorio.ejecutar_reporte(
        "operadores_empresa", SeleccionFiltros(estado_activo="Cancelados")
    )

    # Assert
    assert int(activos["Codigos"].sum()) == 2
    assert cancelados["Codigos"].tolist() == [1]


def test_ejecutar_reporte_reincidencias(repositorio: ReportesRepository) -> None:
    """RF-02: el reporte de reincidencias devuelve los casos guardados."""
    # Arrange / Act
    resultado = repositorio.ejecutar_reporte("reincidencias", SeleccionFiltros())

    # Assert
    assert resultado["Reincidencia"].tolist() == [1]
    assert resultado["Determinacion"].tolist() == ["advertencia"]


@pytest.mark.parametrize("id_reporte", _IDS_REPORTES)
def test_ejecutar_los_ocho_reportes(repositorio: ReportesRepository, id_reporte: str) -> None:
    """S-03/CA-02/CA-03: los ocho reportes se ejecutan sin errores en SQLite."""
    # Arrange
    definicion = next(d for d in repositorio.listar_reportes() if d.id == id_reporte)

    # Act
    resultado = repositorio.ejecutar_reporte(id_reporte, SeleccionFiltros())

    # Assert
    assert isinstance(resultado, pd.DataFrame)
    assert list(resultado.columns) == list(definicion.columnas)


def test_ejecutar_reporte_licencias_vencer(repositorio: ReportesRepository) -> None:
    """CA-02: el reporte de licencias por vencer calcula los días restantes."""
    # Arrange / Act
    resultado = repositorio.ejecutar_reporte("licencias_vencer", SeleccionFiltros())

    # Assert
    assert resultado["Codigo"].tolist() == [2001]
    assert resultado["Vencimiento"].tolist() == [_VENCIMIENTO_LICENCIA]
    assert resultado["Dias Restantes"].tolist()[0] > 0


def test_ejecutar_reporte_certificados_vencer(repositorio: ReportesRepository) -> None:
    """CA-02: el último certificado por código alimenta el reporte por vencer."""
    # Arrange
    seleccion = SeleccionFiltros(dias_vencer=90)

    # Act
    resultado = repositorio.ejecutar_reporte("certificados_vencer", seleccion)

    # Assert
    assert resultado["Codigo"].tolist() == [2001]
    assert 0 < resultado["Dias Restantes"].tolist()[0] <= 90


def test_ejecutar_reporte_certificados_vencidos(repositorio: ReportesRepository) -> None:
    """CA-02: los certificados con vigencia cumplida se listan como vencidos."""
    # Arrange / Act
    resultado = repositorio.ejecutar_reporte("certificados_vencidos", SeleccionFiltros())

    # Assert
    assert resultado["Codigo"].tolist() == [2002]
    assert resultado["Dias Vencido"].tolist()[0] > 0


# --- RF-03: exportaciones y auditoría ----------------------------------------
def test_generar_excel_y_csv() -> None:
    """RF-03: se generan archivos Excel y CSV válidos en memoria."""
    # Arrange
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    # Act
    excel = generar_excel(df, "Reporte de prueba")
    csv = generar_csv(df)

    # Assert
    assert excel[:2] == b"PK"
    libro = pd.ExcelFile(io.BytesIO(excel))
    assert "Resumen" in libro.sheet_names
    assert csv.decode("utf-8-sig").splitlines()[0] == "a,b"


def test_registrar_exportacion_audita(
    repositorio: ReportesRepository, motor_sqlite: Engine
) -> None:
    """RF-03/CA-03: la exportación deja su registro de auditoría."""
    # Act
    repositorio.registrar_exportacion("admin", "Consolidado UTRYT", 3)

    # Assert
    assert _filas(motor_sqlite, "SELECT usuario, accion, detalles FROM log_auditoria") == [
        ("admin", ACCION_EXPORTAR_REPORTE, "Consolidado UTRYT - 3 registros")
    ]


# --- Criterios de aceptación verificables ------------------------------------
def test_paquete_reportes_existe() -> None:
    """CA-01: el paquete existe y expone ``render_reportes``."""
    # Arrange / Act
    from certificado_operadores.modulos.reportes import render_reportes

    # Assert
    assert callable(render_reportes)


def test_ui_no_contiene_sql_ni_acceso_directo() -> None:
    """RNF-01: la UI no contiene SQL ni acceso directo a la base de datos."""
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


def test_repositorio_encapsula_la_sql() -> None:
    """CA-03: las consultas de reportes viven en el repositorio de infraestructura."""
    # Arrange
    contenido = _RUTA_REPOSITORIO.read_text(encoding="utf-8").upper()

    # Act / Assert
    assert "SELECT" in contenido
    assert "INSERT INTO LOG_AUDITORIA" in contenido


def test_repositorio_sin_sintaxis_postgres() -> None:
    """CA-01: el repositorio no conserva tokens nativos de PostgreSQL."""
    # Arrange
    contenido = _RUTA_REPOSITORIO.read_text(encoding="utf-8").upper()

    # Act / Assert
    assert "::" not in contenido
    assert "INTERVAL" not in contenido
    assert "DISTINCT ON" not in contenido


def test_pagina_usa_render_reportes_sin_exec() -> None:
    """RNF-02/CA-02: la página importa la función y ya no usa ``exec``."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    assert "render_reportes" in contenido
    assert "10_Reportes" not in contenido
    assert "exec(" not in contenido
    assert "run_query" not in contenido
    assert "run_transaction" not in contenido


def test_pagina_compila_sin_errores_de_sintaxis() -> None:
    """RNF-02/CA-02: el archivo de la página es sintácticamente válido."""
    # Arrange
    contenido = _RUTA_PAGINA.read_text(encoding="utf-8")

    # Act / Assert
    compile(contenido, str(_RUTA_PAGINA), "exec")


# --- Spec 023: toolbar horizontal, KPIs y gráfico liviano --------------------
def test_construir_agregacion_usa_la_columna_total() -> None:
    """La agregación prefiere la columna de totales cuando existe."""
    # Arrange
    df = pd.DataFrame({"Empresa": ["A", "B", "A"], "Tipologia": [1, 2, 1], "Codigos": [2, 5, 3]})

    # Act
    agregacion = ui.construir_agregacion(df)

    # Assert
    assert list(agregacion.columns) == [ui.COLUMNA_CATEGORIA, ui.COLUMNA_VALOR]
    assert set(zip(agregacion["Categoria"], agregacion["Total"], strict=True)) == {
        ("A", 5),
        ("B", 5),
    }


def test_construir_agregacion_cuenta_ocurrencias_sin_numericas() -> None:
    """Sin columnas numéricas la agregación cuenta las ocurrencias."""
    # Arrange
    df = pd.DataFrame({"Empresa": ["A", "A", "B"]})

    # Act
    agregacion = ui.construir_agregacion(df)

    # Assert
    assert set(zip(agregacion["Categoria"], agregacion["Total"], strict=True)) == {
        ("A", 2),
        ("B", 1),
    }


def test_construir_agregacion_vacia() -> None:
    """Un resultado vacío produce una agregación vacía."""
    # Arrange / Act
    agregacion = ui.construir_agregacion(pd.DataFrame())

    # Assert
    assert agregacion.empty


def test_construir_agregacion_respeta_el_limite() -> None:
    """La agregación se recorta al número máximo de categorías."""
    # Arrange
    df = pd.DataFrame({"Empresa": [f"E{indice}" for indice in range(30)], "Total": [1] * 30})

    # Act
    agregacion = ui.construir_agregacion(df, limite=5)

    # Assert
    assert len(agregacion) == 5


def test_pesos_toolbar_reparto_de_referencia() -> None:
    """El toolbar usa el reparto de referencia cuando hay cuatro filtros."""
    # Arrange / Act / Assert
    assert ui.pesos_toolbar(4) == [2, 2, 1.5, 2, 1]
    assert ui.pesos_toolbar(1) == [2.0, 1.0]


def test_ui_reportes_usa_toolbar_kpis_y_grafico() -> None:
    """CA-06: la vista agrupa filtros en columnas y muestra KPIs y gráfico."""
    # Arrange
    contenido = _RUTA_UI.read_text(encoding="utf-8")

    # Act / Assert
    assert "st.columns(" in contenido
    assert "st.metric(" in contenido
    assert "st.bar_chart(" in contenido
    assert "horizontal=True" in contenido


def test_titulo_reportes_sin_emojis() -> None:
    """CA-03: el título de reportes no contiene emojis informales."""
    # Arrange / Act / Assert
    assert ui.TITULO.isascii()
