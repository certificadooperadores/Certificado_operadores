import streamlit as st
import pandas as pd
import io
import math
from datetime import datetime
from db import run_query, run_transaction, registrar_auditoria
usuario_actual = st.session_state.get('usuario', 'Usuario')
rol_actual = st.session_state.get('rol', 'Desconocido')

st.title("📅 Registro de Eventos e Historial")
st.markdown("""<style>input[type=number]::-webkit-outer-spin-button,input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}input[type=number]{-moz-appearance:textfield}</style>""",unsafe_allow_html=True)

# Helpers
def clean_text(text):
    if pd.isna(text) or str(text).strip() == "":
        return None
    return str(text).strip()

def clean_int(val):
    if pd.isna(val) or str(val).strip() == "":
        return None
    try:
        return int(float(val))
    except ValueError:
        return "INVALID"

# Cargar catálogos comunes
tipos_evento = run_query("SELECT id_tipo_evento, nombre_evento FROM dim_tipo_evento ORDER BY id_tipo_evento")
vehiculos = run_query("SELECT id_vehiculo, nombre_vehiculo FROM dim_vehiculo")

# Cargar lista de evaluadores (para eventos 1 y 3)
evaluadores_db = run_query("SELECT DISTINCT evaluador FROM fact_eventos_operador WHERE evaluador IS NOT NULL ORDER BY evaluador")
lista_evaluadores = evaluadores_db['evaluador'].tolist() if not evaluadores_db.empty else []
lista_evaluadores.append("➕ OTRO (Nuevo Evaluador)")

tab_manual, tab_masiva = st.tabs(["Ingreso Individual", "Carga Masiva (Excel)"])

