import os
import streamlit as st
from db import run_query

def mostrar_badge_version():
    """Muestra un badge persistente en la barra lateral con la versión actual de la BD"""
    try:
        # 1. Obtener la versión actual de la BD
        df_version = run_query("SELECT archivo_origen, fecha_restauracion FROM dim_version_bd ORDER BY id_version DESC LIMIT 1")
        if df_version.empty:
            return
            
        archivo_actual = df_version.iloc[0]['archivo_origen']
        fecha_rest = df_version.iloc[0]['fecha_restauracion']
        
        # 2. Analizar el directorio de backups
        backups_dir = '/Backups'
        archivos_sql = []
        if os.path.exists(backups_dir):
            # Obtener todos los .sql
            for f in os.listdir(backups_dir):
                if f.endswith('.sql'):
                    ruta_completa = os.path.join(backups_dir, f)
                    # Guardamos (nombre_original, nombre_base, timestamp)
                    # nombre_base es sin .protegido para poder comparar si fue protegido después
                    nombre_base = f.replace('.protegido.sql', '.sql')
                    archivos_sql.append((f, nombre_base, os.path.getmtime(ruta_completa)))
                    
        # Ordenar por fecha de modificación (más reciente primero)
        archivos_sql.sort(key=lambda x: x[2], reverse=True)
        
        # 3. Determinar estado
        es_ultimo = True
        if archivos_sql:
            ultimo_backup_base = archivos_sql[0][1]
            # Si el archivo actual es la BD inicial o no es el último backup
            if archivo_actual == 'BD Inicial - Carga desde CSV':
                # Si hay backups, entonces hay algo más reciente (salvo que acabemos de iniciar y el backup se haya hecho después)
                # Técnicamente si estamos en la inicial, siempre es amarilla si hay backups.
                es_ultimo = False
            else:
                # Quitamos .protegido del archivo actual por si fue protegido después de restaurar
                archivo_actual_base = archivo_actual.replace('.protegido.sql', '.sql')
                if ultimo_backup_base != archivo_actual_base:
                    es_ultimo = False
                    
        # 4. Renderizar UI
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 💾 Estado de Datos")
        
        if es_ultimo:
            st.sidebar.success(f"🟢 **Datos Actualizados**\n\nOrigen: `{archivo_actual}`")
        else:
            st.sidebar.warning(f"🟡 **¡Backup Nuevo Disponible!**\n\nOrigen actual: `{archivo_actual}`\n\nRevisa la carpeta de Backups.")
            
    except Exception as e:
        st.sidebar.markdown("---")
        st.sidebar.error("Error cargando versión de BD")
