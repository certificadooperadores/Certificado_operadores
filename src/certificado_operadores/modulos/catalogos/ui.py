"""Interfaz Streamlit del módulo de catálogos (spec 007).

Capa de presentación pura: lista y administra los cinco catálogos del sistema
(empresas, vehículos, impactos, comportamientos y detalles de comportamiento) y
delega **toda** la lectura y mutación en
:class:`~certificado_operadores.infra.catalogos_repository.CatalogosRepository`.
No contiene sentencias SQL ni conoce el motor ni el esquema: cada operación de
datos pasa por el repositorio.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# --- Ajuste de ruta de importación -------------------------------------------
# Streamlit agrega al ``sys.path`` la carpeta del script principal
# (``src/certificado_operadores``), no su padre (``src``). Para importar el
# paquete ``certificado_operadores`` dentro de la app —sin depender del
# directorio de trabajo— se agrega ``src`` una sola vez. En las pruebas ya viene
# en el ``path`` (``pythonpath = ["src"]``), por lo que el ajuste es un no-op.
_RUTA_SRC = Path(__file__).resolve().parents[3]
if str(_RUTA_SRC) not in sys.path:
    sys.path.append(str(_RUTA_SRC))

from certificado_operadores.domain.models import (  # noqa: E402
    VIGENCIA_ACTIVA,
    VIGENCIA_ANULADA,
)
from certificado_operadores.infra.catalogos_repository import (  # noqa: E402
    LIMITE_DETALLES,
    CatalogosRepository,
    ComportamientoInfo,
    DatosDetalleComportamiento,
    DetalleComportamientoInfo,
    EmpresaInfo,
    ImpactoInfo,
    VehiculoInfo,
)

USUARIO_POR_DEFECTO = "Usuario"
"""Usuario de sesión usado cuando la clave ``usuario`` no está presente."""

ETIQUETA_TODAS_FUENTES = "Todas"
"""Opción del selector de fuente que desactiva el filtro."""

FUENTES_DETALLE: tuple[str, ...] = ("jerarquia hgi", "pqrs", "secretaría de movilidad")
"""Fuentes válidas de un detalle de comportamiento."""

ACCION_ACTIVAR = "Activar"
"""Acción de vigencia para activar una empresa."""

ACCION_INACTIVAR = "Inactivar"
"""Acción de vigencia para inactivar una empresa."""

ACCIONES_ESTADO: tuple[str, ...] = (ACCION_ACTIVAR, ACCION_INACTIVAR)
"""Opciones del selector de cambio de estado de empresa."""

TITULO = "⚙️ Catálogos"
"""Título de la pestaña de catálogos."""


def vigencia_desde_accion(accion: str) -> int:
    """Traduce la acción legible de estado a la vigencia correspondiente.

    Args:
        accion: Acción seleccionada ("Activar" o "Inactivar").

    Returns:
        La vigencia activa o inactiva.
    """
    if accion == ACCION_ACTIVAR:
        return VIGENCIA_ACTIVA
    return VIGENCIA_ANULADA


def filas_empresas(empresas: list[EmpresaInfo]) -> list[dict[str, object]]:
    """Traduce los DTOs de empresa a filas para la tabla de Streamlit.

    Args:
        empresas: Empresas devueltas por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": empresa.id_empresa,
            "Empresa": empresa.nombre_empresa,
            "Estado": empresa.estado,
        }
        for empresa in empresas
    ]


def filas_vehiculos(vehiculos: list[VehiculoInfo]) -> list[dict[str, object]]:
    """Traduce los DTOs de vehículo a filas para la tabla de Streamlit.

    Args:
        vehiculos: Vehículos devueltos por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {"ID": vehiculo.id_vehiculo, "Vehículo": vehiculo.nombre_vehiculo} for vehiculo in vehiculos
    ]


def filas_impactos(impactos: list[ImpactoInfo]) -> list[dict[str, object]]:
    """Traduce los DTOs de impacto a filas para la tabla de Streamlit.

    Args:
        impactos: Niveles de impacto devueltos por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": impacto.id_impacto,
            "Impacto": impacto.impacto,
            "Máximo": impacto.maximo,
            "Días reinicio": impacto.dias_maximo,
        }
        for impacto in impactos
    ]


