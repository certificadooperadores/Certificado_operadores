# Documentación de Tablas, Relaciones y Columnas

> Documento generado a partir de la Base de Datos `Operadores_bd`.

---

## 1. Dimensiones (Catálogos)

### 1.1 `dim_vigencia_registro` — Estados de vigencia

| Columna | Objetivo |
|---------|----------|
| `id_vigencia` | PK (1 = vigente, 2 = anulado) |
| `condicion_fila` | Nombre del estado |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 1.2 `dim_empresa` — Empresas operadoras (Git, Bnm, Etm, Unm)

| Columna | Objetivo |
|---------|----------|
| `id_empresa` | PK |
| `nombre_empresa` | Nombre de la empresa |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 1.3 `dim_vehiculo` — Tipos de vehículo

| Columna | Objetivo |
|---------|----------|
| `id_vehiculo` | PK (1 = articulado, 2 = padron, 3 = complementario, 4 = auxiliar) |
| `nombre_vehiculo` | Nombre del tipo |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 1.4 `dim_tipo_evento` — Tipos de evento del historial

| id | Evento |
|----|--------|
| 1 | certificacion |
| 2 | reactivacion |
| 3 | renovacion |
| 4 | observacion |
| 5 | restriccion medica |
| 6 | suspension |
| 7 | cancelacion |
| 8 | advertencia |
| 9 | condicionamiento |

| Columna | Objetivo |
|---------|----------|
| `id_tipo_evento` | PK |
| `nombre_evento` | Nombre del evento |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 1.5 `dim_perfil_tipologia` — Perfiles con autorización de vehículos

| Columna | Objetivo |
|---------|----------|
| `id_perfil_tipologia` | PK (1-4) |
| `autoriza_articulado` | bool: puede operar articulado |
| `autoriza_padron` | bool: puede operar padron |
| `autoriza_complementario` | bool: puede operar complementario |
| `autoriza_auxiliar` | bool: puede operar auxiliar |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 1.6 `dim_persona` — Personas por cédula

| Columna | Objetivo |
|---------|----------|
| `id_persona` | PK = **número de cédula** |
| `nombres` | Nombres |
| `primer_apellido` | Primer apellido |
| `segundo_apellido` | Segundo apellido |
| `genero` | M / F / OTRO |
| `fecha_de_nacimiento` | Fecha de nacimiento |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 1.7 `dim_codigo` — Códigos de operación (tabla puente central)

| Columna | Objetivo |
|---------|----------|
| `id_codigo` | PK = **código de operación** |
| `id_persona` | FK → `dim_persona` (cédula) |
| `id_empresa` | FK → `dim_empresa` |
| `id_perfil_tipologia` | FK → `dim_perfil_tipologia` |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

---

## 2. Dimensiones de Comportamiento

### 2.1 `dim_impacto` — Niveles de severidad

| id | impacto | maximo | dias_maximo |
|----|---------|--------|-------------|
| 1 | Grave | 1 | 0 |
| 2 | Alto | 2 | 120 |
| 3 | Medio | 2 | 90 |
| 4 | Bajo | 2 | 60 |
| 5 | informativo | 0 | 0 |

| Columna | Objetivo |
|---------|----------|
| `id_impacto` | PK |
| `impacto` | Nombre del nivel de severidad |
| `maximo` | Ocurrencias máximas antes de reincidencia |
| `dias_maximo` | Ventana de días para reincidencia |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 2.2 `dim_comportamiento` — Comportamientos generales (45 registros)

| Columna | Objetivo |
|---------|----------|
| `id_comportamiento` | PK |
| `comportamiento` | Descripción general (ej. "se presenta alicorado o drogado") |
| `id_impacto` | FK → `dim_impacto` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

### 2.3 `dim_detalle_comportamiento` — Jerarquía completa de clasificación (737 registros)

| Columna | Objetivo |
|---------|----------|
| `id_jerarquia` | PK |
| `fuente` | Origen (jerarquia hgi, pqrs, secretaría de movilidad) |
| `descripcion_comportamiento` | Jerarquía completa (ej. "metrocali::salidas::por operador::omite parada") |
| `tipo` | Clasificación de alto nivel |
| `servicios` | Categoría de servicio |
| `jerarquia_1` a `jerarquia_4` | Niveles jerárquicos |
| `id_comportamiento` | FK → `dim_comportamiento` |
| `fecha_registro` | Fecha de carga |
| `usuario_registra` | Usuario que registró |

