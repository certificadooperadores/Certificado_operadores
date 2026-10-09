import streamlit as st
import pandas as pd
import io
from datetime import date
from db import run_query, registrar_auditoria

usuario_actual = st.session_state.get('usuario', 'Usuario')
rol_actual = st.session_state.get('rol', 'Desconocido')

st.title(" Reportes y Exportaciones")

def get_empresas():
    df = run_query("SELECT id_empresa, nombre_empresa FROM dim_empresa ORDER BY id_empresa")
    return dict(zip(df['id_empresa'], df['nombre_empresa'])) if not df.empty else {}

def get_tipologias():
    df = run_query("SELECT id_perfil_tipologia, autoriza_articulado, autoriza_padron, autoriza_complementario, autoriza_auxiliar FROM dim_perfil_tipologia ORDER BY id_perfil_tipologia")
    out = {}
    for _, r in df.iterrows():
        partes = []
        if r['autoriza_articulado']: partes.append('Articulado')
        if r['autoriza_padron']: partes.append('Padron')
        if r['autoriza_complementario']: partes.append('Complementario')
        if r['autoriza_auxiliar']: partes.append('Auxiliar')
        out[r['id_perfil_tipologia']] = f"{r['id_perfil_tipologia']} - {', '.join(partes)}" if partes else str(r['id_perfil_tipologia'])
    return out