# ==========================================
# PESTAÑA 1: INGRESO MANUAL
# ==========================================
with tab_manual:
    st.markdown("Busca a un operador por su **Cédula** o **Código de Operación** para registrarle un evento. **El operador debe existir y tener un código activo.**")
    busqueda_str = st.text_input("Buscar por Cédula o Código", key="busqueda_cert").strip()
    busqueda_input = int(busqueda_str) if busqueda_str and busqueda_str.isdigit() else None

    if busqueda_input:
        busqueda_str = str(int(busqueda_input))
        
        if len(busqueda_str) <= 5:
            # Es un Código de Operación (5 caracteres o menos)
            q_cod = "SELECT id_persona, id_codigo FROM dim_codigo WHERE id_codigo = :num AND id_vigencia = 1 AND id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7) LIMIT 1"
            codigos = run_query(q_cod, {"num": busqueda_input})
            if codigos.empty:
                st.error("❌ No se encontró ningún operador activo con ese Código de Operación.")
                st.stop()
            codigo_actual = int(codigos.iloc[0]['id_codigo'])
            cedula_real = int(codigos.iloc[0]['id_persona'])
            persona = run_query("SELECT * FROM dim_persona WHERE id_persona = :ced", {"ced": cedula_real})
            datos = persona.iloc[0]
        else:
            # Es una Cédula (más de 5 caracteres)
            persona = run_query("SELECT * FROM dim_persona WHERE id_persona = :num", {"num": busqueda_input})
            if persona.empty:
                st.error("❌ El operador no existe. Debes crearlo primero en la pestaña de Administración de Operadores.")
                st.stop()
                
            q_cod = "SELECT id_codigo FROM dim_codigo WHERE id_persona = :num AND id_vigencia = 1 AND id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7) ORDER BY fecha_registro DESC LIMIT 1"
            codigos = run_query(q_cod, {"num": busqueda_input})
            if codigos.empty:
                st.error("❌ Este operador existe pero NO tiene un código activo registrado. Asígnale un código primero.")
                st.stop()
            codigo_actual = int(codigos.iloc[0]['id_codigo'])
            cedula_real = busqueda_input
            datos = persona.iloc[0]
            
        st.info(f"👤 **Operador Encontrado:** {datos['nombres']} {datos['primer_apellido']} | **Cédula:** {cedula_real} | **Código Activo:** {codigo_actual}")

        st.subheader("1. Seleccionar Tipo de Evento")
        evento_str = st.selectbox("Evento a registrar", tipos_evento['id_tipo_evento'].astype(str) + " - " + tipos_evento['nombre_evento'].str.title())
        id_tipo_ev = int(evento_str.split(" - ")[0])
        
        with st.form("form_evento"):
            st.subheader("2. Detalles del Evento")
            
            # Variables para capturar los datos dinámicos
            veh, eva, fpru, fcer = None, None, None, None
            observacion = None
            f_obs = None
            f_retiro, f_notif, f_susp = None, None, None
            r_medica, e_proteccion, i_rmedica, f_rmedica = None, None, None, None
            
            if id_tipo_ev == 1: # Certificacion
                st.markdown("**Campos de Certificación**")
                col1, col2 = st.columns(2)
                with col1:
                    if not vehiculos.empty:
                        veh_sel = st.selectbox("Vehículo Evaluado", vehiculos['id_vehiculo'].astype(str) + " - " + vehiculos['nombre_vehiculo'], index=None)
                        veh = int(veh_sel.split(" - ")[0]) if veh_sel else None
                    evaluador_sel = st.selectbox("Evaluador Registrado", lista_evaluadores, key="ev1", index=None)
                    if evaluador_sel == "➕ OTRO (Nuevo Evaluador)":
                        eva = st.text_input("Escribe el nombre del Nuevo Evaluador").strip().title()
                    else:
                        eva = evaluador_sel
                with col2:
                    fpru = st.date_input("Fecha de Prueba", value=None)
                    fcer = st.date_input("Fecha de Certificado", value=None)
                observacion = st.text_area("Observación (Opcional)")
                
            elif id_tipo_ev == 2: # Reactivacion
                st.markdown("**Campos de Reactivación**")
                col1, col2 = st.columns(2)
                with col1:
                    evaluador_sel = st.selectbox("Evaluador Registrado", lista_evaluadores, key="ev2", index=None)
                    if evaluador_sel == "➕ OTRO (Nuevo Evaluador)":
                        eva = st.text_input("Escribe el nombre del Nuevo Evaluador").strip().title()
                    else:
                        eva = evaluador_sel
                with col2:
                    fcer = st.date_input("Fecha de Certificado", value=None)
                    fpru = st.date_input("Fecha de Prueba", value=None)
                observacion = st.text_area("Observación (Opcional)")
                
            elif id_tipo_ev == 3: # Renovacion
                st.markdown("**Campos de Renovación**")
                col1, col2 = st.columns(2)
                with col1:
                    evaluador_sel = st.selectbox("Evaluador Registrado", lista_evaluadores, key="ev3", index=None)
                    if evaluador_sel == "➕ OTRO (Nuevo Evaluador)":
                        eva = st.text_input("Escribe el nombre del Nuevo Evaluador").strip().title()
                    else:
                        eva = evaluador_sel
                with col2:
                    fpru = st.date_input("Fecha de Prueba", value=None)
                observacion = st.text_area("Observación (Opcional)")
                
            elif id_tipo_ev in [4, 8, 9]: # Observación, Advertencia, Condicionamiento
                if id_tipo_ev == 4:
                    st.markdown("**Observación**")
                elif id_tipo_ev == 8:
                    st.markdown("**Advertencia**")
                else:
                    st.markdown("**Condicionamiento**")
                f_obs = st.date_input("Fecha de la Novedad", value=None)
                observacion = st.text_area("Descripción de la Observación")
                
            elif id_tipo_ev == 5: # Restriccion Medica
                st.markdown("**Campos de Restricción Médica**")
                r_medica = st.text_area("Descripción de la Restricción Médica")
                e_proteccion = st.text_input("Elemento de Protección (Opcional)")
                col3, col4 = st.columns(2)
                with col3:
                    i_rmedica = st.date_input("Inicio de Restricción", value=None)
                with col4:
                    f_rmedica = st.date_input("Fin de Restricción", value=None)
                observacion = st.text_area("Observación adicional (Opcional)")
                
            elif id_tipo_ev == 6: # Suspension
                st.markdown("**Campos de Suspensión**")
                f_susp = st.date_input("Fecha de Suspensión", value=None)
                observacion = st.text_area("Motivo / Observación (Opcional)")
                
            elif id_tipo_ev == 7: # Cancelacion o Notificacion Retiro
                st.markdown("**Campos de Retiro y Cancelación**")
                col5, col6 = st.columns(2)
                with col5:
                    f_retiro = st.date_input("Fecha de Retiro / Cancelación", value=None)
                with col6:
                    f_notif = st.date_input("Fecha de Notificación", value=None)
                observacion = st.text_area("Motivo (Obligatorio)")
                
            submit_evento = st.form_submit_button("Guardar Evento")
            
            if submit_evento:
                # Validaciones especificas
                error = False
                if id_tipo_ev == 1 and (veh is None or not eva):
                    st.error("Vehículo y Evaluador son obligatorios para este evento.")
                    error = True
                elif id_tipo_ev in [2, 3] and not eva:
                    st.error("Evaluador es obligatorio para este evento.")
                    error = True
                elif id_tipo_ev == 5 and not r_medica:
                    st.error("Debe describir la restricción médica.")
                    error = True
                elif id_tipo_ev == 5 and f_rmedica is None:
                    st.error("La fecha de Fin de Restricción es obligatoria.")
                    error = True
                elif id_tipo_ev == 7 and not observacion:
                    st.error("Debe escribir un motivo para la Cancelación / Retiro.")
                    error = True
                elif id_tipo_ev == 7 and f_retiro is None and f_notif is None:
                    st.error("Debe seleccionar al menos una fecha (Retiro o Notificación).")
                    error = True
                elif id_tipo_ev in [4, 8, 9] and not observacion:
                    st.error("Debe escribir la observación.")
                    error = True
                elif id_tipo_ev in [4, 8, 9] and f_obs is None:
                    st.error("Debe seleccionar la fecha de la novedad.")
                    error = True
                    
                if not error:
                    # Parsear fechas si existen
                    fp_s = fpru.strftime('%Y-%m-%d') if fpru else None
                    fc_s = fcer.strftime('%Y-%m-%d') if fcer else None
                    fr_s = f_retiro.strftime('%Y-%m-%d') if f_retiro else None
                    fn_s = f_notif.strftime('%Y-%m-%d') if f_notif else None
                    fs_s = f_susp.strftime('%Y-%m-%d') if f_susp else None
                    ir_s = i_rmedica.strftime('%Y-%m-%d') if i_rmedica else None
                    fir_s = f_rmedica.strftime('%Y-%m-%d') if f_rmedica else None
                    fo_s = f_obs.strftime('%Y-%m-%d') if f_obs else None
                    
                    max_evt = run_query("SELECT COALESCE(MAX(id_hecho_evento), 0) + 1 as n FROM fact_eventos_operador").iloc[0]['n']
                    
                    q_evt = """INSERT INTO fact_eventos_operador 
                               (id_hecho_evento, id_codigo, id_tipo_evento, id_vehiculo_evaluado, evaluador, 
                               fecha_prueba, fecha_certificado, fecha_retiro, fecha_notificacion_retiro, 
                               fecha_suspension, restriccion_medica, elemento_de_proteccion, 
                               inicio_restriccion_medica, fin_restriccion_medica, fecha_observacion, observacion, id_vigencia, usuario_registra, fecha_registro) 
                               VALUES (:id, :cod, :tip, :veh, :eva, :fp, :fc, :fr, :fn, :fs, :rm, :ep, :ir, :fir, :fo, :obs, 1, :u, CURRENT_TIMESTAMP)"""
                               
                    params = {
                        "id": int(max_evt), "cod": codigo_actual, "tip": id_tipo_ev,
                        "veh": veh, "eva": eva, "fp": fp_s, "fc": fc_s, "fr": fr_s,
                        "fn": fn_s, "fs": fs_s, "rm": r_medica, "ep": e_proteccion,
                        "ir": ir_s, "fir": fir_s, "fo": fo_s, "obs": observacion, "u": usuario_actual
                    }
                    
                    success, msg = run_transaction(q_evt, params)
                    if success:
                        registrar_auditoria(st.session_state.get('usuario', 'Desconocido'), 'Registro Evento Manual', f'Codigo: {codigo_actual}, Evento ID: {id_tipo_ev}')
                        st.success("✅ ¡Evento registrado exitosamente en el historial del operador!")
                        st.balloons()
                    else:
                        st.error(f"❌ Error al registrar el evento: {msg}")