---

## 3. Tablas de Hechos (Transaccionales)

### 3.1 `fact_licencias` — Licencias de conducción

| Columna | Objetivo |
|---------|----------|
| `id_hecho_licencia` | PK |
| `id_codigo` | FK → `dim_codigo` |
| `tipo` | Tipo de licencia (C2, C3...) |
| `vencimiento` | Fecha de vencimiento |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de registro |
| `usuario_registra` | Usuario que registró |

### 3.2 `fact_eventos_operador` — Historial de eventos

| Columna | Objetivo |
|---------|----------|
| `id_hecho_evento` | PK |
| `id_codigo` | FK → `dim_codigo` |
| `id_tipo_evento` | FK → `dim_tipo_evento` (1-9) |
| `id_vehiculo_evaluado` | FK → `dim_vehiculo` |
| `fecha_certificado` | Fecha de certificación |
| `fecha_retiro` | Fecha de retiro/cancelación |
| `fecha_prueba` | Fecha de prueba |
| `evaluador` | Evaluador del certificado |
| `fecha_notificacion_retiro` | Fecha de notificación de retiro |
| `fecha_suspension` | Fecha de suspensión |
| `restriccion_medica` | Descripción de restricción médica |
| `elemento_de_proteccion` | Elemento de protección |
| `inicio_restriccion_medica` | Inicio de restricción |
| `fin_restriccion_medica` | Fin de restricción |
| `fecha_observacion` | Fecha de observación/advertencia/condicionamiento |
| `observacion` | Texto libre / motivo |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de registro |
| `usuario_registra` | Usuario que registró |

### 3.3 `fact_comportamiento` — Comportamientos registrados (313,000 registros)

| Columna | Objetivo |
|---------|----------|
| `id_hecho_comportamiento` | PK |
| `id_jerarquia` | FK → `dim_detalle_comportamiento` |
| `fuente` | Origen del registro |
| `descripcion_comportamiento` | Descripción original |
| `caso_bitacora_ticket` | N° de caso/ticket |
| `fecha_evento` | Fecha del evento |
| `hora_evento` | Hora del evento |
| `nota` | Nota / descripción |
| `vehiculo` | Número MC del vehículo |
| `viaje` | Número de viaje |
| `tarea` | Número de tarea |
| `id_codigo` | FK → `dim_codigo` (operador) |
| `ruta` | Ruta |
| `sitio_salida` | Sitio de salida |
| `sitio_novedad` | Sitio de novedad |
| `numero_lesionados` | Número de lesionados |
| `observacion_concesionario` | Observación del concesionario |
| `respuesta_mc` | Respuesta Metrocali |
| `responsable_pqrs_cot` | Responsable PQRS/COT |
| `direccion_infraccion` | Dirección de la infracción |
| `clase_servicio` | Clase de servicio |
| `tipo_servicio` | Tipo de servicio |
| `fuente_infraccion` | Fuente de la infracción |
| `placa` | Placa del vehículo |
| `id_vigencia` | FK → `dim_vigencia_registro` |
| `fecha_registro` | Fecha de registro |
| `usuario_registra` | Usuario que registró |

### 3.4 `fact_reincidencia` — Casos de reincidencia

| Columna | Objetivo |
|---------|----------|
| `id_reincidencia` | PK |
| `id_codigo` | Código del operador |
| `id_impacto` | FK → `dim_impacto` |
| `id_comportamiento` | FK → `dim_comportamiento` |
| `fecha_inicio` | Fecha del primer evento |
| `fecha_fin` | Fecha del último evento |
| `cantidad` | Número de ocurrencias |
| `resumen` | Resumen de casos y fechas |
| `determinacion_mc` | Acción Metrocali (advertencia, condicionamiento, suspensión, cancelación) |
| `id_hecho_evento` | Evento creado en `fact_eventos_operador` (permite modificar sin duplicar) |
| `estado` | Estado del caso |
| `usuario_registra` | Usuario que registró |
| `fecha_registro` | Fecha de registro |

