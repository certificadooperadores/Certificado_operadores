import streamlit as st
from db import registrar_auditoria, run_query, run_transaction
from modulos.administrar_backups.ui import render_administrar_backups
from modulos.gestion_usuarios.ui import render_gestion_usuarios
from utils import mostrar_badge_version

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
if not st.session_state.get('logged_in'): st.error("Acceso Denegado."); st.stop()
if st.session_state.get('rol') not in ['Administrador', 'Super Administrador']:
    st.error("Acceso Denegado. Solo Administradores."); st.stop()

st.sidebar.caption(f"👤 {st.session_state.get('usuario','')} ({st.session_state.get('rol','')})")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.switch_page("Inicio.py")

mostrar_badge_version()
rol = st.session_state.get('rol', '')
usuario = st.session_state.get('usuario', 'Desconocido')

def modulo_correccion():
    tab_ind, tab_lote = st.tabs(["🎯 Registro Individual", "📦 Por Lote"])
    with tab_ind:
        correccion_individual()
    with tab_lote:
        correccion_lote()

def correccion_individual():
    st.markdown("Buscar registros de eventos por código, cédula, tipo, fecha o estado. Seleccioná las filas y aplicá una acción.")
    tipos = run_query("SELECT id_tipo_evento, nombre_evento FROM dim_tipo_evento ORDER BY id_tipo_evento")

    col1, col2, col3 = st.columns(3)
    with col1:
        codigo = st.text_input("Código operador", key="corr_cod")
        cedula = st.text_input("Cédula", key="corr_ced")
    with col2:
        opciones_evt = ["Todos"] + [f"{r['id_tipo_evento']} - {r['nombre_evento']}" for _, r in tipos.iterrows()]
        evento = st.selectbox("Tipo de evento", opciones_evt, key="corr_evt")
        estado = st.selectbox("Estado", ["Todos", "Vigente", "Anulado"], key="corr_est")
    with col3:
        fdesde = st.date_input("Fecha desde", value=None, key="corr_desde")
        fhasta = st.date_input("Fecha hasta", value=None, key="corr_hasta")

    condiciones = []
    params = {}
    if codigo.strip().isdigit():
        condiciones.append("e.id_codigo = :cod"); params["cod"] = int(codigo.strip())
    if cedula.strip().isdigit():
        condiciones.append("c.id_persona = :ced"); params["ced"] = int(cedula.strip())
    if evento != "Todos":
        condiciones.append("e.id_tipo_evento = :evt"); params["evt"] = int(evento.split(" - ")[0])
    if estado == "Vigente":
        condiciones.append("e.id_vigencia = 1")
    elif estado == "Anulado":
        condiciones.append("e.id_vigencia = 2")
    if fdesde:
        condiciones.append("e.fecha_registro::date >= :fdesde"); params["fdesde"] = fdesde.strftime('%Y-%m-%d')
    if fhasta:
        condiciones.append("e.fecha_registro::date <= :fhasta"); params["fhasta"] = fhasta.strftime('%Y-%m-%d')

    where = " AND ".join(condiciones) if condiciones else "1=1"
    query = f"""
        SELECT e.id_hecho_evento, e.id_codigo, c.id_persona,
               (p.nombres || ' ' || p.primer_apellido) AS nombre,
               te.nombre_evento,
               e.fecha_registro::date AS fecha,
               CASE WHEN e.id_vigencia = 1 THEN 'Vigente' ELSE 'Anulado' END AS estado
        FROM fact_eventos_operador e
        JOIN dim_codigo c ON e.id_codigo = c.id_codigo
        JOIN dim_persona p ON c.id_persona = p.id_persona
        JOIN dim_tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
        WHERE {where}
        ORDER BY e.fecha_registro DESC
        LIMIT 500
    """
    df = run_query(query, params)

    if df.empty:
        st.info("No se encontraron registros con esos filtros.")
        return

    st.markdown(f"**{len(df)} registro(s)** (máx 500). Hacé clic en las filas para seleccionar.")

    selection = st.dataframe(
        df[['id_hecho_evento', 'id_codigo', 'id_persona', 'nombre', 'nombre_evento', 'fecha', 'estado']],
        on_select="rerun", selection_mode="multi-row",
        hide_index=True, use_container_width=True, key="corr_table",
    )

    try:
        filas = selection.selection.rows
    except AttributeError:
        filas = []

    if filas:
        ids = [int(df.iloc[f]['id_hecho_evento']) for f in filas]
        ids_str = ','.join(str(i) for i in ids)
        st.warning(f"⚠️ {len(ids)} registro(s) seleccionado(s).")

        confirmar = st.checkbox("Confirmo que quiero aplicar la acción a los registros seleccionados.", key="corr_conf")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🟢 Reactivar", disabled=not confirmar, key="corr_react"):
                run_transaction(f"UPDATE fact_eventos_operador SET id_vigencia = 1 WHERE id_hecho_evento IN ({ids_str})")
                registrar_auditoria(usuario, 'Reactivar Registros', f'IDs: {ids_str}')
                st.success(f"✅ {len(ids)} registro(s) reactivado(s)."); st.rerun()
        with c2:
            if st.button("🟡 Anular", disabled=not confirmar, key="corr_anul"):
                run_transaction(f"UPDATE fact_eventos_operador SET id_vigencia = 2 WHERE id_hecho_evento IN ({ids_str})")
                registrar_auditoria(usuario, 'Anular Registros', f'IDs: {ids_str}')
                st.success(f"✅ {len(ids)} registro(s) anulado(s)."); st.rerun()
        with c3:
            if rol == 'Super Administrador':
                if st.button("🔴 Eliminar", disabled=not confirmar, key="corr_elim"):
                    run_transaction(f"DELETE FROM fact_eventos_operador WHERE id_hecho_evento IN ({ids_str})")
                    registrar_auditoria(usuario, 'Eliminar Registros', f'IDs: {ids_str}')
                    st.error(f"🗑️ {len(ids)} registro(s) eliminado(s) permanentemente."); st.rerun()
            else:
                st.caption("🔒 Eliminar: solo Super Admin")

