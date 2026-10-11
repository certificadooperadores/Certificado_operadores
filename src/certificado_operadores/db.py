"""Motor y utilidades de conexión a SQLite (capa de infraestructura).

Centraliza la creación del motor SQLAlchemy sobre la base local
(``operadores.db``), la aplicación de **pragmas de rendimiento** (``WAL``,
``busy_timeout`` y ``synchronous``) y la creación **idempotente** de los
índices estratégicos que aceleran las consultas más frecuentes (spec 025).

Las rutas no se queman: la base y los respaldos se resuelven a partir de la
ubicación del paquete y de variables de entorno configurables.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

# 1. Ruta absoluta a la base de datos local SQLite (en la raíz del proyecto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "operadores.db")

PRAGMAS_SQLITE: tuple[str, ...] = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout = 5000",
    "PRAGMA synchronous = NORMAL",
)
"""Pragmas de alto rendimiento aplicados a cada conexión SQLite (spec 025).

``journal_mode = WAL`` permite lecturas concurrentes sin bloquear escrituras,
``busy_timeout = 5000`` espera hasta 5 segundos ante concurrencia (en lugar de
fallar de inmediato con *database locked*) y ``synchronous = NORMAL`` reduce el
costo de cada ``commit`` conservando la durabilidad necesaria.
"""

INDICES_SQLITE: tuple[tuple[str, str, str], ...] = (
    ("idx_persona_cedula", "dim_persona", "id_persona"),
    ("idx_codigo_operador", "dim_codigo", "id_codigo, id_empresa, id_vigencia"),
    ("idx_codigo_persona", "dim_codigo", "id_persona"),
    ("idx_eventos_operador", "fact_eventos_operador", "id_codigo, id_tipo_evento, id_vigencia"),
    ("idx_eventos_fecha", "fact_eventos_operador", "fecha_certificado, fecha_retiro"),
    ("idx_comportamiento_codigo", "fact_comportamiento", "id_codigo, fecha_evento"),
    ("idx_reincidencia_codigo", "fact_reincidencia", "id_codigo, estado"),
)
"""Índices explícitos de alto impacto: ``(nombre, tabla, columnas)`` (spec 025).

Se crean con ``CREATE INDEX IF NOT EXISTS`` sobre los campos de búsqueda
frecuente: cédula del operador, cruce código/empresa/vigencia, eventos por
código/tipo y por fecha, comportamientos por código/fecha y reincidencias por
código/estado.

Nota: la spec 025 nombra las columnas ``fecha_inicio``/``fecha_fin`` y ``fecha``,
pero el modelo físico real de ``operadores.db`` usa ``fecha_certificado``/
``fecha_retiro`` en ``fact_eventos_operador`` y ``fecha_evento`` en
``fact_comportamiento``; se indexan esas columnas equivalentes para que el
índice sea aplicable.
"""


def configurar_pragmas(motor: Engine) -> None:
    """Aplica los pragmas de SQLite a cada conexión del motor indicado.

    Se apoya en el evento ``connect`` de SQLAlchemy para ejecutar los pragmas
    justo antes de que la conexión atienda la primera consulta, sin importar
    cuántas veces se abra o recicle la conexión.

    Args:
        motor: Motor SQLAlchemy sobre el que se registran los pragmas.
    """

    @event.listens_for(motor, "connect")
    def _aplicar_pragmas(conexion_dbapi: Any, _registro: Any) -> None:
        """Ejecuta los pragmas configurados sobre una conexión DBAPI nueva."""
        cursor = conexion_dbapi.cursor()
        try:
            for pragma in PRAGMAS_SQLITE:
                cursor.execute(pragma)
        finally:
            cursor.close()


def crear_indices(motor: Engine) -> None:
    """Crea de forma idempotente los índices estratégicos de la base.

    Solo crea el índice cuando su tabla y todas sus columnas existen, de modo
    que el motor pueda levantarse sobre una base aún sin cargar (ETL pendiente)
    o con un esquema parcial sin fallar.

    Args:
        motor: Motor SQLAlchemy sobre el que se crean los índices.
    """
    with motor.begin() as conexion:
        tablas = {
            fila[0]
            for fila in conexion.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }
        for nombre, tabla, columnas in INDICES_SQLITE:
            if tabla not in tablas:
                continue
            existentes = {fila[1] for fila in conexion.execute(text(f"PRAGMA table_info({tabla})"))}
            requeridas = {columna.strip() for columna in columnas.split(",")}
            if not requeridas.issubset(existentes):
                continue
            conexion.execute(text(f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla} ({columnas})"))


@st.cache_resource
def get_engine() -> Engine:
    """Retorna el motor de conexión a SQLite local con pragmas aplicados.

    Returns:
        El motor SQLAlchemy cacheado (una sola instancia por proceso) con los
        pragmas de rendimiento activos y los índices estratégicos garantizados
        cuando la base física ya existe.
    """
    engine_url = f"sqlite:///{DB_PATH}"
    engine = create_engine(engine_url)
    configurar_pragmas(engine)
    if os.path.exists(DB_PATH):
        crear_indices(engine)
    return engine


def get_connection():
    """Retorna una conexión activa para ejecutar SQL manual."""
    engine = get_engine()
    return engine.connect()


def run_query(query, params=None):
    """Ejecuta una consulta SELECT y retorna un DataFrame de Pandas."""
    engine = get_engine()
    try:
        if params:
            return pd.read_sql(text(query), engine, params=params)
        else:
            return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error ejecutando consulta: {e}")
        return pd.DataFrame()


def run_transaction(query, params=None):
    """Ejecuta comandos INSERT, UPDATE, DELETE (con Commit)"""
    engine = get_engine()
    try:
        with engine.begin() as conn:  # .begin() hace commit automático al terminar
            if params:
                conn.execute(text(query), params)
            else:
                conn.execute(text(query))
        return True, "Operación exitosa"
    except Exception as e:
        return False, str(e)


def registrar_auditoria(usuario, accion, detalles=None):
    """Registra un evento de auditoría en la tabla ``log_auditoria``."""
    query = "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:u, :a, :d)"
    run_transaction(query, {"u": usuario, "a": accion, "d": detalles})
