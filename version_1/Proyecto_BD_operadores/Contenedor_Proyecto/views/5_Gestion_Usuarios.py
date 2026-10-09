import streamlit as st
import pandas as pd
import bcrypt
from db import run_query, run_transaction
from utils import mostrar_badge_version

st.set_page_config(page_title="Gestión de Usuarios", page_icon="🔐", layout="wide")

if not st.session_state.get('logged_in'):
    st.error("❌ Acceso Denegado. Por favor, inicie sesión en la pantalla principal.")
    st.stop()

rol_actual = st.session_state.get('rol')
if rol_actual not in ['Administrador', 'Super Administrador']:
    st.error("❌ Acceso Denegado. Solo los Administradores o Super Administradores pueden gestionar usuarios.")
    st.stop()

mostrar_badge_version()

st.title("🔐 Gestión de Usuarios del Sistema")
st.markdown("Administra los accesos, roles y contraseñas de la plataforma.")

usuarios = run_query("SELECT id_usuario, usuario, rol, estado, fecha_registro FROM dim_usuarios ORDER BY id_usuario")

st.subheader("Usuarios Registrados")
st.dataframe(usuarios, use_container_width=True)

roles_disponibles = ["Lector", "Administrador"]
if rol_actual == 'Super Administrador':
    roles_disponibles.append("Super Administrador")

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("➕ Agregar Nuevo Usuario")
    with st.form("form_nuevo_usuario"):
        nuevo_user = st.text_input("Nombre de Usuario").strip().lower()
        nuevo_pass = st.text_input("Contraseña", type="password")
        nuevo_rol = st.selectbox("Rol", roles_disponibles)
        
        submit_nuevo = st.form_submit_button("Crear Usuario")
        if submit_nuevo:
            if not nuevo_user or not nuevo_pass:
                st.error("Usuario y contraseña son obligatorios.")
            else:
                existe = run_query("SELECT * FROM dim_usuarios WHERE usuario = :u", {"u": nuevo_user})
                if not existe.empty:
                    st.error("El usuario ya existe.")
                else:
                    hashed = bcrypt.hashpw(nuevo_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    q = "INSERT INTO dim_usuarios (usuario, password_hash, rol, estado) VALUES (:u, :p, :r, 'Activo')"
                    run_transaction(q, {"u": nuevo_user, "p": hashed, "r": nuevo_rol})
                    st.success("Usuario creado exitosamente. Recarga la página para actualizar la tabla.")
                    
with col2:
    st.subheader("🔄 Modificar Usuario Existente")
    with st.form("form_mod_usuario"):
        mod_user_sel = st.selectbox("Seleccione Usuario", usuarios['usuario'].tolist() if not usuarios.empty else [])
        mod_rol = st.selectbox("Nuevo Rol", roles_disponibles)
        mod_estado = st.selectbox("Estado", ["Activo", "Inactivo"])
        mod_pass = st.text_input("Nueva Contraseña (Opcional)", type="password", help="Deje en blanco si no desea cambiar la contraseña.")
        
        submit_mod = st.form_submit_button("Actualizar Usuario")
        if submit_mod and mod_user_sel:
            user_data = usuarios[usuarios['usuario'] == mod_user_sel]
            if not user_data.empty and user_data.iloc[0]['rol'] == 'Super Administrador' and rol_actual != 'Super Administrador':
                st.error("No tienes permisos para modificar cuentas de Super Administrador.")
            elif mod_user_sel == st.session_state.get('usuario') and mod_estado == 'Inactivo':
                st.error("No puedes inactivar tu propio usuario.")
            else:
                if mod_pass:
                    hashed = bcrypt.hashpw(mod_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    q = "UPDATE dim_usuarios SET rol = :r, estado = :e, password_hash = :p WHERE usuario = :u"
                    run_transaction(q, {"r": mod_rol, "e": mod_estado, "p": hashed, "u": mod_user_sel})
                else:
                    q = "UPDATE dim_usuarios SET rol = :r, estado = :e WHERE usuario = :u"
                    run_transaction(q, {"r": mod_rol, "e": mod_estado, "u": mod_user_sel})
                st.success("Usuario actualizado exitosamente. Recarga la página para ver los cambios.")
