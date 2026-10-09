import streamlit as st
import pandas as pd
import io
from db import run_query, run_transaction, registrar_auditoria
usuario_actual = st.session_state.get('usuario', 'Usuario')

def fecha_a_date(v):
    """Convierte un valor de fecha (texto) a datetime.date o None, robusto a formatos y timestamps."""
    if v is None or pd.isna(v):
        return None
    try:
        dt = pd.to_datetime(str(v).strip(), dayfirst=False, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None

st.title(" Reporte de Comportamientos")
st.markdown("""<style>input[type=number]::-webkit-outer-spin-button,input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}input[type=number]{-moz-appearance:textfield}</style>""",unsafe_allow_html=True)

tab_manual, tab_masiva, tab_reinc = st.tabs([" Ingreso Individual", "Carga Masiva (Excel)", " Reincidencia"])

with tab_manual:
    st.markdown("Busca un operador por **Cédula** o **Código** para registrarle un comportamiento.")
    busqueda_str = st.text_input("Buscar por Cédula o Código", key="busqueda_comp").strip()
    busqueda = int(busqueda_str) if busqueda_str and busqueda_str.isdigit() else None
    if busqueda:
        bus_str = str(int(busqueda))
        if len(bus_str) <= 5:
            q = "SELECT id_persona, id_codigo FROM dim_codigo WHERE id_codigo = :n AND id_vigencia = 1 LIMIT 1"
            cods = run_query(q, {"n": busqueda})
            if cods.empty:
                st.error(" No se encontró código activo."); st.stop()
            codigo = int(cods.iloc[0]['id_codigo'])
            cedula = int(cods.iloc[0]['id_persona'])
        else:
            cedula = busqueda
            q = "SELECT id_codigo FROM dim_codigo WHERE id_persona = :n AND id_vigencia = 1 ORDER BY fecha_registro DESC LIMIT 1"
            cods = run_query(q, {"n": cedula})
            if cods.empty:
                st.error(" El operador no tiene código activo."); st.stop()
            codigo = int(cods.iloc[0]['id_codigo'])
        persona = run_query("SELECT nombres, primer_apellido FROM dim_persona WHERE id_persona = :c", {"c": cedula})
        nom = persona.iloc[0] if not persona.empty else None
        if nom is not None:
            st.info(f" **Operador:** {nom['nombres']} {nom['primer_apellido']} | **Cédula:** {cedula} | **Código:** {codigo}")
        st.subheader("1. Seleccionar Comportamiento")
        descs = run_query("SELECT id_jerarquia, descripcion_comportamiento FROM dim_detalle_comportamiento ORDER BY descripcion_comportamiento")
        desc_opts = {str(r['id_jerarquia']): r['descripcion_comportamiento'] for _, r in descs.iterrows()}
        desc_sel = st.selectbox("Comportamiento", list(desc_opts.keys()), format_func=lambda x: desc_opts[x], key="desc_comp")
        jerarquia_id = int(desc_sel) if desc_sel else None
        if jerarquia_id:
            st.caption(f"Seleccionado: {desc_opts[desc_sel]}")
            with st.form("form_comportamiento"):
                st.subheader("2. Detalles del Evento")
                col1, col2 = st.columns(2)
                with col1:
                    f_evento = st.date_input("Fecha del Evento", value=None)
                    h_evento = st.time_input("Hora del Evento", value=None)
                    vehiculo = st.number_input("Vehículo (MC)", min_value=0, step=1, value=None, key="vehiculo_comp")
                    viaje = st.number_input("Viaje", min_value=0, step=1, value=None, key="viaje_comp")
                with col2:
                    tarea = st.number_input("Tarea", min_value=0, step=1, value=None, key="tarea_comp")
                    ruta = st.text_input("Ruta")
                    sitio_salida = st.text_input("Sitio de Salida")
                    sitio_novedad = st.text_input("Sitio de Novedad")
                caso = st.text_input("Caso / Ticket / Bitácora")
                nota = st.text_area("Nota / Descripción")
                col3, col4 = st.columns(2)
                with col3:
                    num_les = st.number_input("Número de Lesionados", min_value=0, step=1, value=None, key="num_les_comp")
                    obs_conc = st.text_area("Observación Concesionario")
                with col4:
                    resp_mc = st.text_area("Respuesta Metrocali")
                    resp_pqrs = st.text_input("Responsable PQRS/COT")
                submit = st.form_submit_button(" Guardar Comportamiento")
                if submit and f_evento:
                    params = {
                        "id_jerarquia": jerarquia_id,
                        "caso": caso,
                        "fecha": f_evento.strftime('%Y-%m-%d'),
                        "hora": h_evento.strftime('%H:%M:%S') if h_evento else None,
                        "nota": nota,
                        "vehiculo": vehiculo,
                        "viaje": viaje,
                        "tarea": tarea,
                        "codigo": codigo,
                        "ruta": ruta,
                        "sitio_salida": sitio_salida,
                        "sitio_novedad": sitio_novedad,
                        "num_les": num_les,
                        "obs_conc": obs_conc,
                        "resp_mc": resp_mc,
                        "resp_pqrs": resp_pqrs,
                        "usuario": usuario_actual
                    }
                    max_id = run_query("SELECT COALESCE(MAX(id_hecho_comportamiento),0)+1 as n FROM fact_comportamiento").iloc[0]['n']
                    q = """INSERT INTO fact_comportamiento 
                        (id_hecho_comportamiento, id_jerarquia, caso_bitacora_ticket, fecha_evento, hora_evento,
                        nota, vehiculo, viaje, tarea, id_codigo, ruta, sitio_salida, sitio_novedad,
                        numero_lesionados, observacion_concesionario, respuesta_mc, responsable_pqrs_cot,
                        id_vigencia, usuario_registra, fecha_registro)
                        VALUES (:id, :j, :c, :f, :h, :n, :v, :vi, :ta, :co, :r, :ss, :sn,
                        :nl, :oc, :rm, :rp, 1, :u, CURRENT_TIMESTAMP)"""
                    success, msg = run_transaction(q, {"id": int(max_id), "j": params["id_jerarquia"], "c": params["caso"], "f": params["fecha"], "h": params["hora"], "n": params["nota"], "v": params["vehiculo"], "vi": params["viaje"], "ta": params["tarea"], "co": params["codigo"], "r": params["ruta"], "ss": params["sitio_salida"], "sn": params["sitio_novedad"], "nl": params["num_les"], "oc": params["obs_conc"], "rm": params["resp_mc"], "rp": params["resp_pqrs"], "u": params["usuario"]})
                    if success:
                        registrar_auditoria(usuario_actual, 'Registro Comportamiento Manual', f'Codigo: {codigo}, Jerarquia: {jerarquia_id}')
                        st.success(" Comportamiento registrado exitosamente!")
                        st.balloons()
                    else:
                        st.error(f" Error: {msg}")

with tab_masiva:
    st.markdown("Descarga la plantilla, diligénciala y súbela para carga masiva.")
    @st.cache_data
    def generar_plantilla_comportamiento():
        inst = [
            ["id_codigo", "Obligatorio. Código de operación del operador. Ej: 10001."],
            ["descripcion_comportamiento", "Obligatorio. Texto exacto de la jerarquía (columna descripcion_comportamiento). El sistema asigna el id_jerarquia automáticamente."],
            ["fecha_evento", "Obligatorio. Formato DD/MM/AAAA o AAAA-MM-DD."],
            ["caso_bitacora_ticket", "Opcional. Número de caso/ticket. Si existe, se actualiza el registro."],
            ["nota", "Opcional. Descripción del evento."],
            ["hora_evento", "Opcional. Formato HH:MM:SS."],
            ["vehiculo", "Opcional. Número MC del vehículo."],
            ["viaje", "Opcional."],
            ["tarea", "Opcional."],
            ["ruta", "Opcional."],
            ["sitio_salida", "Opcional."],
            ["sitio_novedad", "Opcional."],
            ["numero_lesionados", "Opcional."],
            ["observacion_concesionario", "Opcional."],
            ["respuesta_mc", "Opcional."],
            ["responsable_pqrs_cot", "Opcional."],
            ["direccion_infraccion", "Opcional."],
            ["clase_servicio", "Opcional."],
            ["tipo_servicio", "Opcional."],
            ["fuente_infraccion", "Opcional."],
            ["placa", "Opcional."]
        ]
        df_inst = pd.DataFrame(inst, columns=["Campo", "Instrucción"])
        df_data = pd.DataFrame(columns=["id_codigo", "descripcion_comportamiento", "fecha_evento", "caso_bitacora_ticket", "nota", "hora_evento", "vehiculo", "viaje", "tarea", "ruta", "sitio_salida", "sitio_novedad", "numero_lesionados", "observacion_concesionario", "respuesta_mc", "responsable_pqrs_cot", "direccion_infraccion", "clase_servicio", "tipo_servicio", "fuente_infraccion", "placa"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_inst.to_excel(writer, index=False, sheet_name='INSTRUCCIONES')
            df_data.to_excel(writer, index=False, sheet_name='DATOS')
        return output.getvalue()
    st.download_button(" Descargar Plantilla", data=generar_plantilla_comportamiento(), file_name="Plantilla_Comportamientos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("---")
    archivo = st.file_uploader("Sube el Excel diligenciado", type=["xlsx"])
    if archivo:
        try:
            df = pd.read_excel(archivo, sheet_name='DATOS')
            st.write(" Vista previa:")
            df['validacion'] = ""
            df['id_jerarquia_int'] = None
            df['id_existente'] = None
            for i, row in df.iterrows():
                cod_raw = row.get('id_codigo')
                if pd.isna(cod_raw):
                    df.at[i, 'validacion'] = " id_codigo vacío"
                    continue
                try:
                    cod_val = int(float(cod_raw))
                except:
                    df.at[i, 'validacion'] = " id_codigo inválido"
                    continue
                qc = "SELECT id_codigo FROM dim_codigo WHERE id_codigo = :c AND id_vigencia = 1 LIMIT 1"
                cods = run_query(qc, {"c": cod_val})
                if cods.empty:
                    df.at[i, 'validacion'] = " Código no existe o está inactivo"
                    continue
                df.at[i, 'id_codigo_int'] = int(cods.iloc[0]['id_codigo'])
                desc = row.get('descripcion_comportamiento')
                if pd.isna(desc) or not str(desc).strip():
                    df.at[i, 'validacion'] = " descripcion_comportamiento vacía"
                    continue
                qd = "SELECT id_jerarquia FROM dim_detalle_comportamiento WHERE descripcion_comportamiento = :d LIMIT 1"
                dets = run_query(qd, {"d": str(desc).strip()})
                if dets.empty:
                    df.at[i, 'validacion'] = " descripcion_comportamiento no encontrada"
                    continue
                df.at[i, 'id_jerarquia_int'] = int(dets.iloc[0]['id_jerarquia'])
                fec = row.get('fecha_evento')
                if pd.isna(fec):
                    df.at[i, 'validacion'] = " fecha_evento vacía"
                    continue
                caso = row.get('caso_bitacora_ticket')
                if pd.notna(caso) and str(caso).strip():
                    qcaso = "SELECT id_hecho_comportamiento FROM fact_comportamiento WHERE caso_bitacora_ticket = :c LIMIT 1"
                    existente = run_query(qcaso, {"c": str(caso).strip()})
                    if not existente.empty:
                        df.at[i, 'id_existente'] = int(existente.iloc[0]['id_hecho_comportamiento'])
                        df.at[i, 'validacion'] = " Ya existe - se actualizará"
                        continue
                df.at[i, 'validacion'] = " Nuevo"
            st.dataframe(df, use_container_width=True)
            errores = [v for v in df['validacion'] if v.startswith(" id_codigo") or v.startswith(" Código") or v.startswith(" descripcion") or v.startswith(" fecha")]
            dupes = [v for v in df['validacion'] if v == " Ya existe - se actualizará"]
            nuevos = [v for v in df['validacion'] if v == " Nuevo"]
            if errores:
                st.error(f"Corrige los errores ({len(errores)} filas) y vuelve a subir.")
            else:
                if dupes:
                    st.warning(f"Se actualizarán {len(dupes)} registros existentes (mismo caso_bitacora_ticket).")
                st.info(f"**{len(nuevos)}** nuevos + **{len(dupes)}** actualizaciones = **{len(nuevos)+len(dupes)}** total")
                if st.button(" Procesar Carga"):
                    exitosos = 0; actualizados = 0
                    for i, row in df.iterrows():
                        def gd(c):
                            v = row.get(c)
                            return pd.to_datetime(v).strftime('%Y-%m-%d') if pd.notna(v) else None
                        def gn(c):
                            v = row.get(c)
                            return int(float(v)) if pd.notna(v) else None
                        def gt(c):
                            v = row.get(c)
                            return str(v).strip() if pd.notna(v) and str(v).strip() else None
                        params = {
                            "j": int(row['id_jerarquia_int']), "cod": int(row['id_codigo_int']),
                            "f": gd('fecha_evento'), "h": gd('hora_evento'), "n": gt('nota'),
                            "v": gn('vehiculo'), "vi": gn('viaje'), "ta": gn('tarea'),
                            "caso": gt('caso_bitacora_ticket'), "r": gt('ruta'),
                            "ss": gt('sitio_salida'), "sn": gt('sitio_novedad'), "nl": gn('numero_lesionados'),
                            "oc": gt('observacion_concesionario'), "rmc": gt('respuesta_mc'),
                            "rpqrs": gt('responsable_pqrs_cot'), "dir": gt('direccion_infraccion'),
                            "cs": gt('clase_servicio'), "ts": gt('tipo_servicio'), "fi": gt('fuente_infraccion'),
                            "pl": gt('placa'), "u": usuario_actual
                        }
                        if row['id_existente'] is not None:
                            params["id_hecho"] = int(row['id_existente'])
                            q = """UPDATE fact_comportamiento SET id_jerarquia=:j, id_codigo=:cod, 
                                fecha_evento=:f, hora_evento=:h, nota=:n, vehiculo=:v, viaje=:vi, tarea=:ta,
                                caso_bitacora_ticket=:caso, ruta=:r, sitio_salida=:ss, sitio_novedad=:sn,
                                numero_lesionados=:nl, observacion_concesionario=:oc, respuesta_mc=:rmc,
                                responsable_pqrs_cot=:rpqrs, direccion_infraccion=:dir, clase_servicio=:cs,
                                tipo_servicio=:ts, fuente_infraccion=:fi, placa=:pl, usuario_registra=:u
                                WHERE id_hecho_comportamiento=:id_hecho"""
                            run_transaction(q, params)
                            actualizados += 1
                        else:
                            max_id = run_query("SELECT COALESCE(MAX(id_hecho_comportamiento),0)+1 as n FROM fact_comportamiento").iloc[0]['n']
                            params["id"] = int(max_id)
                            q = """INSERT INTO fact_comportamiento 
                                (id_hecho_comportamiento, id_jerarquia, id_codigo, fecha_evento, hora_evento,
                                nota, vehiculo, viaje, tarea, caso_bitacora_ticket, ruta,
                                sitio_salida, sitio_novedad, numero_lesionados, observacion_concesionario,
                                respuesta_mc, responsable_pqrs_cot, direccion_infraccion, clase_servicio,
                                tipo_servicio, fuente_infraccion, placa,
                                id_vigencia, usuario_registra, fecha_registro)
                                VALUES (:id, :j, :cod, :f, :h, :n, :v, :vi, :ta, :caso, :r,
                                :ss, :sn, :nl, :oc, :rmc, :rpqrs, :dir, :cs, :ts, :fi, :pl,
                                1, :u, CURRENT_TIMESTAMP)"""
                            run_transaction(q, params)
                            exitosos += 1
                    registrar_auditoria(usuario_actual, 'Carga Masiva Comportamientos', f'Nuevos: {exitosos}, Actualizados: {actualizados}')
                    st.success(f" {exitosos} nuevos insertados, {actualizados} actualizados!")
                    st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab_reinc:
    st.markdown("###  Reincidencia de Comportamientos")
    st.markdown("Evalúa si un operador ha incurrido en comportamientos reincidentes según las reglas de impacto.")
    
    if st.button(" Evaluar Reincidencia", type="primary"):
        with st.spinner("Analizando comportamientos..."):
            impactos = run_query("SELECT id_impacto, impacto, maximo, dias_maximo FROM dim_impacto WHERE maximo > 0 ORDER BY id_impacto")
            nuevos_casos = 0
            for _, imp in impactos.iterrows():
                imp_id = imp['id_impacto']
                imp_nom = imp['impacto']
                maximo = int(imp['maximo'])
                dias_max = int(imp['dias_maximo'])
                comps = run_query("SELECT id_comportamiento, comportamiento FROM dim_comportamiento WHERE id_impacto = :i", {"i": imp_id})
                for _, comp in comps.iterrows():
                    comp_id = comp['id_comportamiento']
                    codigos = run_query("""
                        SELECT DISTINCT f.id_codigo FROM fact_comportamiento f
                        JOIN dim_detalle_comportamiento d ON f.id_jerarquia = d.id_jerarquia
                        WHERE d.id_comportamiento = :c
                        AND f.fecha_evento IS NOT NULL AND f.fecha_evento::date >= CURRENT_DATE - INTERVAL '7 months'
                        AND f.id_codigo IS NOT NULL
                        AND f.id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)
                        AND f.id_hecho_comportamiento NOT IN (SELECT id_hecho_comportamiento FROM reincidencia_detalle)
                    """, {"c": comp_id})
                    for _, cod_row in codigos.iterrows():
                        cod = int(cod_row['id_codigo'])
                        hechos = run_query("""
                            SELECT f.id_hecho_comportamiento, f.fecha_evento, f.caso_bitacora_ticket, f.hora_evento, f.vehiculo, f.fuente_infraccion, f.responsable_pqrs_cot, f.id_jerarquia
                            FROM fact_comportamiento f
                            JOIN dim_detalle_comportamiento d ON f.id_jerarquia = d.id_jerarquia
                            WHERE d.id_comportamiento = :c AND f.id_codigo = :cod
                            AND f.fecha_evento IS NOT NULL AND f.fecha_evento::date >= CURRENT_DATE - INTERVAL '7 months'
                            AND f.id_hecho_comportamiento NOT IN (SELECT id_hecho_comportamiento FROM reincidencia_detalle)
                            ORDER BY f.fecha_evento
                        """, {"c": comp_id, "cod": cod})
                        if hechos.empty:
                            continue
                        if imp_nom.lower() == 'grave':
                            for _, row in hechos.iterrows():
                                max_r = run_query("SELECT COALESCE(MAX(id_reincidencia),0)+1 as n FROM fact_reincidencia").iloc[0]['n']
                                caso_v = row['caso_bitacora_ticket']
                                if pd.notna(caso_v):
                                    s = str(caso_v).strip()
                                    caso_str = str(int(float(s))) if s.replace('.','').replace('-','').isdigit() else s
                                else:
                                    caso_str = 'N/A'
                                resumen = f"Caso: {caso_str} | Fecha: {row['fecha_evento']} | Hora: {row['hora_evento'] or 'N/A'}"
                                run_transaction("INSERT INTO fact_reincidencia (id_reincidencia,id_impacto,id_comportamiento,id_codigo,fecha_inicio,fecha_fin,cantidad,resumen,usuario_registra) VALUES (:id,:i,:c,:co,:fi,:ff,1,:r,:u)", {"id":int(max_r),"i":int(imp_id),"c":int(comp_id),"co":cod,"fi":fecha_a_date(row['fecha_evento']),"ff":fecha_a_date(row['fecha_evento']),"r":resumen,"u":usuario_actual})
                                run_transaction("INSERT INTO reincidencia_detalle (id_reincidencia,id_hecho_comportamiento) VALUES (:r,:h)", {"r":int(max_r),"h":int(row['id_hecho_comportamiento'])})
                                nuevos_casos += 1
                        else:
                            pares = []
                            for i in range(len(hechos)-1):
                                for j in range(i+1, len(hechos)):
                                    fi = pd.to_datetime(hechos.iloc[i]['fecha_evento'])
                                    fj = pd.to_datetime(hechos.iloc[j]['fecha_evento'])
                                    if fi and fj and (fj - fi).days <= dias_max:
                                        ids_par = sorted([int(hechos.iloc[i]['id_hecho_comportamiento']), int(hechos.iloc[j]['id_hecho_comportamiento'])])
                                        pares.append(ids_par)
                            creados = run_query("SELECT array_agg(id_hecho_comportamiento ORDER BY id_hecho_comportamiento) as ids FROM reincidencia_detalle GROUP BY id_reincidencia")
                            ids_creados = set()
                            if not creados.empty:
                                for _, cr in creados.iterrows():
                                    ids_creados.add(tuple(cr['ids']))
                            for par in pares:
                                if tuple(par) in ids_creados:
                                    continue
                                max_r = run_query("SELECT COALESCE(MAX(id_reincidencia),0)+1 as n FROM fact_reincidencia").iloc[0]['n']
                                r1 = hechos[hechos['id_hecho_comportamiento']==par[0]].iloc[0]
                                r2 = hechos[hechos['id_hecho_comportamiento']==par[1]].iloc[0]
                                def fmt_caso(v):
                                    if pd.notna(v):
                                        s = str(v).strip()
                                        return str(int(float(s))) if s.replace('.','').replace('-','').isdigit() else s
                                    return 'N/A'
                                resumen = f"1) Caso:{fmt_caso(r1['caso_bitacora_ticket'])} Fecha:{r1['fecha_evento']} | 2) Caso:{fmt_caso(r2['caso_bitacora_ticket'])} Fecha:{r2['fecha_evento']}"
                                run_transaction("INSERT INTO fact_reincidencia (id_reincidencia,id_impacto,id_comportamiento,id_codigo,fecha_inicio,fecha_fin,cantidad,resumen,usuario_registra) VALUES (:id,:i,:c,:co,:fi,:ff,2,:r,:u)", {"id":int(max_r),"i":int(imp_id),"c":int(comp_id),"co":cod,"fi":fecha_a_date(r1['fecha_evento']),"ff":fecha_a_date(r2['fecha_evento']),"r":resumen,"u":usuario_actual})
                                run_transaction("INSERT INTO reincidencia_detalle (id_reincidencia,id_hecho_comportamiento) VALUES (:r,:h1),(:r,:h2)", {"r":int(max_r),"h1":par[0],"h2":par[1]})
                                nuevos_casos += 1
            if nuevos_casos:
                st.success(f" {nuevos_casos} casos de reincidencia generados!")
                st.balloons()
            else:
                st.info("No se encontraron nuevos casos de reincidencia.")
    
    st.markdown("---")
    st.markdown("###  Detalle de Casos")

    empresas = run_query("SELECT id_empresa, nombre_empresa FROM dim_empresa ORDER BY nombre_empresa")
    emp_opts = ["Todas"] + empresas['nombre_empresa'].tolist()

    reincidencias = run_query("""
        SELECT r.id_reincidencia, r.id_codigo, e.nombre_empresa, i.impacto, c.comportamiento,
               r.fecha_inicio, r.fecha_fin, r.cantidad, r.determinacion_mc, r.estado,
               r.id_hecho_evento, r.usuario_registra
        FROM fact_reincidencia r
        LEFT JOIN dim_impacto i ON r.id_impacto = i.id_impacto
        LEFT JOIN dim_comportamiento c ON r.id_comportamiento = c.id_comportamiento
        LEFT JOIN dim_codigo dc ON r.id_codigo = dc.id_codigo
        LEFT JOIN dim_empresa e ON dc.id_empresa = e.id_empresa
        ORDER BY r.id_reincidencia DESC
    """)
    if not reincidencias.empty:
        caso_filtro = st.selectbox("Filtrar por Caso", ["Todos"] + reincidencias['id_reincidencia'].astype(str).tolist(), key="reinc_caso")
        cod_opts = ["Todos"] + sorted(reincidencias['id_codigo'].dropna().astype(int).astype(str).unique().tolist())
        cod_filtro = st.selectbox("Filtrar por Código", cod_opts, key="reinc_cod")
        emp_filtro = st.selectbox("Filtrar por Empresa", emp_opts, key="reinc_emp")
        if caso_filtro != "Todos":
            reincidencias = reincidencias[reincidencias['id_reincidencia'].astype(str) == caso_filtro]
        if cod_filtro != "Todos":
            reincidencias = reincidencias[reincidencias['id_codigo'].astype(int).astype(str) == cod_filtro]
        if emp_filtro != "Todas":
            reincidencias = reincidencias[reincidencias['nombre_empresa'] == emp_filtro]
        
        detalle_all = run_query("""
            SELECT r.id_reincidencia, r.id_codigo, e.nombre_empresa, i.impacto, c.comportamiento,
                   r.fecha_inicio, r.fecha_fin, r.determinacion_mc,
                   d.descripcion_comportamiento, f.caso_bitacora_ticket, f.fecha_evento,
                   f.vehiculo, f.viaje, f.tarea, f.hora_evento, f.ruta,
                   f.clase_servicio, f.tipo_servicio, f.fuente_infraccion, f.placa
            FROM reincidencia_detalle rd
            JOIN fact_reincidencia r ON rd.id_reincidencia = r.id_reincidencia
            JOIN fact_comportamiento f ON rd.id_hecho_comportamiento = f.id_hecho_comportamiento
            JOIN dim_detalle_comportamiento d ON f.id_jerarquia = d.id_jerarquia
            LEFT JOIN dim_impacto i ON r.id_impacto = i.id_impacto
            LEFT JOIN dim_comportamiento c ON r.id_comportamiento = c.id_comportamiento
            LEFT JOIN dim_codigo dc ON r.id_codigo = dc.id_codigo
            LEFT JOIN dim_empresa e ON dc.id_empresa = e.id_empresa
            ORDER BY r.id_reincidencia DESC
        """)
        if not detalle_all.empty and emp_filtro != "Todas":
            detalle_all = detalle_all[detalle_all['nombre_empresa'] == emp_filtro]
        
        if not detalle_all.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                detalle_all.to_excel(writer, index=False, sheet_name='Detalle Reincidencia')
            st.download_button("⬇️ Exportar Detalle a Excel", data=output.getvalue(),
                file_name=f"reincidencia_detalle_{emp_filtro}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="export_reinc")
        limite_casos = st.slider("Casos a mostrar", 5, min(100, len(reincidencias)), 20, key="reinc_limite")
        st.markdown(f"**{len(reincidencias)} casos** para empresa: {emp_filtro} (mostrando últimos {limite_casos})")
        casos_visibles = reincidencias.head(limite_casos)
        for _, rw in casos_visibles.iterrows():
            rid = int(rw['id_reincidencia'])
            label = f"Reincidencia #{rid} | Cod:{rw['id_codigo']} | {rw['impacto']} | {rw['comportamiento']}"
            with st.expander(label):
                col_det, col_def = st.columns([2, 1])
                with col_det:
                    detalle = detalle_all[detalle_all['id_reincidencia'] == rid][['descripcion_comportamiento','caso_bitacora_ticket','fecha_evento','vehiculo','viaje','tarea','hora_evento','ruta','clase_servicio','tipo_servicio','fuente_infraccion','placa']]
                    if not detalle.empty:
                        st.dataframe(detalle, use_container_width=True, hide_index=True)
                with col_def:
                    st.markdown("**Determinación Metrocali**")
                    actual = rw['determinacion_mc'] if pd.notna(rw['determinacion_mc']) else ""
                    opciones_mc = ["", "advertencia", "condicionamiento", "suspensión", "cancelación"]
                    nueva_det = st.selectbox("Decisión", opciones_mc,
                        index=opciones_mc.index(actual.lower()) if actual and actual.lower() in opciones_mc else 0,
                        key=f"det_mc_{rid}")
                    if nueva_det and nueva_det != actual.lower():
                        run_transaction("UPDATE fact_reincidencia SET determinacion_mc = :d WHERE id_reincidencia = :r", {"d": nueva_det, "r": rid})
                        registrar_auditoria(usuario_actual, 'Determinar Reincidencia', f"ID: {rid}, Decision: {nueva_det}")
                        st.rerun()
                    if nueva_det:
                        mapa_tipo = {"advertencia": 8, "condicionamiento": 9, "suspensión": 6, "cancelación": 7}
                        fec_def = pd.to_datetime(rw['fecha_fin']).date() if pd.notna(rw['fecha_fin']) else pd.Timestamp.today().date()
                        fecha_acc = st.date_input("Fecha de la Acción", value=fec_def, key=f"fecha_acc_{rid}")
                        st.markdown("**Comportamientos del caso (se registrarán):**")
                        det_caso = detalle_all[detalle_all['id_reincidencia'] == rid]
                        st.caption(f"{len(det_caso)} comportamiento(s): " + "; ".join(
                            f"{r['descripcion_comportamiento']} (caso {r['caso_bitacora_ticket']})" for _, r in det_caso.iterrows()))
                        evt_existente = rw['id_hecho_evento'] if pd.notna(rw['id_hecho_evento']) else None
                        if evt_existente:
                            st.warning(f"⚠️ Ya existe una acción registrada (evento #{int(evt_existente)}). Al guardar se **REEMPLAZARÁ** ese evento en el historial.")
                            lbl_btn = "🔄 Actualizar Acción en Historial"
                        else:
                            lbl_btn = "📝 Registrar Acción en Historial"
                        if st.button(lbl_btn, key=f"btn_acc_{rid}"):
                            id_tipo = mapa_tipo[nueva_det]
                            codigo_val = rw['id_codigo']
                            descs = "; ".join(f"{r['descripcion_comportamiento']} (caso {r['caso_bitacora_ticket']})" for _, r in det_caso.iterrows())
                            obs = f"{nueva_det.capitalize()} por reincidencia #{rid}: {descs}"
                            if evt_existente:
                                q = """UPDATE fact_eventos_operador SET id_tipo_evento = :tip, fecha_observacion = :f, observacion = :o WHERE id_hecho_evento = :e"""
                                ok, msg = run_transaction(q, {"tip": id_tipo, "f": fecha_acc.strftime('%Y-%m-%d'), "o": obs, "e": int(evt_existente)})
                                accion_aud = 'Actualizar Accion Reincidencia'
                            else:
                                max_evt = run_query("SELECT COALESCE(MAX(id_hecho_evento),0)+1 as n FROM fact_eventos_operador").iloc[0]['n']
                                q = """INSERT INTO fact_eventos_operador 
                                    (id_hecho_evento, id_codigo, id_tipo_evento, fecha_observacion, observacion, id_vigencia, usuario_registra, fecha_registro)
                                    VALUES (:id, :cod, :tip, :f, :o, 1, :u, CURRENT_TIMESTAMP)"""
                                ok, msg = run_transaction(q, {"id": int(max_evt), "cod": int(codigo_val), "tip": id_tipo, "f": fecha_acc.strftime('%Y-%m-%d'), "o": obs, "u": usuario_actual})
                                accion_aud = 'Registrar Accion Reincidencia'
                                if ok:
                                    run_transaction("UPDATE fact_reincidencia SET id_hecho_evento = :e WHERE id_reincidencia = :r", {"e": int(max_evt), "r": rid})
                            if ok:
                                registrar_auditoria(usuario_actual, accion_aud, f"Reinc #{rid}, Cod: {codigo_val}, {nueva_det}")
                                st.success(f"Acción '{nueva_det}' guardada en el historial del operador {codigo_val}.")
                                st.rerun()
                            else:
                                st.error(f"Error: {msg}")
    else:
        st.info("No hay casos de reincidencia registrados.")

    st.markdown("---")
    st.markdown("###  Importar Acciones (Excel)")
    @st.cache_data
    def plantilla_acciones():
        inst = [
            ["id_reincidencia", "Obligatorio. ID del caso de reincidencia."],
            ["id_codigo", "Obligatorio. Código del operador."],
            ["accion", "Obligatorio: advertencia, condicionamiento, suspensión o cancelación."],
            ["fecha_observacion", "Obligatorio. Formato AAAA-MM-DD."],
            ["observacion", "Opcional. Descripción de la acción."]
        ]
        df_inst = pd.DataFrame(inst, columns=["Campo", "Instrucción"])
        df_data = pd.DataFrame(columns=["id_reincidencia", "id_codigo", "accion", "fecha_observacion", "observacion"])
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df_inst.to_excel(writer, index=False, sheet_name='INSTRUCCIONES')
            df_data.to_excel(writer, index=False, sheet_name='DATOS')
        return out.getvalue()
    st.download_button("⬇️ Descargar Plantilla de Acciones", data=plantilla_acciones(),
        file_name="Plantilla_Acciones_Reincidencia.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_plant_acciones")
    arch_acc = st.file_uploader("Sube el Excel de acciones", type=["xlsx"], key="up_acciones")
    if arch_acc:
        try:
            df_acc = pd.read_excel(arch_acc, sheet_name='DATOS')
            st.write("Vista previa:")
            df_acc['validacion'] = ""
            df_acc['id_hecho_existente'] = None
            mapa_acc = {"advertencia": 8, "condicionamiento": 9, "suspensión": 6, "suspension": 6, "cancelación": 7, "cancelacion": 7}
            for i, row in df_acc.iterrows():
                rid = row.get('id_reincidencia')
                if pd.isna(rid):
                    df_acc.at[i, 'validacion'] = "id_reincidencia vacío"
                    continue
                try:
                    rid = int(float(rid))
                except:
                    df_acc.at[i, 'validacion'] = "id_reincidencia inválido"
                    continue
                qr = "SELECT id_codigo, id_hecho_evento FROM fact_reincidencia WHERE id_reincidencia = :r"
                reinc = run_query(qr, {"r": rid})
                if reinc.empty:
                    df_acc.at[i, 'validacion'] = "Reincidencia no existe"
                    continue
                cod = row.get('id_codigo')
                if pd.isna(cod) or int(float(cod)) != int(reinc.iloc[0]['id_codigo']):
                    df_acc.at[i, 'validacion'] = "id_codigo no coincide con la reincidencia"
                    continue
                acc = str(row.get('accion')).strip().lower() if pd.notna(row.get('accion')) else ""
                if acc not in mapa_acc:
                    df_acc.at[i, 'validacion'] = "Acción inválida"
                    continue
                if pd.isna(row.get('fecha_observacion')):
                    df_acc.at[i, 'validacion'] = "Falta fecha"
                    continue
                evt_exist = reinc.iloc[0]['id_hecho_evento']
                if pd.notna(evt_exist):
                    df_acc.at[i, 'id_hecho_existente'] = int(evt_exist)
                    df_acc.at[i, 'validacion'] = "Reemplazará acción existente"
                else:
                    df_acc.at[i, 'validacion'] = "Nuevo"
            st.dataframe(df_acc, use_container_width=True)
            if any(v.startswith(("id_", "Acción", "Falta", "Reincidencia")) for v in df_acc['validacion']):
                st.error("Corrige los errores y vuelve a subir.")
            else:
                n_nuevos = sum(1 for v in df_acc['validacion'] if v == "Nuevo")
                n_reemp = sum(1 for v in df_acc['validacion'] if v == "Reemplazará acción existente")
                st.info(f"**{n_nuevos}** nuevos + **{n_reemp}** reemplazarán acciones existentes")
                if n_reemp:
                    st.warning(f"⚠️ {n_reemp} acción(es) ya registrada(s) se **REEMPLAZARÁN** en el historial.")
                if st.button("🚀 Procesar Acciones", key="btn_proc_acc"):
                    insertados = 0; actualizados = 0
                    for i, row in df_acc.iterrows():
                        rid = int(float(row['id_reincidencia']))
                        cod = int(float(row['id_codigo']))
                        acc = str(row['accion']).strip().lower()
                        id_tipo = mapa_acc[acc]
                        fecha_s = pd.to_datetime(row['fecha_observacion']).strftime('%Y-%m-%d')
                        obs = str(row.get('observacion')).strip() if pd.notna(row.get('observacion')) else f"{acc.capitalize()} importada"
                        if row['id_hecho_existente'] is not None:
                            run_transaction("UPDATE fact_eventos_operador SET id_tipo_evento=:t, fecha_observacion=:f, observacion=:o WHERE id_hecho_evento=:e",
                                {"t": id_tipo, "f": fecha_s, "o": obs, "e": int(row['id_hecho_existente'])})
                            actualizados += 1
                        else:
                            max_evt = run_query("SELECT COALESCE(MAX(id_hecho_evento),0)+1 as n FROM fact_eventos_operador").iloc[0]['n']
                            run_transaction("INSERT INTO fact_eventos_operador (id_hecho_evento, id_codigo, id_tipo_evento, fecha_observacion, observacion, id_vigencia, usuario_registra, fecha_registro) VALUES (:id,:c,:t,:f,:o,1,:u,CURRENT_TIMESTAMP)",
                                {"id": int(max_evt), "c": cod, "t": id_tipo, "f": fecha_s, "o": obs, "u": usuario_actual})
                            run_transaction("UPDATE fact_reincidencia SET id_hecho_evento=:e WHERE id_reincidencia=:r", {"e": int(max_evt), "r": rid})
                            insertados += 1
                    registrar_auditoria(usuario_actual, 'Importar Acciones Reincidencia', f'Nuevos: {insertados}, Actualizados: {actualizados}')
                    st.success(f"{insertados} nuevas + {actualizados} actualizadas en el historial!")
                    st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")
