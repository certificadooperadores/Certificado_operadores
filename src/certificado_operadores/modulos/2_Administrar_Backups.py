import os
import subprocess
import streamlit as st
import pandas as pd
from datetime import datetime
from db import run_transaction, registrar_auditoria
rol = st.session_state.get('rol')

st.title("💾 Gestión de Backups")
st.markdown("Desde aquí puedes crear, proteger o eliminar backups de la base de datos.")

backups_dir = '/Backups'

if not os.path.exists(backups_dir):
    st.error(f"El directorio {backups_dir} no existe o no está mapeado en el contenedor.")
    st.stop()

# --------------------------------------------------------
# SECCION 1: CREAR NUEVO BACKUP
# --------------------------------------------------------
st.markdown("---")
st.subheader("📦 Crear Nuevo Backup")
confirmar_backup = st.checkbox("Entiendo que el backup se guardará en la carpeta Backups con la fecha y hora actual.")

if st.button("💾 Crear Backup Ahora", disabled=not confirmar_backup):
    fecha_hoy = datetime.now().strftime('%d-%m-%Y')
    version = 1
    for f in os.listdir(backups_dir):
        if f.startswith(fecha_hoy) and f.endswith('.sql'):
            try:
                v = int(f.split('_V')[1].replace('.protegido.sql', '').replace('.sql', ''))
                if v >= version:
                    version = v + 1
            except (IndexError, ValueError):
                pass
    filename = f"{fecha_hoy}_V{version}.sql"
    filepath = os.path.join(backups_dir, filename)
    
    db_user = os.getenv('DB_USER', '')
    db_host = os.getenv('DB_HOST', 'db')
    db_name = os.getenv('DB_NAME', '')
    db_password = os.getenv('DB_PASSWORD', '')
    
    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        result = subprocess.run(
            ['pg_dump', '-h', db_host, '-U', db_user, '-d', db_name, '--clean'],
            capture_output=True, text=True, env=env, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            size_mb = round(len(result.stdout.encode('utf-8')) / (1024 * 1024), 2)
            registrar_auditoria(
                st.session_state.get('usuario', 'Desconocido'),
                'Creación de Backup desde UI',
                f'Archivo: {filename} ({size_mb} MB)'
            )
            run_transaction(
                "INSERT INTO dim_version_bd (fecha_backup, archivo_origen, restaurado_por) VALUES (:fb, :ao, :rp)",
                {"fb": filename, "ao": filename, "rp": st.session_state.get('usuario', 'Desconocido')}
            )
            st.success(f"✅ Backup creado exitosamente: `{filename}` ({size_mb} MB)")
            st.rerun()
        else:
            st.error(f"❌ pg_dump falló: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        st.error("❌ El backup excedió el tiempo máximo de 60 segundos.")
    except Exception as e:
        st.error(f"❌ Error al crear backup: {e}")

# --------------------------------------------------------
# SECCION 2: LISTAR BACKUPS EXISTENTES
# --------------------------------------------------------
st.markdown("---")
st.subheader("📋 Backups Existentes")

archivos = []
for f in os.listdir(backups_dir):
    if f.endswith('.sql'):
        ruta = os.path.join(backups_dir, f)
        stat = os.stat(ruta)
        es_protegido = '.protegido.' in f
        
        archivos.append({
            'Nombre del Archivo': f,
            'Tamaño (MB)': round(stat.st_size / (1024 * 1024), 2),
            'Fecha de Creación': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'Estado': '🔒 Protegido' if es_protegido else '🔓 Desprotegido',
            'ruta_completa': ruta,
            'timestamp': stat.st_mtime,
            'es_protegido': es_protegido
        })

if not archivos:
    st.info("No hay backups disponibles en la carpeta.")
    st.stop()

df_backups = pd.DataFrame(archivos)
df_backups.sort_values(by='timestamp', ascending=False, inplace=True)

st.dataframe(df_backups[['Nombre del Archivo', 'Tamaño (MB)', 'Fecha de Creación', 'Estado']], use_container_width=True)

# --------------------------------------------------------
# SECCION 3: PROTEGER / DESPROTEGER / ELIMINAR
# --------------------------------------------------------
st.markdown("---")
st.subheader("Acciones sobre Backups")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔒 Proteger / Desproteger")
    archivo_sel_prot = st.selectbox("Seleccione el archivo a proteger/desproteger:", df_backups['Nombre del Archivo'].tolist())
    
    if archivo_sel_prot:
        es_prot_actual = df_backups[df_backups['Nombre del Archivo'] == archivo_sel_prot].iloc[0]['es_protegido']
        
        if not es_prot_actual:
            if st.button("Proteger Backup"):
                nuevo_nombre = archivo_sel_prot.replace('.sql', '.protegido.sql')
                os.rename(os.path.join(backups_dir, archivo_sel_prot), os.path.join(backups_dir, nuevo_nombre))
                registrar_auditoria(st.session_state.get('usuario'), 'Protección de Backup', f'Archivo: {nuevo_nombre}')
                st.success(f"Archivo {nuevo_nombre} protegido exitosamente.")
                st.rerun()
        else:
            if st.button("Quitar Protección"):
                nuevo_nombre = archivo_sel_prot.replace('.protegido.sql', '.sql')
                os.rename(os.path.join(backups_dir, archivo_sel_prot), os.path.join(backups_dir, nuevo_nombre))
                registrar_auditoria(st.session_state.get('usuario'), 'Desprotección de Backup', f'Archivo: {nuevo_nombre}')
                st.success(f"Protección removida. Archivo: {nuevo_nombre}.")
                st.rerun()

with col2:
    st.markdown("### 🗑️ Eliminar Backup Antiguo")
    desprotegidos = df_backups[~df_backups['es_protegido']]['Nombre del Archivo'].tolist()
    
    if desprotegidos:
        archivo_sel_elim = st.selectbox("Seleccione el archivo a eliminar (solo desprotegidos):", desprotegidos)
        confirmacion = st.checkbox("Estoy seguro de querer eliminar este archivo físicamente.")
        
        if archivo_sel_elim:
            if st.button("🔴 Eliminar Backup", disabled=not confirmacion):
                os.remove(os.path.join(backups_dir, archivo_sel_elim))
                registrar_auditoria(st.session_state.get('usuario'), 'Eliminación de Backup', f'Archivo: {archivo_sel_elim}')
                st.error(f"Archivo {archivo_sel_elim} eliminado permanentemente.")
                st.rerun()
    else:
        st.info("No hay backups desprotegidos para eliminar.")
