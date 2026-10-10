"""Módulo heredado (DEPRECADO) — Gestión de certificados (spec 008).

Este archivo mezclaba la vista de Streamlit con más de 15 consultas SQL directas
y transacciones a ``fact_eventos_operador``, ``dim_codigo`` y ``dim_persona``.
En la spec 008 se **deprecó**: toda la funcionalidad se movió al paquete
``modulos/gestion_certificados``, cuya interfaz consume
:class:`~certificado_operadores.infra.certificados_repository.CertificadosRepository`
sin sentencias SQL en la vista.

Se conserva únicamente como redirección para no romper enlaces antiguos; no
debe usarse en código nuevo.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from modulos.gestion_certificados.ui import render_gestion_certificados

render_gestion_certificados()
