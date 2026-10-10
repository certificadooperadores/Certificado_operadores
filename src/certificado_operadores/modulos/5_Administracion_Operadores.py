import streamlit as st
import pandas as pd
import io
import math
from datetime import datetime
from db import run_query, run_transaction, registrar_auditoria
usuario_actual = st.session_state.get('usuario', 'Usuario')
rol_actual = st.session_state.get('rol', 'Desconocido')

st.title("👨‍✈️ Administración de Operadores")
st.markdown("""<style>input[type=number]::-webkit-outer-spin-button,input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}input[type=number]{-moz-appearance:textfield}</style>""",unsafe_allow_html=True)

# Helpers
def clean_text(text):
    if pd.isna(text) or str(text).strip() == "":
        return None
    return str(text).strip().title()

def clean_int(val):
    if pd.isna(val) or str(val).strip() == "":
        return None
    try:
        return int(float(val))
    except ValueError:
        return "INVALID"

tab_manual, tab_masiva = st.tabs(["Ingreso y Modificación", "Carga Masiva (Excel)"])

# ==========================================
# PESTAÑA 1: INGRESO Y MODIFICACIÓN
# ==========================================
with tab_manual:
    st.markdown("Consulta una cédula. Si el operador no existe, podrás crearlo. Si ya existe, podrás actualizar sus datos, asignarle un nuevo código y registrar su licencia.")
    cedula_str = st.text_input("Número de Documento (Cédula)", key="cedula_oper").strip()
    cedula_input = int(cedula_str) if cedula_str and cedula_str.isdigit() else None

    if cedula_input:
        persona = run_query("SELECT * FROM dim_persona WHERE id_persona = :ced", {"ced": cedula_input})
        existe = not persona.empty
        
        # Buscar el código actual si existe
        codigo_actual = None
        if existe:
            st.info("⚠️ Este operador YA EXISTE en la base de datos. Puedes actualizar sus datos o asignarle un nuevo código de operación.")
            datos = persona.iloc[0]
            def_p_ape = datos['primer_apellido']
            def_s_ape = datos['segundo_apellido'] if pd.notna(datos['segundo_apellido']) else ""
            def_nom = datos['nombres']
            def_gen = datos['genero']
            try:
                def_fec = datetime.strptime(str(datos['fecha_de_nacimiento']), '%Y-%m-%d').date() if pd.notna(datos['fecha_de_nacimiento']) else None
            except:
                def_fec = None
                
            # Intentar traer el código activo (que no tenga evento de cancelación 7)
            q_cod = "SELECT id_codigo FROM dim_codigo WHERE id_persona = :ced AND id_vigencia = 1 AND id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7) ORDER BY fecha_registro DESC LIMIT 1"
            codigos = run_query(q_cod, {"ced": cedula_input})
            if not codigos.empty:
                codigo_actual = int(codigos.iloc[0]['id_codigo'])
        else:
            st.success("✨ Operador Nuevo. Completa sus datos para registrarlo.")
            def_p_ape, def_s_ape, def_nom = "", "", ""
            def_gen = ""
            def_fec = None

        # Valores por defecto para Licencia
        def_lic_tipo = ""
        def_lic_fecha = None
        if codigo_actual:
            licencia = run_query("SELECT tipo, vencimiento FROM fact_licencias WHERE id_codigo = :cod ORDER BY id_hecho_licencia DESC LIMIT 1", {"cod": codigo_actual})
            if not licencia.empty:
                def_lic_tipo = licencia.iloc[0]['tipo']
                try:
                    def_lic_fecha = datetime.strptime(str(licencia.iloc[0]['vencimiento']), '%Y-%m-%d').date() if pd.notna(licencia.iloc[0]['vencimiento']) else None
                except:
                    def_lic_fecha = None

        st.subheader("1. Datos Personales")
        col1, col2 = st.columns(2)
        with col1:
            nombres = st.text_input("Nombres", value=def_nom).strip().title()
            primer_ape = st.text_input("Primer Apellido", value=def_p_ape).strip().title()
            segundo_ape = st.text_input("Segundo Apellido (Opcional)", value=def_s_ape).strip().title()
        with col2:
            genero_opciones = ["", "M", "F", "OTRO"]
            idx_gen = 0 if not def_gen else (1 if def_gen == "M" else (2 if def_gen == "F" else 3))
            genero_sel = st.selectbox("Género", genero_opciones, index=idx_gen)
            genero = genero_sel if genero_sel != "" else None
            fecha_nac = st.date_input("Fecha de Nacimiento", value=def_fec, min_value=datetime(1930, 1, 1), max_value=datetime.today())
            
        st.subheader("2. Código de Operación")
        empresas = run_query("SELECT id_empresa, nombre_empresa FROM dim_empresa WHERE id_vigencia = 1")
        tipologias = run_query("SELECT id_perfil_tipologia FROM dim_perfil_tipologia WHERE id_vigencia = 1")
        if not empresas.empty and not tipologias.empty:
            col3, col4 = st.columns(2)
            with col3:
                empresa_sel = st.selectbox("Empresa", empresas['id_empresa'].astype(str) + " - " + empresas['nombre_empresa'], index=None, placeholder="Seleccione Empresa...")
                id_empresa = int(empresa_sel.split(" - ")[0]) if empresa_sel else None
                
                codigo_sugerido = ""
                if codigo_actual:
                    codigo_sugerido = str(codigo_actual)
                elif id_empresa is not None:
                    max_cod_db = run_query("SELECT MAX(id_codigo) as max_c FROM dim_codigo WHERE id_empresa = :emp", {"emp": id_empresa})
                    if not max_cod_db.empty and pd.notna(max_cod_db.iloc[0]['max_c']):
                        codigo_sugerido = str(int(max_cod_db.iloc[0]['max_c']) + 1)
                    else:
                        codigo_sugerido = f"{id_empresa}0001"
                        
                nuevo_codigo_str = st.text_input("Código a Asignar", value=codigo_sugerido).strip()
                nuevo_codigo = int(nuevo_codigo_str) if nuevo_codigo_str.isdigit() else None

            with col4:
                id_tipologia = st.selectbox("ID Tipología (Permisos)", tipologias['id_perfil_tipologia'].astype(int), index=None, placeholder="Seleccione Tipología...")
                
        else:
            st.error("Faltan configurar Empresas o Tipologías en la pestaña de Configuración.")
            id_empresa, id_tipologia, nuevo_codigo = None, None, None
        
        st.subheader("3. Licencia de Conducción")
        col5, col6 = st.columns(2)
        with col5:
            tipo_licencia = st.text_input("Tipo de Licencia (Ej: C2, C3)", value=def_lic_tipo).strip().upper()
            if tipo_licencia and tipo_licencia not in ["C1", "C2", "C3"]:
                st.warning("⚠️ El tipo de licencia ingresado no es el estándar C1/C2/C3. Se guardará, pero por favor verifica.")
        with col6:
            fecha_vencimiento_licencia = st.date_input("Fecha de Vencimiento de Licencia", value=def_lic_fecha)
            
        # Determinar si es un Código Nuevo que requiere Certificación (Evento 1)
        es_codigo_nuevo = False
        if not existe:
            es_codigo_nuevo = True
        elif existe and nuevo_codigo != codigo_actual:
            es_codigo_nuevo = True
            
        if es_codigo_nuevo:
            st.subheader("4. Evento de Certificación Inicial")
            st.markdown("⚠️ Todo código nuevo exige registrar su evento de Certificación.")
            vehiculos = run_query("SELECT id_vehiculo, nombre_vehiculo FROM dim_vehiculo")
            
            evaluadores_db = run_query("SELECT DISTINCT evaluador FROM fact_eventos_operador WHERE evaluador IS NOT NULL ORDER BY evaluador")
            lista_evaluadores = evaluadores_db['evaluador'].tolist() if not evaluadores_db.empty else []
            lista_evaluadores.append("➕ OTRO (Nuevo Evaluador)")
            
            col7, col8 = st.columns(2)
            with col7:
                if not vehiculos.empty:
                    vehiculo_sel = st.selectbox("Vehículo Evaluado", vehiculos['id_vehiculo'].astype(str) + " - " + vehiculos['nombre_vehiculo'], index=None, placeholder="Seleccione Vehículo...")
                    id_vehiculo_eval = int(vehiculo_sel.split(" - ")[0]) if vehiculo_sel else None
                else:
                    st.error("Faltan vehículos.")
                    id_vehiculo_eval = None
                    
                evaluador_sel = st.selectbox("Evaluador Registrado", lista_evaluadores, index=None, placeholder="Seleccione Evaluador...")
                
                evaluador = None
                if evaluador_sel == "➕ OTRO (Nuevo Evaluador)":
                    evaluador_nuevo = st.text_input("Escribe el nombre del Nuevo Evaluador").strip().title()
                    evaluador = evaluador_nuevo if evaluador_nuevo else None
                else:
                    evaluador = evaluador_sel

            with col8:
                fecha_pru = st.date_input("Fecha de Prueba", value=None)
                fecha_cer = st.date_input("Fecha de Certificado", value=None)
                
            observacion_cert = st.text_area("Observación (Opcional)")
        
        if st.button("Guardar Operador", type="primary"):
            if not nombres or not primer_ape or not nuevo_codigo or id_empresa is None or not tipo_licencia or not fecha_vencimiento_licencia:
                st.error(f"Faltan campos obligatorios. Debug info: Nombres='{nombres}', Ape='{primer_ape}', Cod='{nuevo_codigo}', Emp='{id_empresa}', Lic='{tipo_licencia}', FecLic='{fecha_vencimiento_licencia}'")
            elif es_codigo_nuevo and (not evaluador or id_vehiculo_eval is None):
                st.error("Faltan campos obligatorios para la Certificación Inicial. Verifique el evaluador y vehículo.")
            else:
                # Validar regla de negocio: Cambio de código requiere evento 7 (Cancelación) previo
                if existe and codigo_actual and nuevo_codigo != codigo_actual:
                    evento_cancelacion = run_query("SELECT 1 FROM fact_eventos_operador WHERE id_codigo = :cod AND id_tipo_evento = 7 LIMIT 1", {"cod": codigo_actual})
                    if evento_cancelacion.empty:
                        st.error(f"❌ REGLA DE NEGOCIO: No se puede asignar el nuevo código {nuevo_codigo}. El código anterior ({codigo_actual}) aún está activo. Debe registrar un evento tipo 7 (Cancelación) para el código {codigo_actual} antes de reasignar.")
                        st.stop()
                        
                codigo_existe = run_query("SELECT id_persona FROM dim_codigo WHERE id_codigo = :cod", {"cod": nuevo_codigo})
                if not codigo_existe.empty and codigo_existe.iloc[0]['id_persona'] != cedula_input:
                    st.error(f"❌ ERROR: El código {nuevo_codigo} ya le pertenece a la cédula {codigo_existe.iloc[0]['id_persona']}.")
                else:
                    fecha_str = fecha_nac.strftime('%Y-%m-%d') if fecha_nac else None
                    fnac_str = fecha_nac.strftime('%Y-%m-%d') if fecha_nac else None
                    sa_clean = segundo_ape if segundo_ape else None
                    
                    if existe:
                        q_per = "UPDATE dim_persona SET primer_apellido = :pa, segundo_apellido = :sa, nombres = :nom, genero = :gen, fecha_de_nacimiento = :fn WHERE id_persona = :ced"
                        run_transaction(q_per, {"pa": primer_ape, "sa": sa_clean, "nom": nombres, "gen": genero, "fn": fnac_str, "ced": cedula_input})
                    else:
                        # id_persona es la cedula, no se genera un max_persona
                        q_persona = "INSERT INTO dim_persona (id_persona, nombres, primer_apellido, segundo_apellido, genero, fecha_de_nacimiento, id_vigencia, usuario_registra, fecha_registro) VALUES (:ced, :nom, :pa, :sa, :gen, :fnac, 1, :u, CURRENT_TIMESTAMP)"
                        run_transaction(q_persona, {"ced": int(cedula_input), "nom": nombres, "pa": primer_ape, "sa": sa_clean, "gen": genero, "fnac": fnac_str, "u": usuario_actual})
                    
                    if codigo_existe.empty:
                        # id_codigo es el codigo de operacion
                        q_codigo = "INSERT INTO dim_codigo (id_codigo, id_persona, id_empresa, id_perfil_tipologia, id_vigencia, usuario_registra, fecha_registro) VALUES (:cod, :per, :emp, :tip, 1, :u, CURRENT_TIMESTAMP)"
                        run_transaction(q_codigo, {"cod": int(nuevo_codigo), "per": int(cedula_input), "emp": id_empresa, "tip": id_tipologia, "u": usuario_actual})
                    else:
                        q_cod = "UPDATE dim_codigo SET id_empresa = :emp, id_perfil_tipologia = :tip WHERE id_codigo = :cod"
                        run_transaction(q_cod, {"emp": id_empresa, "tip": id_tipologia, "cod": nuevo_codigo})
                        
                    if tipo_licencia:
                        fvenc_str = fecha_vencimiento_licencia.strftime('%Y-%m-%d') if fecha_vencimiento_licencia else None
                        ultima_lic = run_query("SELECT tipo, vencimiento FROM fact_licencias WHERE id_codigo = :cod ORDER BY id_hecho_licencia DESC LIMIT 1", {"cod": nuevo_codigo})
                        
                        insertar_nueva = False
                        if ultima_lic.empty:
                            insertar_nueva = True
                        else:
                            ult_tipo = ultima_lic.iloc[0]['tipo']
                            ult_venc = str(ultima_lic.iloc[0]['vencimiento']) if pd.notna(ultima_lic.iloc[0]['vencimiento']) else None
                            if ult_tipo != tipo_licencia or ult_venc != fvenc_str:
                                insertar_nueva = True
                                
                        if insertar_nueva:
                            max_lic = run_query("SELECT COALESCE(MAX(id_hecho_licencia), 0) + 1 as n FROM fact_licencias").iloc[0]['n']
                            q_lic = "INSERT INTO fact_licencias (id_hecho_licencia, id_codigo, tipo, vencimiento, id_vigencia, usuario_registra, fecha_registro) VALUES (:id, :cod, :tipo, :venc, 1, :u, CURRENT_TIMESTAMP)"
                            run_transaction(q_lic, {"id": int(max_lic), "cod": nuevo_codigo, "tipo": tipo_licencia, "venc": fvenc_str, "u": usuario_actual})
                            
                    if es_codigo_nuevo:
                        fpru_str = fecha_pru.strftime('%Y-%m-%d') if fecha_pru else None
                        fcer_str = fecha_cer.strftime('%Y-%m-%d') if fecha_cer else None
                        max_evt = run_query("SELECT COALESCE(MAX(id_hecho_evento), 0) + 1 as n FROM fact_eventos_operador").iloc[0]['n']
                        q_evt = "INSERT INTO fact_eventos_operador (id_hecho_evento, id_codigo, id_tipo_evento, id_vehiculo_evaluado, evaluador, fecha_prueba, fecha_certificado, observacion, id_vigencia, usuario_registra, fecha_registro) VALUES (:id_e, :cod, 1, :veh, :eva, :fp, :fc, :obs, 1, :u, CURRENT_TIMESTAMP)"
                        run_transaction(q_evt, {"id_e": int(max_evt), "cod": nuevo_codigo, "veh": id_vehiculo_eval, "eva": evaluador, "fp": fpru_str, "fc": fcer_str, "obs": observacion_cert, "u": usuario_actual})
                        
                    st.success("Operador actualizado exitosamente.")
                    registrar_auditoria(st.session_state.get('usuario', 'Desconocido'), 'Edición de Operador', f'Cedula: {cedula_input}')
                    st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA
