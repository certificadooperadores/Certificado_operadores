"""Módulo heredado (DEPRECADO) — Corrección de registros (spec 006).

Este archivo duplicaba parcialmente la corrección de registros con acceso
directo a la base de datos (consultas crudas sobre ``fact_eventos_operador``).
En la spec 006 se **deprecó**: toda la funcionalidad se movió al paquete
``modulos/correccion_registros``, cuya interfaz consume
:class:`~certificado_operadores.infra.eventos_repository.EventosRepository` sin
sentencias SQL en la vista.

Se conserva únicamente como redirección para no romper enlaces antiguos; no
debe usarse en código nuevo.

Autor: Ing. Miguel Angel Ortiz Roldan
"""

from modulos.correccion_registros.ui import render_correccion_registros

render_correccion_registros()