reportes = [
    {
        "id": "utryt",
        "nombre": "Consolidado UTRYT",
        "descripcion": "Exportación de operadores con código, documento, nombre, estado, empresa y tipología (formato UTRYT).",
        "columnas": ["METROCALI ID", "DOCUMENTTYPEID", "DOCUMENTNUMBER", "DRIVERNAME", "LASTNAME", "LASTNAME2", "STATEID", "TRANSPORTCONTRATISTID", "REGISTERDATE", "TIPOLOGY"],
        "query": """
            SELECT dc.id_codigo AS "METROCALI ID", 1 AS "DOCUMENTTYPEID",
                   dc.id_persona AS "DOCUMENTNUMBER",
                   p.nombres AS "DRIVERNAME", p.primer_apellido AS "LASTNAME", p.segundo_apellido AS "LASTNAME2",
                   CASE WHEN dc.id_vigencia = 1 THEN 1 ELSE 2 END AS "STATEID",
                   dc.id_empresa AS "TRANSPORTCONTRATISTID",
                   dc.fecha_registro::date AS "REGISTERDATE",
                   dc.id_perfil_tipologia AS "TIPOLOGY"
            FROM dim_codigo dc
            LEFT JOIN dim_persona p ON dc.id_persona = p.id_persona
            WHERE 1=1
        """,
        "filtros": [
            {"tipo": "empresa", "col": "dc.id_empresa"},
            {"tipo": "estado", "col": "dc.id_vigencia"},
            {"tipo": "tipologia", "col": "dc.id_perfil_tipologia"},
        ],
    },
    {
        "id": "operadores_empresa",
        "nombre": "Operadores por Empresa y Tipología",
        "descripcion": "Conteo de operadores agrupados por empresa y tipología con totales.",
        "columnas": ["Empresa", "Tipologia", "Codigos"],
        "query": """
            SELECT e.nombre_empresa AS "Empresa", t.id_perfil_tipologia AS "Tipologia",
                   COUNT(*) AS "Codigos"
            FROM dim_codigo dc
            LEFT JOIN dim_empresa e ON dc.id_empresa = e.id_empresa
            LEFT JOIN dim_perfil_tipologia t ON dc.id_perfil_tipologia = t.id_perfil_tipologia
            WHERE 1=1
            GROUP BY e.nombre_empresa, t.id_perfil_tipologia
            ORDER BY e.nombre_empresa, t.id_perfil_tipologia
        """,
        "filtros": [
            {"tipo": "empresa", "col": "dc.id_empresa"},
            {"tipo": "estado_activo", "col": "dc.id_codigo"},
        ],
    },
    {
        "id": "licencias_vencer",
        "nombre": "Licencias por Vencer",
        "descripcion": "Licencias de conducción que vencen en los próximos N días.",
        "columnas": ["Codigo", "Cedula", "Nombre", "Tipo Licencia", "Vencimiento", "Dias Restantes"],
        "query": """
            SELECT l.id_codigo AS "Codigo", l.id_codigo AS "Cedula", '' AS "Nombre",
                   l.tipo AS "Tipo Licencia", l.vencimiento AS "Vencimiento",
                   (l.vencimiento::date - CURRENT_DATE) AS "Dias Restantes"
            FROM fact_licencias l
            WHERE 1=1 AND l.vencimiento IS NOT NULL
        """,
        "filtros": [
            {"tipo": "dias_vencer", "col": "l.vencimiento::date", "default": 90},
        ],
    },
    {
        "id": "eventos_tipo",
        "nombre": "Eventos por Tipo y Rango de Fechas",
        "descripcion": "Eventos de operadores por tipo en un rango de fechas.",
        "columnas": ["Codigo", "Cedula", "Nombre", "Evento", "Fecha", "Observacion"],
        "query": """
            SELECT e.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   te.nombre_evento AS "Evento",
                   COALESCE(e.fecha_certificado, e.fecha_retiro, e.fecha_suspension, e.fecha_observacion, e.fecha_registro) AS "Fecha",
                   e.observacion AS "Observacion"
            FROM fact_eventos_operador e
            LEFT JOIN dim_codigo c ON e.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            LEFT JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
            WHERE 1=1
        """,
        "filtros": [
            {"tipo": "fecha", "col": "COALESCE(e.fecha_certificado, e.fecha_retiro, e.fecha_suspension, e.fecha_observacion, e.fecha_registro)::date"},
            {"tipo": "tipo_evento", "col": "e.id_tipo_evento"},
        ],
    },
    {
        "id": "reincidencias",
        "nombre": "Reincidencias con Determinación",
        "descripcion": "Casos de reincidencia con su determinación Metrocali.",
        "columnas": ["Reincidencia", "Codigo", "Empresa", "Impacto", "Comportamiento", "Inicio", "Fin", "Determinacion"],
        "query": """
            SELECT r.id_reincidencia AS "Reincidencia", r.id_codigo AS "Codigo",
                   e.nombre_empresa AS "Empresa", i.impacto AS "Impacto",
                   c.comportamiento AS "Comportamiento", r.fecha_inicio AS "Inicio",
                   r.fecha_fin AS "Fin", r.determinacion_mc AS "Determinacion"
            FROM fact_reincidencia r
            LEFT JOIN dim_impacto i ON r.id_impacto = i.id_impacto
            LEFT JOIN dim_comportamiento c ON r.id_comportamiento = c.id_comportamiento
            LEFT JOIN dim_codigo dc ON r.id_codigo = dc.id_codigo
            LEFT JOIN dim_empresa e ON dc.id_empresa = e.id_empresa
            WHERE 1=1
        """,
        "filtros": [
            {"tipo": "empresa", "col": "dc.id_empresa"},
            {"tipo": "impacto", "col": "r.id_impacto"},
        ],
    },
    {
        "id": "comportamientos_operador",
        "nombre": "Comportamientos por Operador",
        "descripcion": "Comportamientos registrados por operador en un rango de fechas.",
        "columnas": ["Codigo", "Cedula", "Nombre", "Descripcion", "Caso", "Fecha", "Vehiculo", "Ruta"],
        "query": """
            SELECT f.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   d.descripcion_comportamiento AS "Descripcion",
                   f.caso_bitacora_ticket AS "Caso", f.fecha_evento AS "Fecha",
                   f.vehiculo AS "Vehiculo", f.ruta AS "Ruta"
            FROM fact_comportamiento f
            LEFT JOIN dim_detalle_comportamiento d ON f.id_jerarquia = d.id_jerarquia
            LEFT JOIN dim_codigo c ON f.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            WHERE 1=1
        """,
        "filtros": [
            {"tipo": "codigo", "col": "f.id_codigo"},
            {"tipo": "fecha", "col": "f.fecha_evento::date"},
        ],
    },
    {
        "id": "certificados_vencer",
        "nombre": "Certificados por Vencer",
        "descripcion": "Certificados de operadores (eventos certificación, reactivación y renovación) que vencen en los próximos N días (vigencia 3 años).",
        "columnas": ["Codigo", "Cedula", "Nombre", "Ultimo Evento", "Fecha Certificado", "Vencimiento", "Dias Restantes"],
        "query": """
            SELECT e.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   te.nombre_evento AS "Ultimo Evento",
                   e.fecha_certificado::date AS "Fecha Certificado",
                   (e.fecha_certificado::date + INTERVAL '3 years')::date AS "Vencimiento",
                   ((e.fecha_certificado::date + INTERVAL '3 years')::date - CURRENT_DATE) AS "Dias Restantes"
            FROM (
                SELECT DISTINCT ON (id_codigo) id_codigo, id_tipo_evento, fecha_certificado
                FROM fact_eventos_operador
                WHERE id_tipo_evento IN (1,2,3) AND fecha_certificado IS NOT NULL AND fecha_certificado <> ''
                ORDER BY id_codigo, fecha_certificado::date DESC
            ) e
            LEFT JOIN dim_codigo c ON e.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            LEFT JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
            WHERE 1=1 AND c.id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)
        """,
        "filtros": [
            {"tipo": "dias_vencer", "col": "(e.fecha_certificado::date + INTERVAL '3 years')::date", "default": 90},
        ],
    },
    {
        "id": "certificados_vencidos",
        "nombre": "Certificados Vencidos",
        "descripcion": "Operadores con certificado (eventos certificación, reactivación o renovación) vencido hace más de 3 años.",
        "columnas": ["Codigo", "Cedula", "Nombre", "Ultimo Evento", "Fecha Certificado", "Vencimiento", "Dias Vencido"],
        "query": """
            SELECT e.id_codigo AS "Codigo", c.id_persona AS "Cedula",
                   (p.nombres || ' ' || p.primer_apellido) AS "Nombre",
                   te.nombre_evento AS "Ultimo Evento",
                   e.fecha_certificado::date AS "Fecha Certificado",
                   (e.fecha_certificado::date + INTERVAL '3 years')::date AS "Vencimiento",
                   (CURRENT_DATE - (e.fecha_certificado::date + INTERVAL '3 years')::date) AS "Dias Vencido"
            FROM (
                SELECT DISTINCT ON (id_codigo) id_codigo, id_tipo_evento, fecha_certificado
                FROM fact_eventos_operador
                WHERE id_tipo_evento IN (1,2,3) AND fecha_certificado IS NOT NULL AND fecha_certificado <> ''
                ORDER BY id_codigo, fecha_certificado::date DESC
            ) e
            LEFT JOIN dim_codigo c ON e.id_codigo = c.id_codigo
            LEFT JOIN dim_persona p ON c.id_persona = p.id_persona
            LEFT JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
            WHERE 1=1 AND (e.fecha_certificado::date + INTERVAL '3 years')::date < CURRENT_DATE
              AND c.id_codigo NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)
        """,
        "filtros": [],
    },
]

