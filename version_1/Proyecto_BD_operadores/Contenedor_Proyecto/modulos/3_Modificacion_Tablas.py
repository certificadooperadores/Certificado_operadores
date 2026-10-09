import streamlit as st
import pandas as pd
from db import run_query, run_transaction, registrar_auditoria
rol = st.session_state.get('rol')
usuario = st.session_state.get('usuario', 'Desconocido')

st.title("🗑️ Módulo de Modificación y Auditoría")
st.markdown("Permite inactivar o eliminar lotes de eventos registrados por error.")

lotes_query = """
    SELECT TO_CHAR(fecha_registro::timestamp, 'YYYY-MM-DD HH24:MI') as lote, COUNT(*) as total_registros
    FROM fact_eventos_operador 
    GROUP BY TO_CHAR(fecha_registro::timestamp, 'YYYY-MM-DD HH24:MI')
    ORDER BY lote DESC
"""
lotes_df = run_query(lotes_query)

if lotes_df.empty:
    st.info("No hay eventos registrados en la base de datos.")
    st.stop()

opciones_lotes = [f"{row['lote']} ({row['total_registros']} registros)" for _, row in lotes_df.iterrows()]
lote_seleccionado = st.selectbox("Seleccione el Lote (Fecha y Minuto de Cargue)", opciones_lotes)

lote_str = lote_seleccionado.split(" (")[0]

detalle_query = """
    SELECT 
        e.id_hecho_evento, 
        c.id_codigo as codigo_operacion, 
        c.id_persona as cedula,
        p.nombres || ' ' || p.primer_apellido as nombre_completo,
        te.nombre_evento, 
        TO_CHAR(e.fecha_registro::timestamp, 'YYYY-MM-DD HH24:MI') as registro,
        e.id_vigencia,
        CASE WHEN e.id_vigencia = 1 THEN '✅ Vigente' ELSE '❌ Anulado' END as estado_actual
    FROM fact_eventos_operador e
    JOIN dim_codigo c ON e.id_codigo = c.id_codigo
    JOIN dim_persona p ON c.id_persona = p.id_persona
    JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
    WHERE TO_CHAR(e.fecha_registro::timestamp, 'YYYY-MM-DD HH24:MI') = :lote
    ORDER BY e.id_hecho_evento
"""
detalle_df = run_query(detalle_query, {"lote": lote_str})

vigentes = detalle_df[detalle_df['id_vigencia'] == 1]
anulados = detalle_df[detalle_df['id_vigencia'] == 2]

st.markdown("---")
st.subheader(f"Lote: {lote_str}  —  {len(vigentes)} vigentes, {len(anulados)} anulados")

tab_lote, tab_registros = st.tabs(["📦 Modo Lote Completo", "🎯 Modo Registro Individual"])

# ==========================================
# TAB 1: MODO LOTE COMPLETO
# ==========================================
with tab_lote:
    st.dataframe(detalle_df[['id_hecho_evento', 'codigo_operacion', 'cedula', 'nombre_completo', 'nombre_evento', 'registro', 'estado_actual']], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.warning("⚠️ Las siguientes acciones afectan a TODOS los registros del lote.")
    
    confirmacion_lote = st.checkbox("Estoy seguro de querer modificar TODOS los registros de este lote.", key="conf_lote")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🟡 Inactivar Todo el Lote", disabled=not confirmacion_lote):
            update_query = """
                UPDATE fact_eventos_operador 
                SET id_vigencia = 2 
                WHERE TO_CHAR(fecha_registro::timestamp, 'YYYY-MM-DD HH24:MI') = :lote AND id_vigencia = 1
            """
            run_transaction(update_query, {"lote": lote_str})
            registrar_auditoria(usuario, 'Inactivar Lote Completo', f'Lote: {lote_str}')
            st.success(f"✅ Lote '{lote_str}' inactivado completamente.")
            st.rerun()
    
    with col2:
        if rol == 'Super Administrador':
            if st.button("🔴 Borrar Todo el Lote", disabled=not confirmacion_lote):
                delete_query = """
                    DELETE FROM fact_eventos_operador 
                    WHERE TO_CHAR(fecha_registro::timestamp, 'YYYY-MM-DD HH24:MI') = :lote
                """
                run_transaction(delete_query, {"lote": lote_str})
                registrar_auditoria(usuario, 'Borrado Físico Lote Completo', f'Lote: {lote_str}')
                st.error(f"🗑️ Lote '{lote_str}' eliminado permanentemente.")
                st.rerun()
        else:
            st.info("🔒 Solo Super Administrador puede borrar físicamente.")

# ==========================================
# TAB 2: MODO REGISTRO INDIVIDUAL
# ==========================================
with tab_registros:
    if detalle_df.empty:
        st.info("No hay registros en este lote.")
        st.stop()
    
    # Filtro por estado
    df_filtrado = detalle_df.copy()
    filtro_estado = st.radio("Filtrar por estado:", ["Todos", "Solo Vigentes", "Solo Anulados"], horizontal=True)
    if filtro_estado == "Solo Vigentes":
        df_filtrado = vigentes.copy()
    elif filtro_estado == "Solo Anulados":
        df_filtrado = anulados.copy()
    else:
        df_filtrado = detalle_df.copy()
    
    st.markdown(f"**{len(df_filtrado)} registros** — Seleccioná los que querés modificar:")
    
    # Multiselect para elegir registros por ID
    opciones_registros = df_filtrado['id_hecho_evento'].tolist()
    seleccionados = st.multiselect(
        "IDs de eventos a modificar:",
        opciones_registros
    )
    
    if seleccionados:
        df_sel = df_filtrado[df_filtrado['id_hecho_evento'].isin(seleccionados)]
        st.dataframe(df_sel[['id_hecho_evento', 'codigo_operacion', 'cedula', 'nombre_completo', 'nombre_evento', 'estado_actual']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.warning(f"⚠️ Vas a modificar {len(seleccionados)} registro(s).")
        
        confirmacion_reg = st.checkbox("Confirmo que quiero modificar estos registros.", key="conf_reg")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🟡 Inactivar Seleccionados", disabled=not confirmacion_reg):
                ids_str = ','.join(str(int(x)) for x in seleccionados)
                update_query = f"""
                    UPDATE fact_eventos_operador 
                    SET id_vigencia = 2 
                    WHERE id_hecho_evento IN ({ids_str})
                """
                run_transaction(update_query)
                registrar_auditoria(usuario, 'Inactivar Registros Individuales', f'IDs: {ids_str}')
                st.success(f"✅ {len(seleccionados)} registro(s) inactivado(s).")
                st.rerun()
        
        with col2:
            if rol == 'Super Administrador':
                if st.button("🔴 Eliminar Seleccionados", disabled=not confirmacion_reg):
                    ids_str = ','.join(str(int(x)) for x in seleccionados)
                    delete_query = f"""
                        DELETE FROM fact_eventos_operador 
                        WHERE id_hecho_evento IN ({ids_str})
                    """
                    run_transaction(delete_query)
                    registrar_auditoria(usuario, 'Borrado Físico Registros Individuales', f'IDs: {ids_str}')
                    st.error(f"🗑️ {len(seleccionados)} registro(s) eliminado(s) permanentemente.")
                    st.rerun()
            else:
                st.info("🔒 Solo Super Administrador puede borrar físicamente.")
    else:
        st.info("Seleccioná uno o más registros para ver las opciones de modificación.")

