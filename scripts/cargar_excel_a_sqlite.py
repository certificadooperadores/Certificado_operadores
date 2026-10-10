import os
import pandas as pd
from sqlalchemy import create_engine, text
import bcrypt

# 1. Definir la ruta de la base de datos SQLite en la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "operadores.db")
engine_url = f"sqlite:///{DB_PATH}"
engine = create_engine(engine_url)

def cargar_csv(tabla_nombre, csv_path):
    """Lee un CSV y lo convierte en una tabla de SQLite"""
    if not os.path.exists(csv_path):
        print(f"[AVISO] Archivo no encontrado: {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path)
        # Regla de Negocio: Eliminar 'estado' de licencias para cálculo dinámico
        if tabla_nombre == "fact_licencias" and "estado" in df.columns:
            df = df.drop(columns=["estado"])
        if "usuario_registra" not in df.columns:
            df["usuario_registra"] = "sistema"
            
        # SQLite no maneja las fechas tan estricto, pero podemos asegurar que fecha_registro exista
        if "fecha_registro" not in df.columns:
            df["fecha_registro"] = pd.Timestamp.now()
            
        df.to_sql(tabla_nombre, engine, if_exists='replace', index=False)
        print(f"[OK] Tabla '{tabla_nombre}' cargada ({len(df)} registros).")
    except Exception as e:
        print(f"[ERROR] Error al cargar '{tabla_nombre}': {str(e)}")

def main():
    print(f"Iniciando carga de datos hacia SQLite: {DB_PATH}")
    
    # Insumos vigentes: los CSVs del modelo estrella viven en data/
    csv_dir = os.path.join(BASE_DIR, "data", "Modelo_Estrella_Final_CSVs")
    
    tablas = [
        ("dim_vigencia_registro", "dim_vigencia_registro.csv"),
        ("dim_empresa", "dim_empresa.csv"),
        ("dim_vehiculo", "dim_vehiculo.csv"),
        ("dim_tipo_evento", "dim_tipo_evento.csv"),
        ("dim_perfil_tipologia", "dim_perfil_tipologia.csv"),
        ("dim_persona", "dim_persona.csv"),
        ("dim_codigo", "dim_codigo.csv"),
        ("fact_licencias", "fact_licencias.csv"),
        ("fact_eventos_operador", "fact_eventos_operador.csv"),
        ("dim_impacto", "dim_impacto.csv"),
        ("dim_comportamiento", "dim_comportamiento.csv"),
        ("dim_detalle_comportamiento", "dim_detalle_comportamiento.csv"),
        ("fact_comportamiento", "fact_comportamiento.csv")
    ]
    
    for tabla_nombre, archivo_csv in tablas:
        csv_path = os.path.join(csv_dir, archivo_csv)
        cargar_csv(tabla_nombre, csv_path)
        
    print("Creando tablas de configuracion (Usuarios, Logs, Reincidencias)...")
    try:
        pwd = b"admin123"
        hashed = bcrypt.hashpw(pwd, bcrypt.gensalt()).decode('utf-8')
        
        # Sintaxis adaptada para SQLite
        sql_usuarios = f"""
        CREATE TABLE IF NOT EXISTS dim_usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL,
            estado TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        sql_logs = """
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            accion TEXT NOT NULL,
            detalles TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        sql_version = """
        CREATE TABLE IF NOT EXISTS dim_version_bd (
            id_version INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_backup TEXT,
            archivo_origen TEXT,
            fecha_restauracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            restaurado_por TEXT
        );
        """
        sql_reincidencia = """
        CREATE TABLE IF NOT EXISTS fact_reincidencia (
            id_reincidencia INTEGER PRIMARY KEY AUTOINCREMENT,
            id_impacto INTEGER,
            id_comportamiento INTEGER,
            id_codigo INTEGER, 
            fecha_inicio DATE, 
            fecha_fin DATE, 
            cantidad INTEGER,
            resumen TEXT, 
            determinacion_mc TEXT, 
            id_hecho_evento INTEGER, 
            estado TEXT DEFAULT 'Activo',
            usuario_registra TEXT, 
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        sql_reincidencia_det = """
        CREATE TABLE IF NOT EXISTS reincidencia_detalle (
            id_reincidencia INTEGER,
            id_hecho_comportamiento INTEGER,
            PRIMARY KEY (id_reincidencia, id_hecho_comportamiento)
        );
        """
        
        with engine.begin() as conn:
            conn.execute(text(sql_usuarios))
            conn.execute(text(sql_logs))
            conn.execute(text(sql_version))
            conn.execute(text(sql_reincidencia))
            conn.execute(text(sql_reincidencia_det))
            
            # Insertar admin por defecto si no existe
            conn.execute(text(f"""
                INSERT OR IGNORE INTO dim_usuarios (usuario, password_hash, rol, estado) 
                VALUES ('admin', '{hashed}', 'Super Administrador', 'Activo');
            """))
            
            # Insertar versión por defecto
            conn.execute(text("""
                INSERT INTO dim_version_bd (fecha_backup, archivo_origen, restaurado_por)
                SELECT 'N/A', 'BD Inicial - Carga desde CSV', 'sistema'
                WHERE NOT EXISTS (SELECT 1 FROM dim_version_bd);
            """))
            
        print("[OK] Tablas de configuracion creadas con exito.")
    except Exception as e:
        print(f"[ERROR] Error al crear tablas de configuracion: {e}")
        
    print("[FINALIZADO] Proceso finalizado. La base de datos SQLite 'operadores.db' esta lista.")

if __name__ == "__main__":
    main()
