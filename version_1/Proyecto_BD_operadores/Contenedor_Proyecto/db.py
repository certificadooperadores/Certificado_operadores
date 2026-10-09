import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Leer credenciales de la BD (Docker las inyecta solas)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', '')

@st.cache_resource
def get_engine():
    """Retorna el motor de conexión a PostgreSQL"""
    engine_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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