### 3.5 `reincidencia_detalle` — Eventos que componen cada caso

| Columna | Objetivo |
|---------|----------|
| `id_reincidencia` | FK → `fact_reincidencia` |
| `id_hecho_comportamiento` | FK → `fact_comportamiento` |

---

## 4. Tablas del Sistema

### 4.1 `dim_usuarios` — Cuentas de acceso

| Columna | Objetivo |
|---------|----------|
| `id_usuario` | PK |
| `usuario` | Nombre de usuario (único) |
| `password_hash` | Hash bcrypt de la contraseña |
| `rol` | Gestor / Administrador / Super Administrador |
| `estado` | Activo / Inactivo |
| `fecha_registro` | Fecha de creación |

### 4.2 `log_auditoria` — Registro de acciones

| Columna | Objetivo |
|---------|----------|
| `id_log` | PK |
| `usuario` | Quién realizó la acción |
| `accion` | Tipo de acción |
| `detalles` | Descripción de la acción |
| `fecha_registro` | Fecha de la acción |

### 4.3 `dim_version_bd` — Versión del backup activo

| Columna | Objetivo |
|---------|----------|
| `id_version` | PK |
| `fecha_backup` | Fecha del backup |
| `archivo_origen` | Archivo de origen |
| `fecha_restauracion` | Fecha de restauración |
| `restaurado_por` | Usuario que restauró |

---

## 5. Relaciones del Modelo Estrella

```
dim_persona ←(1:N)→ dim_codigo ←(N:1)→ dim_empresa
                              ←(N:1)→ dim_perfil_tipologia
                              ←(N:1)→ dim_vigencia_registro

dim_codigo ←(1:N)→ fact_licencias
dim_codigo ←(1:N)→ fact_eventos_operador
dim_codigo ←(1:N)→ fact_comportamiento

dim_tipo_evento ←(1:N)→ fact_eventos_operador
dim_vehiculo    ←(1:N)→ fact_eventos_operador

dim_impacto ←(1:N)→ dim_comportamiento ←(1:N)→ dim_detalle_comportamiento
dim_detalle_comportamiento ←(1:N)→ fact_comportamiento

fact_comportamiento ←(N:N)→ fact_reincidencia (vía reincidencia_detalle)
fact_reincidencia → dim_impacto / dim_comportamiento
fact_reincidencia → fact_eventos_operador (id_hecho_evento)
```

### Lista de Llaves Foráneas (22)

| Tabla | Referencia |
|-------|-----------|
| `dim_codigo.id_persona` | `dim_persona` |
| `dim_codigo.id_empresa` | `dim_empresa` |
| `dim_codigo.id_perfil_tipologia` | `dim_perfil_tipologia` |
| `dim_codigo.id_vigencia` | `dim_vigencia_registro` |
| `dim_comportamiento.id_impacto` | `dim_impacto` |
| `dim_detalle_comportamiento.id_comportamiento` | `dim_comportamiento` |
| `dim_empresa.id_vigencia` | `dim_vigencia_registro` |
| `dim_perfil_tipologia.id_vigencia` | `dim_vigencia_registro` |
| `dim_persona.id_vigencia` | `dim_vigencia_registro` |
| `dim_tipo_evento.id_vigencia` | `dim_vigencia_registro` |
| `fact_comportamiento.id_jerarquia` | `dim_detalle_comportamiento` |
| `fact_comportamiento.id_codigo` | `dim_codigo` |
| `fact_eventos_operador.id_codigo` | `dim_codigo` |
| `fact_eventos_operador.id_tipo_evento` | `dim_tipo_evento` |
| `fact_eventos_operador.id_vehiculo_evaluado` | `dim_vehiculo` |
| `fact_eventos_operador.id_vigencia` | `dim_vigencia_registro` |
| `fact_licencias.id_vigencia` | `dim_vigencia_registro` |
| `fact_licencias.id_codigo` | `dim_codigo` |
| `fact_reincidencia.id_impacto` | `dim_impacto` |
| `fact_reincidencia.id_comportamiento` | `dim_comportamiento` |
| `reincidencia_detalle.id_reincidencia` | `fact_reincidencia` |
| `reincidencia_detalle.id_hecho_comportamiento` | `fact_comportamiento` |