def correccion_lote():
    st.markdown("Seleccioná un lote (registros cargados en el mismo minuto) para modificarlo o borrarlo de una vez.")
    lotes_df = run_query("SELECT TO_CHAR(fecha_registro::timestamp,'YYYY-MM-DD HH24:MI') as lote, COUNT(*) as n FROM fact_eventos_operador GROUP BY 1 ORDER BY 1 DESC")
    if lotes_df.empty:
        st.info("Sin eventos."); return
    lote_str = st.selectbox("Lote", [f"{r['lote']} ({r['n']} reg.)" for _, r in lotes_df.iterrows()], key="corr_lote").split(" (")[0]

    detalle = run_query("""SELECT e.id_hecho_evento, e.id_codigo, c.id_persona,
        (p.nombres||' '||p.primer_apellido) AS nombre, te.nombre_evento,
        e.fecha_registro::date AS fecha,
        CASE WHEN e.id_vigencia=1 THEN 'Vigente' ELSE 'Anulado' END AS estado
        FROM fact_eventos_operador e JOIN dim_codigo c ON e.id_codigo=c.id_codigo
        JOIN dim_persona p ON c.id_persona=p.id_persona
        JOIN dim_tipo_evento te ON e.id_tipo_evento=te.id_tipo_evento
        WHERE TO_CHAR(e.fecha_registro::timestamp,'YYYY-MM-DD HH24:00')=:l
        ORDER BY e.id_hecho_evento""", {"l": lote_str})

    if detalle.empty:
        st.info("No hay registros en este lote."); return

    n_vig = int((detalle['estado'] == 'Vigente').sum())
    n_anu = int((detalle['estado'] == 'Anulado').sum())
    st.caption(f"{n_vig} vigentes · {n_anu} anulados · {len(detalle)} total")

    st.dataframe(detalle, use_container_width=True, hide_index=True)

    confirmar = st.checkbox("Confirmo que quiero aplicar la acción a TODO el lote.", key="corr_conf_lote")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🟢 Reactivar Lote", disabled=not confirmar, key="corr_react_lote"):
            run_transaction("UPDATE fact_eventos_operador SET id_vigencia=1 WHERE TO_CHAR(fecha_registro::timestamp,'YYYY-MM-DD HH24:00')=:l", {"l": lote_str})
            registrar_auditoria(usuario, 'Reactivar Lote', f"Lote:{lote_str}")
            st.success("✅ Lote reactivado."); st.rerun()
    with c2:
        if st.button("🟡 Anular Lote", disabled=not confirmar, key="corr_anul_lote"):
            run_transaction("UPDATE fact_eventos_operador SET id_vigencia=2 WHERE TO_CHAR(fecha_registro::timestamp,'YYYY-MM-DD HH24:00')=:l", {"l": lote_str})
            registrar_auditoria(usuario, 'Anular Lote', f"Lote:{lote_str}")
            st.success("✅ Lote anulado."); st.rerun()
    with c3:
        if rol == 'Super Administrador':
            if st.button("🔴 Borrar Lote", disabled=not confirmar, key="corr_elim_lote"):
                run_transaction("DELETE FROM fact_eventos_operador WHERE TO_CHAR(fecha_registro::timestamp,'YYYY-MM-DD HH24:00')=:l", {"l": lote_str})
                registrar_auditoria(usuario, 'Borrar Lote', f"Lote:{lote_str}")
                st.error("🗑️ Lote eliminado."); st.rerun()
        else:
            st.caption("🔒 Borrar: solo Super Admin")

nombres = ["🔐 Gestión de Usuarios", "🗑️ Corrección de Registros", "⚙️ Catálogos"]
if rol == 'Super Administrador':
    nombres.insert(1, "💾 Administrar Backups")
    t1, t2, t3, t4 = st.tabs(nombres)
    with t1:
        render_gestion_usuarios()
    with t2:
        render_administrar_backups()
    with t3: modulo_correccion()
    with t4: exec(open("modulos/4_Catalogos.py").read(), globals())
else:
    t1, t2, t3 = st.tabs(nombres)
    with t1:
        render_gestion_usuarios()
    with t2: modulo_correccion()
    with t3: exec(open("modulos/4_Catalogos.py").read(), globals())