# ==========================================
# PESTAÑA 2: CARGA MASIVA
# ==========================================
with tab_masiva:
    st.markdown("Descarga la Plantilla Maestra y sube la hoja del evento que deseas cargar de forma masiva.")
    
    @st.cache_data
    def generar_plantilla_eventos():
        # Hoja Instrucciones
        inst_data = [
            ["Cédula (Todas las hojas)", "Es obligatoria. Sirve para identificar al operador y aplicarle el evento a su código activo."],
            ["Evento 1 (Certificación)", "Requiere id_vehiculo_evaluado, evaluador, fecha_prueba, fecha_certificado, nota."],
            ["Evento 2 (Reactivación)", "Requiere fecha_certificado, fecha_prueba, evaluador, nota."],
            ["Evento 3 (Renovación)", "Requiere fecha_prueba, evaluador, nota."],
            ["Evento 4 (Observación)", "Requiere fecha_observacion y observación."],
            ["Evento 5 (Restricción Médica)", "Requiere restriccion_medica, inicio_restriccion_medica, elemento_de_proteccion, fin_restriccion_medica, nota."],
            ["Evento 6 (Suspensión)", "Requiere fecha_suspension, nota."],
            ["Evento 7 (Cancelación / Notif. Retiro)", "Requiere observación y al menos una fecha (fecha_retiro o fecha_notificacion_retiro)."],
            ["Evento 8 (Advertencia)", "Requiere fecha_observacion y observación."],
            ["Evento 9 (Condicionamiento)", "Requiere fecha_observacion y observación."]
        ]
        df_inst = pd.DataFrame(inst_data, columns=["Aspecto", "Instrucción"])
        
        # Hojas de plantillas
        df_1 = pd.DataFrame(columns=["cedula", "id_vehiculo_evaluado", "evaluador", "fecha_prueba", "fecha_certificado", "observacion"])
        df_2 = pd.DataFrame(columns=["cedula", "fecha_certificado", "fecha_prueba", "evaluador", "observacion"])
        df_3 = pd.DataFrame(columns=["cedula", "fecha_prueba", "evaluador", "observacion"])
        df_4 = pd.DataFrame(columns=["cedula", "fecha_observacion", "observacion"])
        df_5 = pd.DataFrame(columns=["cedula", "restriccion_medica", "elemento_de_proteccion", "inicio_restriccion_medica", "fin_restriccion_medica", "observacion"])
        df_6 = pd.DataFrame(columns=["cedula", "fecha_suspension", "observacion"])
        df_7_8 = pd.DataFrame(columns=["cedula", "fecha_retiro", "fecha_notificacion_retiro", "observacion"])
        df_8 = pd.DataFrame(columns=["cedula", "fecha_observacion", "observacion"])
        df_9 = pd.DataFrame(columns=["cedula", "fecha_observacion", "observacion"])
        
        # Evaluadores válidos
        df_evaluadores = pd.DataFrame(lista_evaluadores[:-1], columns=["Evaluadores Históricos Disponibles"]) if len(lista_evaluadores) > 1 else pd.DataFrame(["No hay registros"], columns=["Evaluadores Históricos Disponibles"])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_inst.to_excel(writer, index=False, sheet_name='INSTRUCCIONES', startrow=0, startcol=0)
            df_evaluadores.to_excel(writer, index=False, sheet_name='INSTRUCCIONES', startrow=0, startcol=3)
            
            df_1.to_excel(writer, index=False, sheet_name='1-Certificacion')
            df_2.to_excel(writer, index=False, sheet_name='2-Reactivacion')
            df_3.to_excel(writer, index=False, sheet_name='3-Renovacion')
            df_4.to_excel(writer, index=False, sheet_name='4-Observacion')
            df_5.to_excel(writer, index=False, sheet_name='5-Restriccion Medica')
            df_6.to_excel(writer, index=False, sheet_name='6-Suspension')
            df_7_8.to_excel(writer, index=False, sheet_name='7-Retiros')
            df_8.to_excel(writer, index=False, sheet_name='8-Advertencia')
            df_9.to_excel(writer, index=False, sheet_name='9-Condicionamiento')
            
        return output.getvalue()
        
    st.download_button(
        label="📥 Descargar Plantilla Maestra de Eventos",
        data=generar_plantilla_eventos(),
        file_name="Plantilla_Eventos_Operadores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    
    # Mapeo de Nombres de Hoja
    hojas_map = {
        1: "1-Certificacion",
        2: "2-Reactivacion",
        3: "3-Renovacion",
        4: "4-Observacion",
        5: "5-Restriccion Medica",
        6: "6-Suspension",
        7: "7-Retiros",
        8: "8-Advertencia",
        9: "9-Condicionamiento"
    }
    
    col_sel, col_up = st.columns([1, 2])
    with col_sel:
        evento_masivo_str = st.selectbox("¿Qué tipo de evento vas a procesar?", tipos_evento['id_tipo_evento'].astype(str) + " - " + tipos_evento['nombre_evento'].str.title())
        id_tipo_masivo = int(evento_masivo_str.split(" - ")[0])
        hoja_esperada = hojas_map[id_tipo_masivo]
        st.info(f"El sistema leerá ÚNICAMENTE la hoja: **{hoja_esperada}**")
        
    with col_up:
        archivo_subido = st.file_uploader("Sube el archivo diligenciado (Excel)", type=["xlsx"], key="upload_cert")
        
    if archivo_subido:
        try:
            df_up = pd.read_excel(archivo_subido, sheet_name=hoja_esperada)
            st.write("🔍 **Vista Previa de los Datos Subidos:**")
            
            df_up['Estado'] = ""
            df_up['Validacion'] = "🟢 OK"
            df_up['codigo_interno'] = None # Guardar codigo para el insert final
            
            for index, row in df_up.iterrows():
                ced = clean_int(row.get('cedula'))
                if ced == "INVALID" or ced is None:
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Cédula inválida o vacía"
                    continue
                    
                # Validar existencia de operador
                q_cod = "SELECT id_codigo FROM dim_codigo WHERE id_persona = :ced AND id_vigencia = 1 AND id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7) ORDER BY fecha_registro DESC LIMIT 1"
                codigos = run_query(q_cod, {"ced": ced})
                if codigos.empty:
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Cédula no tiene código activo registrado."
                    continue
                else:
                    df_up.at[index, 'codigo_interno'] = int(codigos.iloc[0]['id_codigo'])
                    df_up.at[index, 'Estado'] = "Listo para procesar"
                    
                # Validaciones específicas por evento
                if id_tipo_masivo == 1:
                    v = clean_int(row.get('id_vehiculo_evaluado'))
                    e = clean_text(row.get('evaluador'))
                    if v == "INVALID" or v is None or not e:
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Vehículo evaluado y evaluador son obligatorios."
                elif id_tipo_masivo in [2, 3]:
                    e = clean_text(row.get('evaluador'))
                    if not e:
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Evaluador es obligatorio."
                elif id_tipo_masivo == 5:
                    if not clean_text(row.get('restriccion_medica')):
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Falta Descripción de Restricción."
                    elif pd.isna(row.get('fin_restriccion_medica')):
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Falta Fin de Restricción."
                elif id_tipo_masivo == 7:
                    if not clean_text(row.get('observacion')):
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Retiro/Cancelación requiere Motivo (observación)."
                    else:
                        fr = row.get('fecha_retiro')
                        fn = row.get('fecha_notificacion_retiro')
                        if pd.isna(fr) and pd.isna(fn):
                            df_up.at[index, 'Validacion'] = "🔴 ERROR: Debe indicar al menos una fecha (retiro o notificación)."
                elif id_tipo_masivo in [4, 8, 9]:
                    if not clean_text(row.get('observacion')):
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Observación requiere una nota."
                    elif pd.isna(row.get('fecha_observacion')):
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Falta fecha_observacion."
                        
            st.dataframe(df_up.drop(columns=['codigo_interno']), use_container_width=True)
            hay_errores = any("🔴" in str(val) for val in df_up['Validacion'])
            
            if hay_errores:
                st.error("Corrige los errores marcados en rojo en tu Excel y vuelve a subir el archivo.")
            else:
                st.info("💡 Haz clic en 'Procesar Carga' para inyectar estos eventos al historial.")
                if st.button("🚀 Procesar Eventos"):
                    exitosos = 0
                    for index, row in df_up.iterrows():
                        cod = row['codigo_interno']
                        
                        # Helpers para sacar valores limpios
                        def get_dt(col_name):
                            raw = row.get(col_name)
                            if pd.isna(raw): return None
                            try: return pd.to_datetime(raw).strftime('%Y-%m-%d')
                            except: return None
                            
                        # Mapear variables según tipo
                        veh = clean_int(row.get('id_vehiculo_evaluado'))
                        eva = clean_text(row.get('evaluador'))
                        observacion = clean_text(row.get('observacion'))
                        rm = clean_text(row.get('restriccion_medica'))
                        ep = clean_text(row.get('elemento_de_proteccion'))
                        
                        fp = get_dt('fecha_prueba')
                        fc = get_dt('fecha_certificado')
                        fs = get_dt('fecha_suspension')
                        fr = get_dt('fecha_retiro')
                        fn = get_dt('fecha_notificacion_retiro')
                        ir = get_dt('inicio_restriccion_medica')
                        fir = get_dt('fin_restriccion_medica')
                        fo = get_dt('fecha_observacion')
                        
                        max_evt = run_query("SELECT COALESCE(MAX(id_hecho_evento), 0) + 1 as n FROM fact_eventos_operador").iloc[0]['n']
                        
                        q_evt = """INSERT INTO fact_eventos_operador 
                                   (id_hecho_evento, id_codigo, id_tipo_evento, id_vehiculo_evaluado, evaluador, 
                                   fecha_prueba, fecha_certificado, fecha_retiro, fecha_notificacion_retiro, 
                                   fecha_suspension, restriccion_medica, elemento_de_proteccion, 
                                   inicio_restriccion_medica, fin_restriccion_medica, fecha_observacion, observacion, id_vigencia, usuario_registra, fecha_registro) 
                                   VALUES (:id, :cod, :tip, :veh, :eva, :fp, :fc, :fr, :fn, :fs, :rm, :ep, :ir, :fir, :fo, :obs, 1, :u, CURRENT_TIMESTAMP)"""
                                   
                        params = {
                            "id": int(max_evt), "cod": cod, "tip": id_tipo_masivo,
                            "veh": veh if veh != "INVALID" else None, "eva": eva, "fp": fp, "fc": fc, "fr": fr,
                            "fn": fn, "fs": fs, "rm": rm, "ep": ep,
                            "ir": ir, "fir": fir, "fo": fo, "obs": observacion, "u": usuario_actual
                        }
                        
                        run_transaction(q_evt, params)
                        exitosos += 1
                        
                    registrar_auditoria(st.session_state.get('usuario', 'Desconocido'), 'Carga Masiva de Eventos', f'Registros exitosos: {exitosos}')
                    st.success(f"✅ ¡Carga completada! {exitosos} eventos procesados e inyectados.")
                    st.balloons()
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