# ---------- Filtros dinámicos ----------
def construir_filtros(def_report):
    condiciones = []
    params = {}
    emp_map = get_empresas()
    tipo_map = get_tipologias()
    for f in def_report.get("filtros", []):
        t = f["tipo"]
        if t == "empresa":
            opciones = ["Todas"] + [f"{k} - {v}" for k, v in emp_map.items()]
            sel = st.selectbox("Empresa", opciones, key=f"filt_emp_{def_report['id']}")
            if sel != "Todas":
                id_e = int(sel.split(" - ")[0])
                condiciones.append(f"{f['col']} = :emp")
                params["emp"] = id_e
        elif t == "estado":
            sel = st.selectbox("Estado", ["Vigente", "Inactivo", "Todos"], index=0, key=f"filt_est_{def_report['id']}")
            if sel != "Todos":
                condiciones.append(f"{f['col']} = :est")
                params["est"] = 1 if sel == "Vigente" else 2
        elif t == "estado_activo":
            sel = st.selectbox("Estado (Activo = sin cancelación)", ["Activos", "Cancelados", "Todos"], index=0, key=f"filt_estac_{def_report['id']}")
            if sel == "Activos":
                condiciones.append(f"{f['col']} NOT IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)")
            elif sel == "Cancelados":
                condiciones.append(f"{f['col']} IN (SELECT id_codigo FROM fact_eventos_operador WHERE id_tipo_evento = 7)")
        elif t == "tipologia":
            opciones = ["Todas"] + [str(k) for k in tipo_map.keys()]
            sel = st.selectbox("Tipología", opciones, key=f"filt_tip_{def_report['id']}")
            if sel != "Todas":
                condiciones.append(f"{f['col']} = :tip")
                params["tip"] = int(sel)
        elif t == "dias_vencer":
            dias = st.slider("Días para vencimiento", 1, 365, int(f.get("default", 90)), key=f"filt_dias_{def_report['id']}")
            condiciones.append(f"{f['col']} BETWEEN CURRENT_DATE AND CURRENT_DATE + {dias}")
        elif t == "fecha":
            c1, c2 = st.columns(2)
            with c1:
                fdesde = st.date_input("Desde", value=date.today().replace(day=1), key=f"filt_desde_{def_report['id']}")
            with c2:
                fhasta = st.date_input("Hasta", value=date.today(), key=f"filt_hasta_{def_report['id']}")
            if fdesde and fhasta:
                condiciones.append(f"{f['col']} BETWEEN :fdesde AND :fhasta")
                params["fdesde"] = fdesde.strftime('%Y-%m-%d')
                params["fhasta"] = fhasta.strftime('%Y-%m-%d')
        elif t == "tipo_evento":
            te = run_query("SELECT id_tipo_evento, nombre_evento FROM dim_tipo_evento ORDER BY id_tipo_evento")
            opciones = ["Todos"] + [f"{r['id_tipo_evento']} - {r['nombre_evento'].title()}" for _, r in te.iterrows()]
            sel = st.selectbox("Tipo de Evento", opciones, key=f"filt_tev_{def_report['id']}")
            if sel != "Todos":
                condiciones.append(f"{f['col']} = :tev")
                params["tev"] = int(sel.split(" - ")[0])
        elif t == "impacto":
            imp = run_query("SELECT id_impacto, impacto FROM dim_impacto ORDER BY id_impacto")
            opciones = ["Todos"] + [str(r['id_impacto']) + " - " + r['impacto'] for _, r in imp.iterrows()]
            sel = st.selectbox("Impacto", opciones, key=f"filt_imp_{def_report['id']}")
            if sel != "Todos":
                condiciones.append(f"{f['col']} = :imp")
                params["imp"] = int(sel.split(" - ")[0])
        elif t == "codigo":
            cod = st.text_input("Código de Operador", key=f"filt_cod_{def_report['id']}")
            if cod:
                condiciones.append(f"{f['col']} = :cod")
                params["cod"] = int(cod)
    where = " AND ".join(condiciones) if condiciones else ""
    return where, params

