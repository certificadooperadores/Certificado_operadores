import streamlit as st
import pandas as pd
from db import run_query, run_transaction, registrar_auditoria
usuario_actual = st.session_state.get('usuario', 'Usuario')
st.title("⚙️ Catálogos")

tab_emp, tab_veh, tab_imp, tab_comp, tab_det = st.tabs(["🏢 Empresas", "🚌 Vehículos", "⚠️ Impactos", "📋 Comportamientos", "🔍 Detalle Comportamiento"])

with tab_emp:
    empresas = run_query("SELECT id_empresa, nombre_empresa, CASE WHEN id_vigencia=1 THEN 'Activo' ELSE 'Inactivo' END as estado, id_vigencia FROM dim_empresa ORDER BY id_empresa")
    st.dataframe(empresas[['id_empresa','nombre_empresa','estado']], use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("form_empresa"):
            nombre = st.text_input("Nueva empresa")
            if st.form_submit_button("Crear"):
                if nombre:
                    max_id = run_query("SELECT COALESCE(MAX(id_empresa),0)+1 as n FROM dim_empresa").iloc[0]['n']
                    run_transaction("INSERT INTO dim_empresa (id_empresa,nombre_empresa,id_vigencia,usuario_registra) VALUES (:i,:n,1,:u)", {"i":int(max_id),"n":nombre.upper(),"u":usuario_actual})
                    st.success("Creada."); st.rerun()
    with col2:
        with st.form("form_emp_estado"):
            emp_sel = st.selectbox("Empresa", empresas['nombre_empresa'].tolist())
            accion = st.radio("Acción", ["Activar", "Inactivar"], horizontal=True)
            if st.form_submit_button("Cambiar Estado"):
                id_e = int(empresas[empresas['nombre_empresa']==emp_sel]['id_empresa'].values[0])
                nuevo_estado = 1 if accion == "Activar" else 2
                run_transaction("UPDATE dim_empresa SET id_vigencia=:v WHERE id_empresa=:i", {"v":nuevo_estado,"i":id_e})
                st.success(f"{accion}da."); st.rerun()
    
    with st.form("form_emp_editar"):
        editar = st.selectbox("Editar nombre", [""] + empresas['nombre_empresa'].tolist())
        nuevo = st.text_input("Nuevo nombre")
        if st.form_submit_button("Renombrar") and editar and nuevo:
            id_e = int(empresas[empresas['nombre_empresa']==editar]['id_empresa'].values[0])
            run_transaction("UPDATE dim_empresa SET nombre_empresa=:n WHERE id_empresa=:i", {"n":nuevo.upper(),"i":id_e})
            st.success("Renombrada."); st.rerun()

with tab_veh:
    vehiculos = run_query("SELECT id_vehiculo, nombre_vehiculo FROM dim_vehiculo ORDER BY id_vehiculo")
    st.dataframe(vehiculos, use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    with col1:
        with st.form("form_veh"):
            nombre = st.text_input("Nuevo vehículo")
            if st.form_submit_button("Crear"):
                if nombre:
                    max_id = run_query("SELECT COALESCE(MAX(id_vehiculo),0)+1 as n FROM dim_vehiculo").iloc[0]['n']
                    run_transaction("INSERT INTO dim_vehiculo (id_vehiculo,nombre_vehiculo,usuario_registra) VALUES (:i,:n,:u)", {"i":int(max_id),"n":nombre.upper(),"u":usuario_actual})
                    st.success("Creado."); st.rerun()
    with col2:
        with st.form("form_veh_editar"):
            editar = st.selectbox("Editar nombre", [""] + vehiculos['nombre_vehiculo'].tolist())
            nuevo = st.text_input("Nuevo nombre")
            if st.form_submit_button("Renombrar") and editar and nuevo:
                id_v = int(vehiculos[vehiculos['nombre_vehiculo']==editar]['id_vehiculo'].values[0])
                run_transaction("UPDATE dim_vehiculo SET nombre_vehiculo=:n WHERE id_vehiculo=:i", {"n":nuevo.upper(),"i":id_v})
                st.success("Renombrado."); st.rerun()

with tab_imp:
    st.markdown("**Niveles de Impacto** — Clasificación de severidad de comportamientos.")
    impactos = run_query("SELECT id_impacto, impacto, maximo, dias_maximo FROM dim_impacto ORDER BY id_impacto")
    st.dataframe(impactos, use_container_width=True, hide_index=True)
    
    col_c, col_m = st.columns(2)
    with col_c:
        with st.form("form_impacto"):
            st.subheader("➕ Nuevo Impacto")
            nombre_imp = st.text_input("Nombre", key="imp_nom")
            col1, col2 = st.columns(2)
            with col1:
                max_imp = st.number_input("Máximo ocurrencias", min_value=0, value=2, key="imp_max")
            with col2:
                dias_imp = st.number_input("Días reinicio", min_value=0, value=90, key="imp_dias")
            if st.form_submit_button("Crear"):
                if nombre_imp:
                    max_id = run_query("SELECT COALESCE(MAX(id_impacto),0)+1 as n FROM dim_impacto").iloc[0]['n']
                    run_transaction("INSERT INTO dim_impacto (id_impacto,impacto,maximo,dias_maximo,usuario_registra) VALUES (:i,:n,:m,:d,:u)", {"i":int(max_id),"n":nombre_imp.upper(),"m":max_imp,"d":dias_imp,"u":usuario_actual})
                    registrar_auditoria(usuario_actual, 'Crear Impacto', f"Impacto: {nombre_imp}")
                    st.success("Creado."); st.rerun()
    with col_m:
        imp_sel_ed = st.selectbox("Seleccionar impacto a editar", [""] + impactos['impacto'].tolist(), key="imp_edit_sel")
        if imp_sel_ed:
            ir = impactos[impactos['impacto']==imp_sel_ed].iloc[0]
            with st.form("form_imp_editar"):
                st.subheader(f"✏️ Editando: {imp_sel_ed}")
                n_nom = st.text_input("Nombre", value=ir['impacto'], key="imp_ed_nom")
                n_max = st.number_input("Máximo ocurrencias", min_value=0, value=int(ir['maximo']), key="imp_ed_max")
                n_dias = st.number_input("Días reinicio", min_value=0, value=int(ir['dias_maximo']), key="imp_ed_dias")
                if st.form_submit_button("Guardar cambios"):
                    run_transaction("UPDATE dim_impacto SET impacto=:n, maximo=:m, dias_maximo=:d WHERE id_impacto=:i",
                        {"n": n_nom.upper(), "m": n_max, "d": n_dias, "i": int(ir['id_impacto'])})
                    registrar_auditoria(usuario_actual, 'Editar Impacto', f"ID: {ir['id_impacto']}")
                    st.success("Actualizado."); st.rerun()

with tab_comp:
    st.markdown("**Comportamientos** — Cada comportamiento está asociado a un nivel de impacto.")
    impactos_lista = run_query("SELECT id_impacto, impacto FROM dim_impacto ORDER BY id_impacto")
    imp_opciones = dict(zip(impactos_lista['id_impacto'], impactos_lista['impacto']))
    
    comps = run_query("""SELECT c.id_comportamiento, c.comportamiento, i.impacto 
                         FROM dim_comportamiento c 
                         LEFT JOIN dim_impacto i ON c.id_impacto = i.id_impacto 
                         ORDER BY c.id_comportamiento""")
    st.dataframe(comps, use_container_width=True, hide_index=True)
    
    col_c2, col_m2 = st.columns(2)
    with col_c2:
        with st.form("form_comportamiento"):
            st.subheader("➕ Nuevo Comportamiento")
            comp_nombre = st.text_input("Descripción", key="comp_nom")
            comp_impacto = st.selectbox("Nivel de Impacto", list(imp_opciones.values()), key="comp_imp")
            if st.form_submit_button("Crear"):
                if comp_nombre and comp_impacto:
                    id_imp = [k for k,v in imp_opciones.items() if v == comp_impacto][0]
                    max_id = run_query("SELECT COALESCE(MAX(id_comportamiento),0)+1 as n FROM dim_comportamiento").iloc[0]['n']
                    run_transaction("INSERT INTO dim_comportamiento (id_comportamiento,comportamiento,id_impacto,usuario_registra) VALUES (:i,:n,:imp,:u)", {"i":int(max_id),"n":comp_nombre.lower(),"imp":id_imp,"u":usuario_actual})
                    registrar_auditoria(usuario_actual, 'Crear Comportamiento', f"Comportamiento: {comp_nombre}")
                    st.success("Creado."); st.rerun()
    with col_m2:
        comp_sel_ed = st.selectbox("Seleccionar comportamiento a editar", [""] + comps['comportamiento'].tolist(), key="comp_edit_sel")
        if comp_sel_ed:
            cr = comps[comps['comportamiento']==comp_sel_ed].iloc[0]
            with st.form("form_comp_editar"):
                st.subheader(f"✏️ Editando: {comp_sel_ed}")
                n_desc = st.text_input("Descripción", value=cr['comportamiento'], key="comp_ed_desc")
                n_imp = st.selectbox("Nivel de Impacto", list(imp_opciones.values()),
                    index=list(imp_opciones.keys())[list(imp_opciones.values()).index(cr['impacto'])] if cr['impacto'] in imp_opciones.values() else 0, key="comp_ed_imp")
                if st.form_submit_button("Guardar cambios"):
                    id_imp_n = [k for k,v in imp_opciones.items() if v == n_imp][0]
                    run_transaction("UPDATE dim_comportamiento SET comportamiento=:n, id_impacto=:imp WHERE id_comportamiento=:i",
                        {"n": n_desc.lower(), "imp": id_imp_n, "i": int(cr['id_comportamiento'])})
                    registrar_auditoria(usuario_actual, 'Editar Comportamiento', f"ID: {cr['id_comportamiento']}")
                    st.success("Actualizado."); st.rerun()

with tab_det:
    st.markdown("**Detalle de Comportamientos** — Jerarquía completa de clasificación de eventos.")
    fuente_op = st.selectbox("Filtrar por fuente", ["Todas", "jerarquia hgi", "pqrs", "secretaría de movilidad"], key="det_fuente")
    if fuente_op == "Todas":
        detalles = run_query("""SELECT d.id_jerarquia, d.fuente, d.descripcion_comportamiento, d.tipo, d.servicios, 
                                d.jerarquia_1, d.jerarquia_2, d.jerarquia_3, d.jerarquia_4, c.id_comportamiento as comp_id, c.comportamiento 
                                FROM dim_detalle_comportamiento d 
                                LEFT JOIN dim_comportamiento c ON d.id_comportamiento = c.id_comportamiento 
                                ORDER BY d.id_jerarquia LIMIT 500""")
    else:
        detalles = run_query("""SELECT d.id_jerarquia, d.fuente, d.descripcion_comportamiento, d.tipo, d.servicios, 
                                d.jerarquia_1, d.jerarquia_2, d.jerarquia_3, d.jerarquia_4, c.id_comportamiento as comp_id, c.comportamiento 
                                FROM dim_detalle_comportamiento d 
                                LEFT JOIN dim_comportamiento c ON d.id_comportamiento = c.id_comportamiento 
                                WHERE d.fuente = :f ORDER BY d.id_jerarquia LIMIT 500""", {"f": fuente_op})
    st.dataframe(detalles, use_container_width=True, hide_index=True)
    st.caption(f"Mostrando hasta 500 registros de {len(detalles)}")
    
    st.markdown("---")
    comps_det = run_query("SELECT id_comportamiento, comportamiento FROM dim_comportamiento ORDER BY id_comportamiento")
    comp_opts = {str(r['id_comportamiento']): r['comportamiento'] for _, r in comps_det.iterrows()}
    
    col_dc, col_de = st.columns(2)
    with col_dc:
        with st.form("form_detalle"):
            st.subheader("➕ Nuevo Detalle")
            fuente_n = st.selectbox("Fuente", ["jerarquia hgi", "pqrs", "secretaría de movilidad"], key="det_fuente_n")
            tipo_n = st.text_input("Tipo", key="det_tipo")
            servicios_n = st.text_input("Servicios", key="det_serv")
            j1 = st.text_input("Jerarquía 1", key="det_j1")
            j2 = st.text_input("Jerarquía 2", key="det_j2")
            j3 = st.text_input("Jerarquía 3", key="det_j3")
            j4 = st.text_input("Jerarquía 4", key="det_j4")
            comp_n = st.selectbox("Comportamiento asociado", list(comp_opts.keys()), format_func=lambda x: comp_opts[x], key="det_comp")
            if st.form_submit_button("Crear"):
                if fuente_n and tipo_n and servicios_n and j1:
                    desc = f"{tipo_n.lower()}::{servicios_n.lower()}::{j1.lower()}"
                    if j2: desc += f"::{j2.lower()}"
                    if j3: desc += f"::{j3.lower()}"
                    if j4: desc += f"::{j4.lower()}"
                    max_id = run_query("SELECT COALESCE(MAX(id_jerarquia),0)+1 as n FROM dim_detalle_comportamiento").iloc[0]['n']
                    run_transaction("""INSERT INTO dim_detalle_comportamiento 
                        (id_jerarquia, fuente, descripcion_comportamiento, tipo, servicios, 
                        jerarquia_1, jerarquia_2, jerarquia_3, jerarquia_4, id_comportamiento, usuario_registra)
                        VALUES (:id, :f, :d, :t, :s, :j1, :j2, :j3, :j4, :c, :u)""",
                        {"id": int(max_id), "f": fuente_n, "d": desc, "t": tipo_n.lower(), "s": servicios_n.lower(),
                         "j1": j1.lower(), "j2": j2.lower() if j2 else None, "j3": j3.lower() if j3 else None,
                         "j4": j4.lower() if j4 else None, "c": int(comp_n), "u": usuario_actual})
                    registrar_auditoria(usuario_actual, 'Crear Detalle Comportamiento', f"Desc: {desc}")
                    st.success("Creado."); st.rerun()
    with col_de:
        det_sel = st.selectbox("Seleccionar ID a editar", [""] + [str(x) for x in detalles['id_jerarquia'].tolist()], key="det_edit_sel")
        if det_sel:
            dr = detalles[detalles['id_jerarquia'] == int(det_sel)].iloc[0]
            with st.form("form_det_editar"):
                st.subheader(f"✏️ Editando ID {det_sel}")
                n_fuente = st.selectbox("Fuente", ["jerarquia hgi", "pqrs", "secretaría de movilidad"],
                    index=["jerarquia hgi", "pqrs", "secretaría de movilidad"].index(dr['fuente']) if dr['fuente'] in ["jerarquia hgi", "pqrs", "secretaría de movilidad"] else 0, key="det_ed_f")
                n_tipo = st.text_input("Tipo", value=dr['tipo'] if dr['tipo'] else "", key="det_ed_tipo")
                n_serv = st.text_input("Servicios", value=dr['servicios'] if dr['servicios'] else "", key="det_ed_serv")
                n_j1 = st.text_input("Jerarquía 1", value=dr['jerarquia_1'] if dr['jerarquia_1'] else "", key="det_ed_j1")
                n_j2 = st.text_input("Jerarquía 2", value=dr['jerarquia_2'] if dr['jerarquia_2'] else "", key="det_ed_j2")
                n_j3 = st.text_input("Jerarquía 3", value=dr['jerarquia_3'] if dr['jerarquia_3'] else "", key="det_ed_j3")
                n_j4 = st.text_input("Jerarquía 4", value=dr['jerarquia_4'] if dr['jerarquia_4'] else "", key="det_ed_j4")
                n_comp = st.selectbox("Comportamiento asociado", list(comp_opts.keys()),
                    index=list(comp_opts.keys()).index(str(dr['comp_id'])) if pd.notna(dr['comp_id']) and str(dr['comp_id']) in comp_opts else 0,
                    format_func=lambda x: comp_opts[x], key="det_ed_comp")
                if st.form_submit_button("Guardar cambios"):
                    ndesc = f"{n_tipo.lower()}::{n_serv.lower()}::{n_j1.lower()}"
                    if n_j2: ndesc += f"::{n_j2.lower()}"
                    if n_j3: ndesc += f"::{n_j3.lower()}"
                    if n_j4: ndesc += f"::{n_j4.lower()}"
                    run_transaction("""UPDATE dim_detalle_comportamiento SET fuente=:f, tipo=:t, servicios=:s, 
                        jerarquia_1=:j1, jerarquia_2=:j2, jerarquia_3=:j3, jerarquia_4=:j4, 
                        descripcion_comportamiento=:d, id_comportamiento=:c WHERE id_jerarquia=:id""",
                        {"f": n_fuente, "t": n_tipo.lower(), "s": n_serv.lower(),
                         "j1": n_j1.lower(), "j2": n_j2.lower() if n_j2 else None,
                         "j3": n_j3.lower() if n_j3 else None, "j4": n_j4.lower() if n_j4 else None,
                         "d": ndesc, "c": int(n_comp), "id": int(det_sel)})
                    registrar_auditoria(usuario_actual, 'Editar Detalle Comportamiento', f"ID: {det_sel}")
                    st.success("Actualizado."); st.rerun()