def filas_comportamientos(
    comportamientos: list[ComportamientoInfo],
) -> list[dict[str, object]]:
    """Traduce los DTOs de comportamiento a filas para la tabla de Streamlit.

    Args:
        comportamientos: Comportamientos devueltos por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": comportamiento.id_comportamiento,
            "Comportamiento": comportamiento.comportamiento,
            "Impacto": comportamiento.impacto,
        }
        for comportamiento in comportamientos
    ]


def filas_detalles(detalles: list[DetalleComportamientoInfo]) -> list[dict[str, object]]:
    """Traduce los DTOs de detalle a filas para la tabla de Streamlit.

    Args:
        detalles: Detalles devueltos por el repositorio.

    Returns:
        Lista de diccionarios con columnas legibles para ``st.dataframe``.
    """
    return [
        {
            "ID": detalle.id_jerarquia,
            "Fuente": detalle.fuente,
            "Descripción": detalle.descripcion_comportamiento,
            "Tipo": detalle.tipo,
            "Servicios": detalle.servicios,
            "Jerarquía 1": detalle.jerarquia_1,
            "Jerarquía 2": detalle.jerarquia_2,
            "Jerarquía 3": detalle.jerarquia_3,
            "Jerarquía 4": detalle.jerarquia_4,
            "Comportamiento": detalle.comportamiento,
        }
        for detalle in detalles
    ]


def opciones_impacto(impactos: list[ImpactoInfo]) -> dict[int, str]:
    """Construye el mapa identificador → nombre de los niveles de impacto.

    Args:
        impactos: Niveles de impacto devueltos por el repositorio.

    Returns:
        Diccionario ``{id_impacto: impacto}``.
    """
    return {impacto.id_impacto: impacto.impacto for impacto in impactos}


def id_impacto_desde_nombre(opciones: dict[int, str], nombre: str) -> int | None:
    """Busca el identificador del impacto a partir de su nombre.

    Args:
        opciones: Mapa ``{id_impacto: impacto}``.
        nombre: Nombre del impacto seleccionado.

    Returns:
        El identificador del impacto, o ``None`` si el nombre no existe.
    """
    for id_impacto, impacto in opciones.items():
        if impacto == nombre:
            return id_impacto
    return None


def opciones_comportamiento(
    comportamientos: list[ComportamientoInfo],
) -> dict[str, str]:
    """Construye el mapa identificador → descripción de los comportamientos.

    Args:
        comportamientos: Comportamientos devueltos por el repositorio.

    Returns:
        Diccionario ``{str(id_comportamiento): comportamiento}``.
    """
    return {
        str(comportamiento.id_comportamiento): comportamiento.comportamiento
        for comportamiento in comportamientos
    }


def _indice_opcion(opciones: list[str], valor: str) -> int:
    """Devuelve el índice de un valor dentro de una lista de opciones.

    Args:
        opciones: Lista de opciones del selector.
        valor: Valor buscado.

    Returns:
        El índice del valor, o ``0`` si no está presente.
    """
    return opciones.index(valor) if valor in opciones else 0


def _id_empresa_por_nombre(empresas: list[EmpresaInfo], nombre: str) -> int | None:
    """Busca el identificador de una empresa a partir de su nombre."""
    for empresa in empresas:
        if empresa.nombre_empresa == nombre:
            return empresa.id_empresa
    return None


def _id_impacto_seleccionado(impactos: list[ImpactoInfo], nombre: str) -> int | None:
    """Busca el identificador de un impacto a partir de su nombre."""
    return id_impacto_desde_nombre(opciones_impacto(impactos), nombre)


def _id_vehiculo_por_nombre(vehiculos: list[VehiculoInfo], nombre: str) -> int | None:
    """Busca el identificador de un vehículo a partir de su nombre."""
    for vehiculo in vehiculos:
        if vehiculo.nombre_vehiculo == nombre:
            return vehiculo.id_vehiculo
    return None


def _id_comportamiento_por_nombre(
    comportamientos: list[ComportamientoInfo], nombre: str
) -> int | None:
    """Busca el identificador de un comportamiento a partir de su descripción."""
    for comportamiento in comportamientos:
        if comportamiento.comportamiento == nombre:
            return comportamiento.id_comportamiento
    return None


def _render_empresas(repositorio: CatalogosRepository, usuario: str) -> None:
    """Renderiza y procesa la gestión de empresas (RF-01).

    Args:
        repositorio: Repositorio de catálogos inyectado desde el punto de entrada.
        usuario: Usuario de la sesión (para el registro).
    """
    empresas = repositorio.listar_empresas()
    st.dataframe(filas_empresas(empresas), use_container_width=True, hide_index=True)

    col_crear, col_estado = st.columns(2)
    with col_crear, st.form("cat_empresa_crear"):
        nombre = st.text_input("Nueva empresa")
        if st.form_submit_button("Crear") and nombre:
            repositorio.crear_empresa(nombre, usuario)
            st.success("Creada.")
            st.rerun()
    with col_estado, st.form("cat_empresa_estado"):
        if empresas:
            seleccion = st.selectbox("Empresa", [empresa.nombre_empresa for empresa in empresas])
            accion = st.radio("Acción", ACCIONES_ESTADO, horizontal=True)
            if st.form_submit_button("Cambiar Estado"):
                id_empresa = _id_empresa_por_nombre(empresas, seleccion)
                if id_empresa is not None:
                    repositorio.cambiar_vigencia_empresa(id_empresa, vigencia_desde_accion(accion))
                    st.success(f"{accion}da.")
                    st.rerun()
        else:
            st.info("Sin empresas registradas.")

    with st.form("cat_empresa_renombrar"):
        editar = st.selectbox(
            "Editar nombre", [""] + [empresa.nombre_empresa for empresa in empresas]
        )
        nuevo = st.text_input("Nuevo nombre")
        if st.form_submit_button("Renombrar") and editar and nuevo:
            id_empresa = _id_empresa_por_nombre(empresas, editar)
            if id_empresa is not None:
                repositorio.renombrar_empresa(id_empresa, nuevo)
                st.success("Renombrada.")
                st.rerun()


def _render_vehiculos(repositorio: CatalogosRepository, usuario: str) -> None:
    """Renderiza y procesa la gestión de vehículos (RF-02).

    Args:
        repositorio: Repositorio de catálogos inyectado desde el punto de entrada.
        usuario: Usuario de la sesión (para el registro).
    """
    vehiculos = repositorio.listar_vehiculos()
    st.dataframe(filas_vehiculos(vehiculos), use_container_width=True, hide_index=True)

    col_crear, col_editar = st.columns(2)
    with col_crear, st.form("cat_vehiculo_crear"):
        nombre = st.text_input("Nuevo vehículo")
        if st.form_submit_button("Crear") and nombre:
            repositorio.crear_vehiculo(nombre, usuario)
            st.success("Creado.")
            st.rerun()
    with col_editar, st.form("cat_vehiculo_renombrar"):
        editar = st.selectbox(
            "Editar nombre", [""] + [vehiculo.nombre_vehiculo for vehiculo in vehiculos]
        )
        nuevo = st.text_input("Nuevo nombre")
        if st.form_submit_button("Renombrar") and editar and nuevo:
            id_vehiculo = _id_vehiculo_por_nombre(vehiculos, editar)
            if id_vehiculo is not None:
                repositorio.renombrar_vehiculo(id_vehiculo, nuevo)
                st.success("Renombrado.")
                st.rerun()


def _render_impactos(repositorio: CatalogosRepository, usuario: str) -> None:
    """Renderiza y procesa la gestión de niveles de impacto (RF-03).

    Args:
        repositorio: Repositorio de catálogos inyectado desde el punto de entrada.
        usuario: Usuario de la sesión (para el registro y la auditoría).
    """
    st.markdown("**Niveles de Impacto** — Clasificación de severidad de comportamientos.")
    impactos = repositorio.listar_impactos()
    st.dataframe(filas_impactos(impactos), use_container_width=True, hide_index=True)

    col_crear, col_editar = st.columns(2)
    with col_crear, st.form("cat_impacto_crear"):
        st.subheader("Nuevo Impacto")
        nombre = st.text_input("Nombre", key="cat_imp_nom")
        col_max, col_dias = st.columns(2)
        with col_max:
            maximo = st.number_input("Máximo ocurrencias", min_value=0, value=2, key="cat_imp_max")
        with col_dias:
            dias = st.number_input("Días reinicio", min_value=0, value=90, key="cat_imp_dias")
        if st.form_submit_button("Crear") and nombre:
            repositorio.crear_impacto(nombre, int(maximo), int(dias), usuario)
            st.success("Creado.")
            st.rerun()
    with col_editar:
        seleccion = st.selectbox(
            "Seleccionar impacto a editar",
            [""] + [impacto.impacto for impacto in impactos],
            key="cat_imp_edit_sel",
        )
        if seleccion:
            impacto = next(i for i in impactos if i.impacto == seleccion)
            with st.form("cat_impacto_editar"):
                st.subheader(f"✏️ Editando: {seleccion}")
                nuevo_nombre = st.text_input("Nombre", value=impacto.impacto, key="cat_imp_ed_nom")
                nuevo_max = st.number_input(
                    "Máximo ocurrencias",
                    min_value=0,
                    value=int(impacto.maximo),
                    key="cat_imp_ed_max",
                )
                nuevos_dias = st.number_input(
                    "Días reinicio",
                    min_value=0,
                    value=int(impacto.dias_maximo),
                    key="cat_imp_ed_dias",
                )
                if st.form_submit_button("Guardar cambios"):
                    repositorio.actualizar_impacto(
                        impacto.id_impacto,
                        nuevo_nombre,
                        int(nuevo_max),
                        int(nuevos_dias),
                        usuario,
                    )
                    st.success("Actualizado.")
                    st.rerun()


def _render_comportamientos(repositorio: CatalogosRepository, usuario: str) -> None:
    """Renderiza y procesa la gestión de comportamientos (RF-04).

    Args:
        repositorio: Repositorio de catálogos inyectado desde el punto de entrada.
        usuario: Usuario de la sesión (para el registro y la auditoría).
    """
    st.markdown("**Comportamientos** — Cada comportamiento está asociado a un nivel de impacto.")
    impactos = repositorio.listar_impactos()
    opciones = opciones_impacto(impactos)
    comportamientos = repositorio.listar_comportamientos()
    st.dataframe(filas_comportamientos(comportamientos), use_container_width=True, hide_index=True)

    col_crear, col_editar = st.columns(2)
    with col_crear, st.form("cat_comportamiento_crear"):
        st.subheader("Nuevo Comportamiento")
        descripcion = st.text_input("Descripción", key="cat_comp_nom")
        impacto_nombre = st.selectbox(
            "Nivel de Impacto", list(opciones.values()), key="cat_comp_imp"
        )
        if st.form_submit_button("Crear"):
            id_impacto = id_impacto_desde_nombre(opciones, impacto_nombre)
            if descripcion and id_impacto is not None:
                repositorio.crear_comportamiento(descripcion, id_impacto, usuario)
                st.success("Creado.")
                st.rerun()
    with col_editar:
        seleccion = st.selectbox(
            "Seleccionar comportamiento a editar",
            [""] + [comportamiento.comportamiento for comportamiento in comportamientos],
            key="cat_comp_edit_sel",
        )
        if seleccion:
            comportamiento = next(c for c in comportamientos if c.comportamiento == seleccion)
            with st.form("cat_comportamiento_editar"):
                st.subheader(f"✏️ Editando: {seleccion}")
                nueva_descripcion = st.text_input(
                    "Descripción", value=comportamiento.comportamiento, key="cat_comp_ed_desc"
                )
                impacto_actual = comportamiento.impacto
                nuevo_impacto = st.selectbox(
                    "Nivel de Impacto",
                    list(opciones.values()),
                    index=_indice_opcion(list(opciones.values()), impacto_actual),
                    key="cat_comp_ed_imp",
                )
                if st.form_submit_button("Guardar cambios"):
                    id_impacto = id_impacto_desde_nombre(opciones, nuevo_impacto)
                    if id_impacto is not None:
                        repositorio.actualizar_comportamiento(
                            comportamiento.id_comportamiento,
                            nueva_descripcion,
                            id_impacto,
                            usuario,
                        )
                        st.success("Actualizado.")
                        st.rerun()


def _render_detalles(repositorio: CatalogosRepository, usuario: str) -> None:
    """Renderiza y procesa la gestión de detalles de comportamiento (RF-05).

    Args:
        repositorio: Repositorio de catálogos inyectado desde el punto de entrada.
        usuario: Usuario de la sesión (para el registro y la auditoría).
    """
    st.markdown("**Detalle de Comportamientos** — Jerarquía completa de clasificación de eventos.")
    fuente = st.selectbox(
        "Filtrar por fuente", [ETIQUETA_TODAS_FUENTES, *FUENTES_DETALLE], key="cat_det_fuente"
    )
    fuente_filtro = None if fuente == ETIQUETA_TODAS_FUENTES else fuente
    detalles = repositorio.listar_detalles(fuente=fuente_filtro)
    st.dataframe(filas_detalles(detalles), use_container_width=True, hide_index=True)
    st.caption(f"Mostrando hasta {LIMITE_DETALLES} registros de {len(detalles)}")

    st.markdown("---")
    comportamientos = repositorio.listar_comportamientos()
    opciones_comp = opciones_comportamiento(comportamientos)

    col_crear, col_editar = st.columns(2)
    with col_crear, st.form("cat_detalle_crear"):
        st.subheader("Nuevo Detalle")
        fuente_n = st.selectbox("Fuente", FUENTES_DETALLE, key="cat_det_fuente_n")
        tipo = st.text_input("Tipo", key="cat_det_tipo")
        servicios = st.text_input("Servicios", key="cat_det_serv")
        jerarquia_1 = st.text_input("Jerarquía 1", key="cat_det_j1")
        jerarquia_2 = st.text_input("Jerarquía 2", key="cat_det_j2")
        jerarquia_3 = st.text_input("Jerarquía 3", key="cat_det_j3")
        jerarquia_4 = st.text_input("Jerarquía 4", key="cat_det_j4")
        comp_opcion = st.selectbox(
            "Comportamiento asociado",
            list(opciones_comp.keys()),
            format_func=lambda clave: opciones_comp[clave],
            key="cat_det_comp",
        )
        if (
            st.form_submit_button("Crear")
            and fuente_n
            and tipo
            and servicios
            and jerarquia_1
            and comp_opcion
        ):
            datos = DatosDetalleComportamiento(
                fuente=fuente_n,
                tipo=tipo,
                servicios=servicios,
                jerarquia_1=jerarquia_1,
                jerarquia_2=jerarquia_2 or None,
                jerarquia_3=jerarquia_3 or None,
                jerarquia_4=jerarquia_4 or None,
                id_comportamiento=int(comp_opcion),
            )
            repositorio.crear_detalle(datos, usuario)
            st.success("Creado.")
            st.rerun()
    with col_editar:
        seleccion = st.selectbox(
            "Seleccionar ID a editar",
            [""] + [str(detalle.id_jerarquia) for detalle in detalles],
            key="cat_det_edit_sel",
        )
        if seleccion:
            detalle = next(d for d in detalles if d.id_jerarquia == int(seleccion))
            with st.form("cat_detalle_editar"):
                st.subheader(f"✏️ Editando ID {seleccion}")
                nueva_fuente = st.selectbox(
                    "Fuente",
                    FUENTES_DETALLE,
                    index=_indice_opcion(list(FUENTES_DETALLE), detalle.fuente),
                    key="cat_det_ed_f",
                )
                nuevo_tipo = st.text_input("Tipo", value=detalle.tipo, key="cat_det_ed_tipo")
                nuevos_servicios = st.text_input(
                    "Servicios", value=detalle.servicios, key="cat_det_ed_serv"
                )
                nueva_j1 = st.text_input(
                    "Jerarquía 1", value=detalle.jerarquia_1, key="cat_det_ed_j1"
                )
                nueva_j2 = st.text_input(
                    "Jerarquía 2", value=detalle.jerarquia_2 or "", key="cat_det_ed_j2"
                )
                nueva_j3 = st.text_input(
                    "Jerarquía 3", value=detalle.jerarquia_3 or "", key="cat_det_ed_j3"
                )
                nueva_j4 = st.text_input(
                    "Jerarquía 4", value=detalle.jerarquia_4 or "", key="cat_det_ed_j4"
                )
                comp_opcion = st.selectbox(
                    "Comportamiento asociado",
                    list(opciones_comp.keys()),
                    index=_indice_opcion(
                        list(opciones_comp.keys()), str(detalle.id_comportamiento)
                    ),
                    format_func=lambda clave: opciones_comp[clave],
                    key="cat_det_ed_comp",
                )
                if st.form_submit_button("Guardar cambios"):
                    datos = DatosDetalleComportamiento(
                        fuente=nueva_fuente,
                        tipo=nuevo_tipo,
                        servicios=nuevos_servicios,
                        jerarquia_1=nueva_j1,
                        jerarquia_2=nueva_j2 or None,
                        jerarquia_3=nueva_j3 or None,
                        jerarquia_4=nueva_j4 or None,
                        id_comportamiento=int(comp_opcion),
                    )
                    repositorio.actualizar_detalle(detalle.id_jerarquia, datos, usuario)
                    st.success("Actualizado.")
                    st.rerun()


def render_catalogos(repositorio: CatalogosRepository | None = None) -> None:
    """Renderiza la pestaña completa de catálogos.

    Args:
        repositorio: Repositorio de catálogos a usar. Si es ``None`` se construye
            uno con la configuración por defecto; inyectarlo facilita las
            pruebas.
    """
    repositorio = repositorio or CatalogosRepository()
    usuario = st.session_state.get("usuario", USUARIO_POR_DEFECTO)

    st.title(TITULO)
    tab_empresas, tab_vehiculos, tab_impactos, tab_comportamientos, tab_detalles = st.tabs(
        [
            "🏢 Empresas",
            "🚌 Vehículos",
            "⚠️ Impactos",
            "📋 Comportamientos",
            "🔍 Detalle Comportamiento",
        ]
    )
    with tab_empresas:
        _render_empresas(repositorio, usuario)
    with tab_vehiculos:
        _render_vehiculos(repositorio, usuario)
    with tab_impactos:
        _render_impactos(repositorio, usuario)
    with tab_comportamientos:
        _render_comportamientos(repositorio, usuario)
    with tab_detalles:
        _render_detalles(repositorio, usuario)


__all__ = [
    "ACCIONES_ESTADO",
    "ACCION_ACTIVAR",
    "ACCION_INACTIVAR",
    "ETIQUETA_TODAS_FUENTES",
    "FUENTES_DETALLE",
    "TITULO",
    "USUARIO_POR_DEFECTO",
    "filas_comportamientos",
    "filas_detalles",
    "filas_empresas",
    "filas_impactos",
    "filas_vehiculos",
    "id_impacto_desde_nombre",
    "opciones_comportamiento",
    "opciones_impacto",
    "render_catalogos",
    "vigencia_desde_accion",
]