# ---------- Motor ----------
def ejecutar(def_report):
    where, params = construir_filtros(def_report)
    query = def_report["query"].replace("WHERE 1=1", "WHERE 1=1" + (" AND " + where if where else ""))
    df = run_query(query, params) if params else run_query(query)
    return df

# ---------- Exportar ----------
def a_excel(df, nombre):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre[:30])
        if not df.empty:
            resumen = pd.DataFrame({"Total Registros": [len(df)]})
            resumen.to_excel(writer, index=False, sheet_name='Resumen', startrow=0)
    return out.getvalue()

def a_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# ---------- UI ----------
st.markdown("Selecciona un reporte, aplica los filtros y exporta a Excel o CSV.")
nombres_reportes = [f"{r['nombre']}" for r in reportes]
sel_reporte = st.selectbox("Reporte", nombres_reportes, key="sel_reporte")
def_report = [r for r in reportes if r["nombre"] == sel_reporte][0]

st.markdown(f"**{def_report['descripcion']}**")

with st.form(f"form_report_{def_report['id']}"):
    col_f, col_b = st.columns([3, 1])
    with col_f:
        where, params = construir_filtros(def_report)
    with col_b:
        st.write("")
        st.write("")
        ejecutar_b = st.form_submit_button("🔍 Ejecutar Reporte")

query = def_report["query"].replace("WHERE 1=1", "WHERE 1=1" + (" AND " + where if where else ""))
if ejecutar_b:
    df = run_query(query, params) if params else run_query(query)
    st.session_state[f"df_report_{def_report['id']}"] = df
else:
    df = st.session_state.get(f"df_report_{def_report['id']}")

if df is not None and not df.empty:
    st.success(f" {len(df)} registros encontrados")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if "Totales" not in df.columns.tolist():
        st.markdown("**Resumen de totales:**")
        cols_numeric = df.select_dtypes(include=['number']).columns.tolist()
        total_row = {"Reporte": f"Total: {len(df)} registros"}
        st.dataframe(pd.DataFrame([total_row]), use_container_width=True, hide_index=True)

    c_exp, c_csv = st.columns(2)
    with c_exp:
        st.download_button("📥 Exportar a Excel", data=a_excel(df, def_report["nombre"]),
            file_name=f"{def_report['id']}_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"exp_xlsx_{def_report['id']}")
    with c_csv:
        st.download_button("📄 Exportar a CSV", data=a_csv(df),
            file_name=f"{def_report['id']}_{date.today()}.csv",
            mime="text/csv", key=f"exp_csv_{def_report['id']}")
    registrar_auditoria(usuario_actual, 'Exportar Reporte', f"{def_report['nombre']} - {len(df)} registros")
elif df is not None:
    st.info("El reporte no arrojó resultados con los filtros actuales.")
