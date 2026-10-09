import os
import pandas as pd
from sqlalchemy import create_engine, text
import time

# 1. Leer las credenciales (Docker le pasará estos valores automáticamente)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', '')

# 2. Conectar a PostgreSQL
engine_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(engine_url)

def esperar_db(max_retries=10, wait_time=5):
    """Pausa inteligente: Espera a que PostgreSQL esté encendido antes de empezar"""
    print("⏳ Intentando conectar a la Base de Datos...")
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Conexión establecida con éxito.")
            return True
        except Exception as e:
            time.sleep(wait_time)
    
    print("❌ No se pudo conectar a la base de datos.")
    return False

def cargar_csv(tabla_nombre, csv_path):
    """Lee un CSV y lo convierte en una tabla de SQL"""
    if not os.path.exists(csv_path):
        print(f"⚠️ Archivo no encontrado: {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path)
        # 💡 Regla de Negocio: Eliminar 'estado' de licencias para cálculo dinámico
        if tabla_nombre == "fact_licencias" and "estado" in df.columns:
            df = df.drop(columns=["estado"])
        if "usuario_registra" not in df.columns:
            df["usuario_registra"] = "sistema"
        df.to_sql(tabla_nombre, engine, if_exists='replace', index=False)
        print(f"✅ Tabla '{tabla_nombre}' cargada ({len(df)} registros).")
    except Exception as e:
        print(f"❌ Error al cargar '{tabla_nombre}': {str(e)}")

def crear_relaciones():
    print("⏳ Creando Llaves Primarias y Foráneas...")
    sql_commands = [
        # --- LLAVES PRIMARIAS (DIMENSIONES) ---
        "ALTER TABLE dim_vigencia_registro ADD PRIMARY KEY (id_vigencia);",
        "ALTER TABLE dim_empresa ADD PRIMARY KEY (id_empresa);",
        "ALTER TABLE dim_vehiculo ADD PRIMARY KEY (id_vehiculo);",
        "ALTER TABLE dim_tipo_evento ADD PRIMARY KEY (id_tipo_evento);",
        "ALTER TABLE dim_perfil_tipologia ADD PRIMARY KEY (id_perfil_tipologia);",
        "ALTER TABLE dim_persona ADD PRIMARY KEY (id_persona);",
        "ALTER TABLE dim_codigo ADD PRIMARY KEY (id_codigo);",
        
        # --- LLAVES PRIMARIAS (HECHOS) ---
        "ALTER TABLE fact_licencias ADD PRIMARY KEY (id_hecho_licencia);",
        "ALTER TABLE fact_eventos_operador ADD PRIMARY KEY (id_hecho_evento);",

        # --- LLAVES PRIMARIAS (COMPORTAMIENTO) ---
        "ALTER TABLE dim_impacto ADD PRIMARY KEY (id_impacto);",
        "ALTER TABLE dim_comportamiento ADD PRIMARY KEY (id_comportamiento);",
        "ALTER TABLE dim_detalle_comportamiento ADD PRIMARY KEY (id_jerarquia);",
        "ALTER TABLE fact_comportamiento ADD PRIMARY KEY (id_hecho_comportamiento);",

        # --- LLAVES FORÁNEAS (RELACIONES DEL MODELO ESTRELLA) ---
        "ALTER TABLE dim_codigo ADD CONSTRAINT fk_persona FOREIGN KEY (id_persona) REFERENCES dim_persona(id_persona);",
        "ALTER TABLE dim_codigo ADD CONSTRAINT fk_empresa FOREIGN KEY (id_empresa) REFERENCES dim_empresa(id_empresa);",
        "ALTER TABLE dim_codigo ADD CONSTRAINT fk_perfil FOREIGN KEY (id_perfil_tipologia) REFERENCES dim_perfil_tipologia(id_perfil_tipologia);",
        "ALTER TABLE fact_licencias ADD CONSTRAINT fk_codigo_lic FOREIGN KEY (id_codigo) REFERENCES dim_codigo(id_codigo);",
        "ALTER TABLE fact_eventos_operador ADD CONSTRAINT fk_codigo_evt FOREIGN KEY (id_codigo) REFERENCES dim_codigo(id_codigo);",
        "ALTER TABLE fact_eventos_operador ADD CONSTRAINT fk_tipo_evt FOREIGN KEY (id_tipo_evento) REFERENCES dim_tipo_evento(id_tipo_evento);",
        
        # --- EL ARREGLO DE LOS VEHICULOS QUE NOTASTE ---
        "ALTER TABLE fact_eventos_operador ALTER COLUMN id_vehiculo_evaluado TYPE BIGINT USING id_vehiculo_evaluado::bigint;",
        "ALTER TABLE fact_eventos_operador ADD CONSTRAINT fk_vehiculo_evt FOREIGN KEY (id_vehiculo_evaluado) REFERENCES dim_vehiculo(id_vehiculo);",
        
        # --- RELACIONES DEL MODELO DE COMPORTAMIENTO ---
        "ALTER TABLE dim_comportamiento ADD CONSTRAINT fk_comp_impacto FOREIGN KEY (id_impacto) REFERENCES dim_impacto(id_impacto);",
        "ALTER TABLE dim_detalle_comportamiento ADD CONSTRAINT fk_det_comp FOREIGN KEY (id_comportamiento) REFERENCES dim_comportamiento(id_comportamiento);",
        "ALTER TABLE fact_comportamiento ALTER COLUMN id_codigo TYPE BIGINT USING id_codigo::bigint;",
        "UPDATE fact_comportamiento SET id_codigo = NULL WHERE id_codigo NOT IN (SELECT id_codigo FROM dim_codigo);",
        "ALTER TABLE fact_comportamiento ADD CONSTRAINT fk_fact_jerarquia FOREIGN KEY (id_jerarquia) REFERENCES dim_detalle_comportamiento(id_jerarquia);",
        "ALTER TABLE fact_comportamiento ADD CONSTRAINT fk_fact_codigo FOREIGN KEY (id_codigo) REFERENCES dim_codigo(id_codigo);",
        
        # --- RELACIONES DE VIGENCIA ---
        "ALTER TABLE dim_codigo ADD CONSTRAINT fk_vig_codigo FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);",
        "ALTER TABLE dim_empresa ADD CONSTRAINT fk_vig_empresa FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);",
        "ALTER TABLE dim_perfil_tipologia ADD CONSTRAINT fk_vig_perfil FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);",
        "ALTER TABLE dim_persona ADD CONSTRAINT fk_vig_persona FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);",
        "ALTER TABLE dim_tipo_evento ADD CONSTRAINT fk_vig_evento FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);",
        "ALTER TABLE fact_licencias ADD CONSTRAINT fk_vig_lic FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);",
        "ALTER TABLE fact_eventos_operador ADD CONSTRAINT fk_vig_fact_evt FOREIGN KEY (id_vigencia) REFERENCES dim_vigencia_registro(id_vigencia);"
    ]

    try:
        with engine.begin() as conn:  
            for cmd in sql_commands:
                conn.execute(text(cmd))
                
            # Establecer DEFAULT CURRENT_TIMESTAMP a la columna fecha_registro y usuario_registra
            tablas_a_modificar = [
                "dim_codigo", "dim_empresa", "dim_perfil_tipologia", 
                "dim_persona", "dim_tipo_evento", "dim_vehiculo", 
                "dim_vigencia_registro", "fact_eventos_operador", "fact_licencias",
                "dim_impacto", "dim_comportamiento", "dim_detalle_comportamiento",
                "fact_comportamiento"
            ]
            for t in tablas_a_modificar:
                try:
                    conn.execute(text(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
                    conn.execute(text(f"ALTER TABLE {t} ALTER COLUMN fecha_registro SET DEFAULT CURRENT_TIMESTAMP;"))
                except Exception as ex_col:
                    pass
                try:
                    conn.execute(text(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS usuario_registra VARCHAR(50) DEFAULT 'sistema';"))
                except Exception as ex_col:
                    pass
            # Columnas extra para fact_eventos_operador (eventos de observación/advertencia/condicionamiento)
            try:
                conn.execute(text("ALTER TABLE fact_eventos_operador ADD COLUMN IF NOT EXISTS fecha_observacion text;"))
            except Exception as ex_col:
                pass
            # Corregir tipo de jerarquia_4 (pandas la infiere como numeric cuando viene vacía)
            try:
                conn.execute(text("ALTER TABLE dim_detalle_comportamiento ALTER COLUMN jerarquia_4 TYPE text USING jerarquia_4::text;"))
            except Exception as ex_col:
                pass
                    
        print("✅ Relaciones, restricciones de integridad y defaults creados con éxito.")
    except Exception as e:
        print(f"❌ Error al crear relaciones: {e}")

def main():
    print("Iniciando carga de datos...")
    if not esperar_db():
        return
        
    csv_dir = "/Modelo_Estrella_Final_CSVs" 
    
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
        
    crear_relaciones()
    
    print("⏳ Creando tabla dim_usuarios...")
    try:
        import bcrypt
        pwd = b"admin123"
        hashed = bcrypt.hashpw(pwd, bcrypt.gensalt()).decode('utf-8')
        
        sql_usuarios = f"""
        CREATE TABLE IF NOT EXISTS dim_usuarios (
            id_usuario SERIAL PRIMARY KEY,
            usuario VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            rol VARCHAR(20) NOT NULL,
            estado VARCHAR(10) NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id_log SERIAL PRIMARY KEY,
            usuario VARCHAR(50) NOT NULL,
            accion VARCHAR(100) NOT NULL,
            detalles TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS dim_version_bd (
            id_version SERIAL PRIMARY KEY,
            fecha_backup VARCHAR(100),
            archivo_origen VARCHAR(255),
            fecha_restauracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            restaurado_por VARCHAR(50)
        );
        CREATE TABLE IF NOT EXISTS fact_reincidencia (
            id_reincidencia SERIAL PRIMARY KEY,
            id_impacto INT REFERENCES dim_impacto(id_impacto),
            id_comportamiento INT REFERENCES dim_comportamiento(id_comportamiento),
            id_codigo INT, fecha_inicio DATE, fecha_fin DATE, cantidad INT,
            resumen TEXT, determinacion_mc VARCHAR(20), id_hecho_evento INT, estado VARCHAR(20) DEFAULT 'Activo',
            usuario_registra VARCHAR(50), fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reincidencia_detalle (
            id_reincidencia INT REFERENCES fact_reincidencia(id_reincidencia) ON DELETE CASCADE,
            id_hecho_comportamiento INT REFERENCES fact_comportamiento(id_hecho_comportamiento),
            PRIMARY KEY (id_reincidencia, id_hecho_comportamiento)
        );
        INSERT INTO dim_usuarios (usuario, password_hash, rol, estado) 
        VALUES ('admin', '{hashed}', 'Super Administrador', 'Activo')
        ON CONFLICT (usuario) DO NOTHING;
        
        INSERT INTO dim_version_bd (fecha_backup, archivo_origen, restaurado_por)
        SELECT 'N/A', 'BD Inicial - Carga desde CSV', 'sistema'
        WHERE NOT EXISTS (SELECT 1 FROM dim_version_bd);
        
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'consulta') THEN
                CREATE ROLE consulta LOGIN PASSWORD 'consulta2026' NOSUPERUSER NOCREATEDB NOCREATEROLE;
            END IF;
        END $$;
        GRANT CONNECT ON DATABASE "Operadores_bd" TO consulta;
        GRANT USAGE ON SCHEMA public TO consulta;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO consulta;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO consulta;
        """
        with engine.begin() as conn:
            conn.execute(text(sql_usuarios))
        print("✅ Tabla 'dim_usuarios' creada.")
    except Exception as e:
        print(f"❌ Error al crear 'dim_usuarios': {e}")
        
    print("🎉 Proceso finalizado. Todo está en PostgreSQL.")

if __name__ == "__main__":
    main()

