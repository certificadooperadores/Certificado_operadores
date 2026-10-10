import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Ruta absoluta a la base de datos local SQLite (en la raíz del proyecto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "operadores.db")

@st.cache_resource
def get_engine():
    """Retorna el motor de conexión a SQLite local"""
    engine_url = f"sqlite:///{DB_PATH}"
    return create_engine(engine_url)

def get_connection():
    """Retorna una conexión activa para ejecutar SQL manual"""
    engine = get_engine()
    return engine.connect()

def run_query(query, params=None):
    """Ejecuta una consulta SELECT y retorna un DataFrame de Pandas"""
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
        with engine.begin() as conn: # .begin() hace commit automático al terminar
            if params:
                conn.execute(text(query), params)
            else:
                conn.execute(text(query))
        return True, "Operación exitosa"
    except Exception as e:
        return False, str(e)

def registrar_auditoria(usuario, accion, detalles=None):
    query = "INSERT INTO log_auditoria (usuario, accion, detalles) VALUES (:u, :a, :d)"
    run_transaction(query, {"u": usuario, "a": accion, "d": detalles})