# ==========================================
with tab_masiva:
    st.markdown("Sube una plantilla de Excel con múltiples operadores.")

    @st.cache_data
    def generar_plantilla():
        import pandas as pd
        df_plantilla = pd.DataFrame(columns=[
            "cedula", "primer_apellido", "segundo_apellido", "nombres", "genero", 
            "fecha_de_nacimiento", "codigo_operacion", "id_empresa", "id_tipologia", 
            "tipo_licencia", "vencimiento_licencia", 
            "id_vehiculo_evaluado", "evaluador", "fecha_prueba", "fecha_certificado", "observacion_certificacion"
        ])
        df_plantilla.loc[0] = [123456789, "Perez", "Gomez", "Juan", "M", "1990-01-01", 10001, 1, 1, "C2", "2028-12-31", 1, "Carlos Mora", "2023-05-15", "2023-05-16", "Sin novedades"]
    
        datos_instrucciones = [
            ["cedula", "SÍ", "Número de documento sin puntos ni comas."],
            ["primer_apellido", "SÍ", "Primer apellido del operador."],
            ["segundo_apellido", "NO", "Segundo apellido (opcional)."],
            ["nombres", "SÍ", "Nombres completos."],
            ["genero", "SÍ", "M (Masculino), F (Femenino), u OTRO."],
            ["fecha_de_nacimiento", "NO", "Formato AAAA-MM-DD."],
            ["codigo_operacion", "SÍ", "Número de código asignado al operador."],
            ["id_empresa", "SÍ", "ID de la empresa (Ver Pestaña Configuración)."],
            ["id_tipologia", "SÍ", "ID de la tipología (Ver Pestaña Configuración)."],
            ["tipo_licencia", "SÍ", "Tipo de licencia (Ej: C2, C3)."],
            ["vencimiento_licencia", "SÍ", "Fecha de vencimiento en formato AAAA-MM-DD."],
            ["id_vehiculo_evaluado", "CONDICIONAL", "OBLIGATORIO si es un operador o código nuevo."],
            ["evaluador", "CONDICIONAL", "OBLIGATORIO si es un código nuevo."],
            ["fecha_prueba", "CONDICIONAL", "OBLIGATORIO si es un código nuevo. Formato AAAA-MM-DD."],
            ["fecha_certificado", "CONDICIONAL", "OBLIGATORIO si es un código nuevo. Formato AAAA-MM-DD."],
            ["observacion_certificacion", "NO", "Observaciones de la certificación (Opcional)."]
        ]
        df_instrucciones = pd.DataFrame(datos_instrucciones, columns=["Nombre Columna", "Es Obligatoria", "Instrucción de Llenado"])
    
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_plantilla.to_excel(writer, index=False, sheet_name='Operadores')
            df_instrucciones.to_excel(writer, index=False, sheet_name='Instrucciones', startrow=0, startcol=0)
        return output.getvalue()

    st.download_button(
        label="📥 Descargar Plantilla Excel Multi-Hoja",
        data=generar_plantilla(),
        file_name="Plantilla_Operadores_Maestra.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    archivo_subido = st.file_uploader("Sube el archivo diligenciado (Excel)", type=["xlsx"], key="upload_ops")

    if archivo_subido:
        try:
            df_up = pd.read_excel(archivo_subido, sheet_name="Operadores")
            st.write("🔍 **Vista Previa de los Datos Subidos:**")
        
            df_up['Estado'] = ""
            df_up['Validacion'] = "🟢 OK"
        
            for index, row in df_up.iterrows():
                ced = clean_int(row.get('cedula'))
                cod = clean_int(row.get('codigo_operacion'))
                emp = clean_int(row.get('id_empresa'))
                tip = clean_int(row.get('id_tipologia'))
                pa = clean_text(row.get('primer_apellido'))
                nom = clean_text(row.get('nombres'))
            
                veh = clean_int(row.get('id_vehiculo_evaluado'))
                eva = clean_text(row.get('evaluador'))
            
                if ced == "INVALID" or ced is None:
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Cédula inválida o vacía"
                    continue
                if cod == "INVALID" or cod is None:
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Código inválido o vacío"
                    continue
                if emp == "INVALID" or emp is None or tip == "INVALID" or tip is None:
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Empresa/Tipología inválidos"
                    continue
                if not pa or not nom:
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Nombre/Primer Apellido vacíos"
                    continue
                
                tipo_lic_raw = row.get('tipo_licencia')
                venc_lic_raw = row.get('vencimiento_licencia')
                if pd.isna(tipo_lic_raw) or str(tipo_lic_raw).strip() == "" or pd.isna(venc_lic_raw):
                    df_up.at[index, 'Validacion'] = "🔴 ERROR: Tipo y Vencimiento de Licencia obligatorios"
                    continue
            
                es_codigo_nuevo = False
                p_existe = run_query("SELECT 1 FROM dim_persona WHERE id_persona = :ced", {"ced": ced})
            
                if not p_existe.empty:
                    df_up.at[index, 'Estado'] = "🟡 EXISTE (Se actualizará)"
                    q_cod = "SELECT id_codigo FROM dim_codigo WHERE id_persona = :ced AND id_vigencia = 1 AND id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7) ORDER BY fecha_registro DESC LIMIT 1"
                    cod_actual_db = run_query(q_cod, {"ced": ced})
                    if not cod_actual_db.empty:
                        cod_activo = int(cod_actual_db.iloc[0]['id_codigo'])
                        if cod != cod_activo:
                            es_codigo_nuevo = True
                            evento_cancel = run_query("SELECT 1 FROM fact_eventos_operador WHERE id_codigo = :cod_old AND id_tipo_evento = 7 LIMIT 1", {"cod_old": cod_activo})
                            if evento_cancel.empty:
                                df_up.at[index, 'Validacion'] = f"🔴 ERROR: El código anterior {cod_activo} no tiene evento 7 (Cancelación)."
                                continue
                else:
                    df_up.at[index, 'Estado'] = "✨ NUEVO"
                    es_codigo_nuevo = True
                
                if es_codigo_nuevo:
                    if veh == "INVALID" or veh is None or not eva:
                        df_up.at[index, 'Validacion'] = "🔴 ERROR: Es un código nuevo, requiere id_vehiculo_evaluado y evaluador."
                        continue
                
                c_existe = run_query("SELECT id_persona FROM dim_codigo WHERE id_codigo = :cod", {"cod": cod})
                if not c_existe.empty and c_existe.iloc[0]['id_persona'] != ced:
                    df_up.at[index, 'Validacion'] = f"🔴 ERROR: Código usado por cédula {c_existe.iloc[0]['id_persona']}"
        
            st.dataframe(df_up, use_container_width=True)
            hay_errores = any("🔴" in val for val in df_up['Validacion'])
        
            if hay_errores:
                st.error("Corrige los errores marcados en rojo en tu Excel y vuelve a subir el archivo.")
            else:
                st.info("💡 Haz clic en 'Procesar Carga' para guardar todos los registros verdes y amarillos.")
                if st.button("🚀 Procesar Carga Masiva"):
                    exitosos = 0
                    for index, row in df_up.iterrows():
                        ced = clean_int(row['cedula'])
                        pa = clean_text(row['primer_apellido'])
                        sa = clean_text(row['segundo_apellido'])
                        nom = clean_text(row['nombres'])
                        gen = str(row['genero']).strip().upper() if pd.notna(row['genero']) else "OTRO"
                    
                        fec = row['fecha_de_nacimiento']
                        try:
                            fecha_str = pd.to_datetime(fec).strftime('%Y-%m-%d') if pd.notna(fec) else None
                        except:
                            fecha_str = None
                        
                        cod = clean_int(row['codigo_operacion'])
                        emp = clean_int(row['id_empresa'])
                        tip = clean_int(row['id_tipologia'])
                        estado = row['Estado']
                    
                        es_codigo_nuevo = True if "NUEVO" in estado else False
                        if not es_codigo_nuevo:
                            q_cod = "SELECT id_codigo FROM dim_codigo WHERE id_persona = :ced AND id_vigencia = 1 AND id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7) ORDER BY fecha_registro DESC LIMIT 1"
                            c_act = run_query(q_cod, {"ced": ced})
                            if not c_act.empty and int(c_act.iloc[0]['id_codigo']) != cod:
                                es_codigo_nuevo = True
                    
                        if "NUEVO" in estado:
                            # id_persona es la cedula
                            q_per = "INSERT INTO dim_persona (id_persona, nombres, primer_apellido, segundo_apellido, genero, fecha_de_nacimiento, id_vigencia, usuario_registra, fecha_registro) VALUES (:ced, :nom, :pa, :sa, :gen, :fn, 1, :u, CURRENT_TIMESTAMP)"
                            run_transaction(q_per, {"ced": int(ced), "pa": pa, "sa": sa, "nom": nom, "gen": gen, "fn": fecha_str, "u": usuario_actual})
                        else:
                            q_per = "UPDATE dim_persona SET primer_apellido = :pa, segundo_apellido = :sa, nombres = :nom, genero = :gen, fecha_de_nacimiento = :fn WHERE id_persona = :ced"
                            run_transaction(q_per, {"pa": pa, "sa": sa, "nom": nom, "gen": gen, "fn": fecha_str, "ced": ced})
                        
                        c_existe = run_query("SELECT 1 FROM dim_codigo WHERE id_codigo = :cod", {"cod": cod})
                        if c_existe.empty:
                            # id_codigo es el codigo
                            q_cod = "INSERT INTO dim_codigo (id_codigo, id_persona, id_empresa, id_perfil_tipologia, id_vigencia, usuario_registra, fecha_registro) VALUES (:cod, :ced, :emp, :tip, 1, :u, CURRENT_TIMESTAMP)"
                            run_transaction(q_cod, {"cod": int(cod), "ced": int(ced), "emp": emp, "tip": tip, "u": usuario_actual})
                        else:
                            q_cod = "UPDATE dim_codigo SET id_empresa = :emp, id_perfil_tipologia = :tip WHERE id_codigo = :cod"
                            run_transaction(q_cod, {"emp": emp, "tip": tip, "cod": cod})
                        
                        tipo_lic_raw = row.get('tipo_licencia')
                        venc_lic_raw = row.get('vencimiento_licencia')
                    
                        if pd.notna(tipo_lic_raw) and str(tipo_lic_raw).strip() != "":
                            tipo_lic = str(tipo_lic_raw).strip().upper()
                            try:
                                venc_lic_str = pd.to_datetime(venc_lic_raw).strftime('%Y-%m-%d') if pd.notna(venc_lic_raw) else None
                            except:
                                venc_lic_str = None
                        
                            ultima_lic = run_query("SELECT tipo, vencimiento FROM fact_licencias WHERE id_codigo = :cod ORDER BY id_hecho_licencia DESC LIMIT 1", {"cod": cod})
                        
                            insertar_nueva = False
                            if ultima_lic.empty:
                                insertar_nueva = True
                            else:
                                ult_tipo = ultima_lic.iloc[0]['tipo']
                                ult_venc = str(ultima_lic.iloc[0]['vencimiento']) if pd.notna(ultima_lic.iloc[0]['vencimiento']) else None
                                if ult_tipo != tipo_lic or ult_venc != venc_lic_str:
                                    insertar_nueva = True
                                
                            if insertar_nueva:
                                max_lic = run_query("SELECT COALESCE(MAX(id_hecho_licencia), 0) + 1 as n FROM fact_licencias").iloc[0]['n']
                                q_lic = "INSERT INTO fact_licencias (id_hecho_licencia, id_codigo, tipo, vencimiento, id_vigencia, usuario_registra, fecha_registro) VALUES (:id_l, :cod, :tipo, :venc, 1, :u, CURRENT_TIMESTAMP)"
                                run_transaction(q_lic, {"id_l": int(max_lic), "cod": cod, "tipo": tipo_lic, "venc": venc_lic_str, "u": usuario_actual})
                            
                        if es_codigo_nuevo:
                            veh = clean_int(row.get('id_vehiculo_evaluado'))
                            eva = clean_text(row.get('evaluador'))
                            observacion_cert = clean_text(row.get('observacion_certificacion'))
                            fp_raw = row.get('fecha_prueba')
                            fc_raw = row.get('fecha_certificado')
                        
                            try:
                                fp_str = pd.to_datetime(fp_raw).strftime('%Y-%m-%d') if pd.notna(fp_raw) else None
                            except:
                                fp_str = None
                            
                            try:
                                fc_str = pd.to_datetime(fc_raw).strftime('%Y-%m-%d') if pd.notna(fc_raw) else None
                            except:
                                fc_str = None
                            
                            max_evt = run_query("SELECT COALESCE(MAX(id_hecho_evento), 0) + 1 as n FROM fact_eventos_operador").iloc[0]['n']
                            q_evt = "INSERT INTO fact_eventos_operador (id_hecho_evento, id_codigo, id_tipo_evento, id_vehiculo_evaluado, evaluador, fecha_prueba, fecha_certificado, observacion, id_vigencia, usuario_registra, fecha_registro) VALUES (:id_e, :cod, 1, :veh, :eva, :fp, :fc, :obs, 1, :u, CURRENT_TIMESTAMP)"
                            run_transaction(q_evt, {"id_e": int(max_evt), "cod": cod, "veh": veh, "eva": eva, "fp": fp_str, "fc": fc_str, "obs": observacion_cert, "u": usuario_actual})
                        
                        exitosos += 1
                    
                    st.success(f"Carga exitosa! Se actualizaron {len(df_up)} operadores en la base de datos.")
                    registrar_auditoria(st.session_state.get('usuario', 'Desconocido'), 'Carga Masiva de Operadores', f'Registros actualizados: {len(df_up)}')
                    st.balloons()
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
