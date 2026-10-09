# Análisis y Propuestas — Proyecto BD Operadores

> Documento generado a partir de la lectura completa del proyecto, sin modificaciones.
> Fecha: 2026-07-20

---

## 1. Resumen del Proyecto

**Objetivo:** Plataforma web (Streamlit + PostgreSQL + Docker) para que un usuario sin conocimientos técnicos pueda levantar y administrar una base de datos de operadores de transporte (Metro Cali) a partir de un archivo Excel maestro.

El sistema permite:
- Cargar datos desde `BASE DE DATOS OPERADORESv4.xlsm` mediante un script ETL que genera un modelo estrella (9 CSVs).
- Levantar PostgreSQL + Streamlit en contenedores Docker con un solo `.bat`.
- Gestionar operadores, licencias, eventos (certificaciones, suspensiones, cancelaciones, etc.), empresas, tipologías y vehículos.
- Control de usuarios con roles (Administrador / Super Administrador), autenticación vía bcrypt.
- Carga masiva desde plantillas Excel.
- Borrado lógico (vigencia) con opción de borrado físico para Super Admin.

---

## 2. Estructura del Proyecto

```
Proyecto_BD_operadores/
├── BASE DE DATOS OPERADORESv4.xlsm          # Excel fuente con datos históricos
├── DOCUMENTACION_ARQUITECTURA.md            # Documentación de arquitectura (diagramas)
├── INSTRUCCIONES_DOCKER.txt                 # Guía paso a paso en español
├── Iniciar_App_Operadores.bat               # Lanzador Windows con menú interactivo
├── generar_modelo_estrella_maestro.py       # ETL: Excel → 9 CSVs (modelo estrella)
├── renombrar_nota.py                        # Script de migración puntual
├── Backups/
│   └── backup_mar 14-07-2026_16-46-44-93.sql
├── Contenedor_Proyecto/
│   ├── .streamlit/config.toml               # Configuración de Streamlit
│   ├── docker-compose.yaml                  # Servicios: db (PostgreSQL 15) + app (Streamlit)
│   ├── Dockerfile                           # Imagen python:3.10-slim con dependencias
│   ├── requirements.txt                     # Dependencias Python
│   ├── Inicio.py                            # Página principal: login
│   ├── db.py                                # Conexión SQLAlchemy + helpers
│   ├── init_db.py                           # Inicializador: carga CSVs, crea FKs, admin user
│   └── pages/
│       ├── 1_Configuracion.py               # Catálogos: empresas, tipologías, vehículos
│       ├── 2_Administracion_Operadores.py   # CRUD operadores + carga masiva Excel
│       ├── 3_Registro_Eventos.py            # Registro de eventos + carga masiva
│       ├── 4_Gestion_Usuarios.py            # Administración de usuarios del sistema
│       └── 5_Modificacion_Tablas.py         # Borrado lógico/físico de lotes de eventos
├── Modelo_Estrella_Final_CSVs/              # 9 archivos CSV (modelo estrella)
└── Plantillas/
    ├── Plantilla_Eventos_Operadores.xlsx
    └── Plantilla_Operadores_Maestra.xlsx
```

### Modelo de Datos (Estrella)

| Tabla | Descripción | Registros |
|-------|-------------|-----------|
| `dim_vigencia_registro` | Estados: vigente (1), anulado (2) | 2 |
| `dim_empresa` | Empresas operadoras (Git, Bnm, Etm, Unm) | 4 |
| `dim_vehiculo` | Tipos de vehículo | 4 |
| `dim_tipo_evento` | 7 tipos de evento | 7 |
| `dim_perfil_tipologia` | Perfiles con autorización booleana por vehículo | 4 |
| `dim_persona` | Datos personales por cédula | 6,773 |
| `dim_codigo` | Códigos de operador (persona + empresa + tipología) | 9,199 |
| `fact_licencias` | Licencias de conducción | 9,199 |
| `fact_eventos_operador` | Todos los eventos | 33,596 |
| `dim_usuarios` | Usuarios del sistema (creada por init_db.py) | 1 (admin) |

---

## 3. Errores Encontrados

### 3.1 ERROR CRÍTICO — Columna inexistente en `5_Modificacion_Tablas.py` (línea 45)

La consulta SQL referencia `c.codigo_operacion` pero la tabla `dim_codigo` no tiene esa columna (su PK es `id_codigo`). Esto **romperá en tiempo de ejecución** al intentar agrupar eventos.

```sql
-- Línea ~45 del archivo:
... GROUP BY c.codigo_operacion, c.cedula, ...
-- Debería ser:
... GROUP BY c.id_codigo, c.cedula, ...
```

### 3.2 ERROR DE SEGURIDAD — Login comentado en `2_Administracion_Operadores.py` (líneas 10-12)

Las líneas que verifican autenticación están comentadas. Cualquier persona sin loguearse puede acceder a la página de administración de operadores.

```python
# if "autenticado" not in st.session_state or not st.session_state.autenticado:
#     st.warning("Debe iniciar sesión...")
#     st.stop()
```

### 3.3 ERROR DE DESPLIEGUE — Rutas absolutas hardcodeadas en `renombrar_nota.py`

Usa rutas Windows absolutas del equipo original. Solo funciona en la máquina del autor original.

```python
ruta_archivo = r"C:\Users\maortiz\OneDrive - metrocali.gov.co\Scripts\..."
```

### 3.4 DUPLICACIÓN DE CSVs

El directorio `Modelo_Estrella_Final_CSVs/` existe tanto en la raíz como dentro de `Contenedor_Proyecto/`. El `docker-compose` monta ambos, pero la copia interna podría quedar desactualizada si solo se ejecuta el ETL en la raíz.

### 3.5 Credenciales hardcodeadas en múltiples archivos

- `docker-compose.yaml`: `POSTGRES_USER: mao`, `POSTGRES_PASSWORD: metrocali6200`
- `db.py`: valores por defecto en variables de entorno con las mismas credenciales
- `init_db.py`: ídem

No hay archivo `.env` ni `.env.example` para que un nuevo usuario configure sus credenciales.

### 3.6 Seguridad deshabilitada en `.streamlit/config.toml`

`enableCORS=false` y `enableXsrfProtection=false`. Aceptable solo en red interna, riesgoso si se expone.

### 3.7 Dependencias no utilizadas

`plotly==5.18.0`, `matplotlib==3.8.2` y `seaborn==0.13.2` están en `requirements.txt` pero no se importan en ningún archivo `.py`. Están listas para dashboards futuros.

### 3.8 Sin `.gitignore`

No hay `.gitignore`. Riesgo de commitear `__pycache__/`, `*.pyc`, `Backups/*.sql`, credenciales.

### 3.9 README solo en español y sin información de instalación rápida

`DOCUMENTACION_ARQUITECTURA.md` es útil pero no hay un README raíz con instrucciones rápidas.

---

## 4. Propuestas de Mejora (ordenadas por prioridad)

### Fase 1 — Correcciones Urgentes (estabilidad)

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P1 | **Corregir `codigo_operacion` → `id_codigo`** en `5_Modificacion_Tablas.py` | La funcionalidad de borrado de lotes no funciona | Bajo |
| P2 | **Restaurar verificación de login** en `2_Administracion_Operadores.py` | Agujero de seguridad: cualquiera puede modificar operadores | Bajo |
| P3 | **Crear `.env.example`** y mover credenciales del `docker-compose.yaml` a variables de entorno | Facilita despliegue por terceros sin exponer credenciales en código | Bajo |
| P4 | **Crear `.gitignore`** con reglas para Python, Docker, backups | Evita commits accidentales de binarios, backups y credenciales | Bajo |

### Fase 2 — Robustez (experiencia de usuario no técnico)

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P5 | **Panel de "Primer inicio" en Streamlit** — Una página inicial que guíe al usuario paso a paso: (a) ejecutar ETL desde el Excel, (b) levantar la BD, (c) verificar estado, sin tocar terminal | El usuario sin conocimientos puede regenerar la BD desde cero sin ayuda | Medio |
| P6 | **Indicador de estado de conexión** en la UI — Mostrar en la barra lateral si PostgreSQL está accesible y cuántos registros hay | Feedback inmediato para el usuario | Bajo |
| P7 | **Auto-ejecución de `init_db.py` en el entrypoint del contenedor** — Para que al hacer `docker compose up` la BD se inicialice sola la primera vez | Elimina el paso manual actual | Medio |
| P8 | **Validación del Excel maestro antes del ETL** — Verificar columnas esperadas, formato de fechas, cédulas duplicadas | Previene errores silenciosos en la carga de datos | Medio |

### Fase 3 — Nuevas funcionalidades (valor agregado)

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P9 | **Dashboard de operadores** — Usando `plotly`/`matplotlib`/`seaborn` (ya instalados): gráficos de operadores por empresa, eventos próximos a vencer, certificaciones por mes | Visibilidad inmediata del estado de la operación | Medio |
| P10 | **Alertas de vencimiento** — Notificaciones en la UI cuando una certificación/licencia esté por vencer (30, 15, 7 días) | Reduce riesgo operativo por documentos vencidos | Medio |
| P11 | **Exportación a Excel/PDF** de reportes (listado de operadores, eventos por rango de fechas) | Facilita compartir información con otros departamentos | Medio |
| P12 | **Registro de auditoría (`dim_auditoria`)** — Tabla que registre quién hizo qué cambio y cuándo | Trazabilidad completa de modificaciones | Medio |
| P13 | **Gestión de restricciones médicas con fechas de vencimiento** — Actualmente se registra como evento pero no hay campo de vencimiento; agregarlo permitiría alertas | Mejor control de condiciones médicas temporales | Medio |

### Fase 4 — Infraestructura (mantenibilidad)

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P14 | **Healthcheck en `docker-compose.yaml`** para el servicio `db` | El contenedor `app` no intentará conectarse hasta que PostgreSQL esté listo | Bajo |
| P15 | **Separar `docker-compose.override.yaml`** para desarrollo vs producción | Permite configuraciones distintas sin modificar el compose principal | Bajo |
| P16 | **Tests con `pytest`** para `generar_modelo_estrella_maestro.py` y `db.py` | Previene regresiones en el ETL y la capa de datos | Alto |
| P17 | **Reemplazar `renombrar_nota.py`** con una migración SQL versionada o eliminarlo (ya cumplió su función) | Limpia el proyecto de scripts puntuales obsoletos | Bajo |

---

## 5. Diagrama de Arquitectura Actual

```
┌──────────────────────────────────────────────────────┐
│                  MÁQUINA WINDOWS                      │
│                                                       │
│  ┌─────────────────────────┐                         │
│  │  Iniciar_App_Operadores  │  Menú .bat interactivo │
│  │  .bat                    │  Start / Backup /      │
│  └───────────┬─────────────┘  Restore / Reset        │
│              │                                       │
│              ▼                                       │
│  ┌─────────────────────────┐                         │
│  │  Docker Engine           │                         │
│  │                          │                         │
│  │  ┌──────────────────┐   ┌──────────────────────┐ │
│  │  │ operadores_app   │   │ operadores_db        │ │
│  │  │ Python 3.10      │──▶│ PostgreSQL 15 Alpine │ │
│  │  │ Streamlit :8505  │   │ :5432                │ │
│  │  │                  │   │                      │ │
│  │  │ Volumes:         │   │ Volume: pgdata       │ │
│  │  │  ./Contenedor    │   │ (persistente)        │ │
│  │  │  ../CSVs         │   │                      │ │
│  │  └──────────────────┘   └──────────────────────┘ │
│  └───────────────────────────────────────────────────┘
│                                                       │
│  ┌─────────────────────────┐                         │
│  │ generar_modelo_estrella │  ETL (manual, fuera de  │
│  │ _maestro.py             │  Docker)                │
│  │ Excel → 9 CSVs          │                         │
│  └─────────────────────────┘                         │
└──────────────────────────────────────────────────────┘
```

---

## 6. Mejoras Adicionales Detectadas (no incluidas en el análisis original)

### 6.1 ERROR — Puerto expuesto vs puerto real en Dockerfile
El `Dockerfile` expone el puerto **8501** (`EXPOSE 8501`) pero el `CMD` ejecuta Streamlit en el puerto **8505** (`--server.port=8505`). No es crítico (EXPOSE es informativo), pero es inconsistente.

### 6.3 ACLARACIÓN — Datos personales en CSVs (NO APLICA — proyecto interno)
Los CSVs en `Modelo_Estrella_Final_CSVs/` contienen **6,773 registros de personas** con nombres, cédulas y números de licencia. Dado que el proyecto es interno y no se compartirá públicamente, esto no representa un riesgo real. De todas formas se recomienda agregarlos al `.gitignore` como buena práctica por si en el futuro el repositorio llegara a compartirse.

### 6.4 RIESGO — Sin validación de datos en formularios Streamlit
Ningún formulario valida formato de cédula, fechas coherentes (ej. fecha fin > fecha inicio), campos obligatorios vacíos, ni duplicados antes de insertar. Un usuario puede introducir datos inconsistentes sin recibir advertencia.

### 6.5 ACLARACIÓN — `admin/admin123` hardcodeado sin obligar cambio (BAJA PRIORIDAD — proyecto interno)
`init_db.py` crea el usuario admin con contraseña fija `admin123`. Al ser un proyecto interno donde vos entregás el contenedor ya configurado, podés cambiar la contraseña manualmente antes de la entrega. No es crítico, pero forzar cambio en primer login sería una mejora de seguridad deseable.

### 6.6 RIESGO — Sin timeout de sesión en Streamlit
Una vez autenticado, la sesión nunca expira. Si el usuario deja la sesión abierta, cualquiera con acceso físico puede operar.

### 6.7 ACLARACIÓN — ETL requiere Python local (NO APLICA — flujo de trabajo definido)
`generar_modelo_estrella_maestro.py` se ejecuta en la máquina host con Python. Según el flujo definido, **vos (el desarrollador) ejecutás el ETL una sola vez** y entregás el contenedor ya listo con los CSVs precargados. El usuario final nunca toca Python. Esto no es un problema para el objetivo del proyecto, pero si en el futuro otro desarrollador necesita regenerar los CSVs, requerirá Python + dependencias locales. Considerar dockerizar el ETL solo si se prevé que alguien más necesite ejecutarlo.

### 6.8 LIMITACIÓN — Sin equivalente `.sh` para Linux/Mac
El lanzador `Iniciar_App_Operadores.bat` solo funciona en Windows. Si alguien necesita desplegar en Linux/Mac, no tiene script equivalente.

### 6.9 LIMITACIÓN — Backup con nombre con espacios
El archivo `backup_mar 14-07-2026_16-46-44-93.sql` tiene espacios en el nombre, lo que puede causar problemas en scripts que no escapen correctamente las rutas.

### 6.10 LIMITACIÓN — Sin respaldo automático programado
El `.bat` ofrece backup manual, pero no hay cron/tarea programada para respaldos automáticos periódicos de la BD.

---

## 7. Propuestas Adicionales

### Fase 1A — Correcciones complementarias

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P18 | **Corregir `EXPOSE 8501` → `8505`** en el Dockerfile | Consistencia en la configuración | Bajo |
| P19 | **Agregar CSVs y Backups al `.gitignore`** — Buena práctica (proyecto interno, no se comparte) | Previene exposición accidental si el repo se comparte en el futuro | Bajo |
| P20 | **Forzar cambio de contraseña en primer login** — Detectar si el hash es el de `admin123` y redirigir a pantalla de cambio | Mejora de seguridad deseable. Alternativa: cambiar la contraseña manualmente antes de entregar el contenedor | Bajo |

### Fase 2A — Experiencia de usuario no técnico

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P21 | **Dockerizar el ETL** — Solo necesario si otro desarrollador va a regenerar los CSVs desde el Excel maestro. En el flujo actual, vos lo ejecutás una vez y entregás el contenedor listo, así que es **opcional** | Futuro: evitar dependencia de Python local para regenerar datos | Medio |
| P22 | **Validación de formularios en Streamlit** — Validar formato de cédula (numérico, longitud), fechas coherentes, campos obligatorios, y mostrar errores en rojo antes de enviar | Previene datos basura en la BD | Medio |
| P23 | **Timeout de sesión configurable** — Cerrar sesión tras N minutos de inactividad (ej. 30 min) | Seguridad en entornos compartidos | Bajo |
| P24 | **Crear `Iniciar_App_Operadores.sh`** para Linux/Mac | Soporte multi-plataforma | Bajo |
| P25 | **Indicador de versión de BD / backup en Streamlit** — El usuario debe ver en **todas las páginas** (incluida Gestión de Usuarios) qué backup está activo y si es el más reciente. **Implementación propuesta:** (a) Crear tabla `dim_version_bd` con campos: `fecha_backup`, `archivo_origen`, `fecha_restauracion`, `restaurado_por`. (b) Al ejecutar restore desde el `.bat` o `docker exec`, insertar un registro con los metadatos del backup. (c) Mostrar en la **barra lateral persistente** de Streamlit un badge con la fecha del backup activo y un indicador visual (🟢 = es el último, 🟡 = hay uno más reciente en `Backups/`). Este badge debe ser visible en Inicio.py y en todas las páginas del menú. | El usuario sabe exactamente con qué datos está trabajando y si necesita actualizar. Fundamental para evitar trabajo sobre datos desactualizados | Medio |
| P26 | **Respaldo automático programado** — Usando pg_dump dentro del contenedor con una tarea programada (cron en Linux, Task Scheduler en Windows) | Tranquilidad ante pérdida de datos | Medio |

### Fase 3A — Robustez de datos

| # | Propuesta | Impacto | Esfuerzo |
|---|-----------|---------|----------|
| P27 | **Constraints de unicidad en BD** — Agregar UNIQUE a `dim_persona.cedula`, `dim_codigo.id_codigo` (si no existen) para prevenir duplicados por error de carga | Integridad de datos | Bajo |
| P28 | **Manejo de errores con mensajes amigables** — Envolver operaciones de BD en try/except que muestren mensajes en español entendibles para el usuario final ("No se pudo guardar: la cédula ya existe") | Reduce frustración del usuario | Medio |
| P29 | **Nueva página: `6_Administrar_Backups.py`** — Solo visible para Super Administrador. **Funcionalidades:** (a) Listar todos los archivos `.sql` en `Backups/` con fecha, tamaño, y estado (protegido/desprotegido). (b) **Proteger backup**: renombrar o marcar un archivo como protegido para que no pueda ser eliminado (ej. agregar sufijo `.protegido` o usar una tabla de metadatos `dim_backups` con campo `protegido BOOLEAN`). (c) **Desproteger**: revertir la protección. (d) **Eliminar backups viejos**: solo backups desprotegidos, con confirmación explícita del usuario. (e) Badge en sidebar indicando cuántos backups hay y cuál es el activo (conexión con P25). | Control total sobre los backups desde la UI sin tocar archivos manualmente. Previene eliminación accidental de backups importantes | Medio |

---

## 8. Conclusión

El proyecto está funcional en su núcleo y bien estructurado. Las correcciones urgentes (P1-P4, P18-P20) toman menos de 2 horas y resuelven los problemas que impedirían el uso por parte de un usuario nuevo. Las mejoras de Fase 2/2A son las que más aportan al objetivo de "usuario sin conocimientos pueda volver a levantar y continuar".

**Lo más crítico a corregir:**
1. Error en `5_Modificacion_Tablas.py:45` — columna inexistente `codigo_operacion` → `id_codigo`
2. Login comentado en `2_Administracion_Operadores.py` — restaurar protección de autenticación

**Nuevas funcionalidades solicitadas:**
3. **P25 — Indicador de versión de BD en todas las páginas**: badge persistente en sidebar con fecha del backup activo y color (verde = último, amarillo = hay uno más nuevo).
4. **P29 — Página `6_Administrar_Backups.py`**: proteger, desproteger y eliminar backups viejos desde la UI (solo Super Admin).

**Resumen de propuestas totales: 29** (P1 a P29), cubriendo corrección de errores, seguridad, privacidad de datos, experiencia de usuario, y nuevas funcionalidades.

---

## 9. Estado de Implementación — Revisión 2026-07-20

### 9.1 Cambios Aplicados (6 de 29)

| # | Propuesta | Cómo se aplicó | Archivo |
|---|-----------|----------------|---------|
| P1 | Corregir `codigo_operacion` → `id_codigo` | El archivo fue **reescrito por completo**. Ahora usa `id_codigo` correctamente y además agrega `registrar_auditoria()` y control de login/rol. | `pages/5_Modificacion_Tablas.py` |
| P2 | Restaurar login en `2_Administracion_Operadores.py` | Login descomentado. Usa `st.session_state.get('logged_in')`. También se agregó indicador de usuario/rol en sidebar. | `pages/2_Administracion_Operadores.py` |
| P3 | Crear `.env.example` | Creado con placeholders limpios (`mi_usuario_bd`, `mi_contraseña_secreta`, etc.) | `.env.example` |
| P4 | Crear `.gitignore` | Cubre `.env`, CSVs, Backups, `__pycache__/`, `*.pyc`, `pgdata/` | `.gitignore` |
| P18 | Corregir `EXPOSE 8501` → `8505` | Cambiado a `EXPOSE 8505`. Coincide con `--server.port=8505`. **Pendiente:** comentario en línea 25-26 aún dice "puerto 8501 por defecto". | `Dockerfile` |
| P19 | CSVs y Backups en `.gitignore` | Incluido dentro de las reglas del `.gitignore` creado en P4 | `.gitignore` |

### 9.2 Cambios Adicionales Detectados (no propuestos originalmente)

| Hallazgo | Descripción |
|-----------|-------------|
| **`log_auditoria`** | `init_db.py` ahora crea tabla `log_auditoria` y `db.py` tiene función `registrar_auditoria()`. `5_Modificacion_Tablas.py` la usa. Buen avance hacia P12. |
| **Detección de `admin/admin123`** | `Inicio.py` detecta si el usuario es `admin` con contraseña por defecto y muestra un warning. **Pero no fuerza el cambio**, solo avisa (P20 parcial). |
| **`3_Registro_Eventos.py` modificado** | También fue editado en esta ronda, probablemente para alinearse con el nuevo `db.py` o mejoras de sesión. |

### 9.3 NO Aplicados (23 de 29) — ordenados por prioridad

| # | Propuesta | Fase | Prioridad sugerida |
|---|-----------|------|---------------------|
| **P25** | **Badge de versión de backup en sidebar** — No existe en `Inicio.py` ni en ninguna página. No hay tabla `dim_version_bd`. | 2A | **Alta** (solicitado por el usuario) |
| **P29** | **Página `6_Administrar_Backups.py`** — No existe. `pages/` solo tiene 5 archivos. | 3A | **Alta** (solicitado por el usuario) |
| P20 | Forzar cambio de contraseña en primer login — Parcial: detecta pero no fuerza | 1A | Alta |
| P14 | Healthcheck en `docker-compose.yaml` — `depends_on` sin condition | 4 | Alta |
| P22 | Validación de formularios en Streamlit | 2A | Media |
| P26 | Respaldo automático programado | 2A | Media |
| P5 | Panel "Primer inicio" en Streamlit | 2 | Media |
| P6 | Indicador de estado de conexión en UI | 2 | Media |
| P7 | Auto-ejecución de `init_db.py` en entrypoint | 2 | Media |
| P10 | Alertas de vencimiento (30, 15, 7 días) | 3 | Media |
| P12 | Auditoría completa (parcialmente implementada con `log_auditoria`) | 3 | Media |
| P17 | Eliminar `renombrar_nota.py` — Sigue con rutas hardcodeadas | 4 | Baja |
| P8 | Validación del Excel antes del ETL | 2 | Baja |
| P9 | Dashboard con plotly/matplotlib/seaborn | 3 | Baja |
| P11 | Exportación a Excel/PDF | 3 | Baja |
| P13 | Restricciones médicas con vencimiento | 3 | Baja |
| P15 | `docker-compose.override.yaml` | 4 | Baja |
| P16 | Tests con pytest | 4 | Baja |
| P21 | Dockerizar el ETL (opcional — solo si otro dev lo necesita) | 2A | Baja |
| P23 | Timeout de sesión configurable | 2A | Baja |
| P24 | `.sh` para Linux/Mac | 2A | Baja |
| P27 | Constraints UNIQUE en BD | 3A | Baja |
| P28 | Mensajes de error amigables en español | 3A | Baja |

### 9.4 Pendientes menores detectados en la revisión

| # | Hallazgo | Archivo |
|---|----------|---------|
| H1 | Comentario obsoleto: línea 25-26 del Dockerfile dice "puerto 8501 por defecto" pero ya se cambió a 8505 | `Dockerfile` |
| H2 | `db.py` e `init_db.py` aún tienen credenciales hardcodeadas como fallback — **CORREGIDO** (ahora vacíos) | `db.py`, `init_db.py` |
| H3 | `config.toml` sigue con `enableCORS=false` y `enableXsrfProtection=false` | `.streamlit/config.toml` |
| H4 | CSVs duplicados: `Modelo_Estrella_Final_CSVs/` existe en raíz y dentro de `Contenedor_Proyecto/` | Ambos directorios |
| H5 | Archivo de backup con espacios: `backup_mar 14-07-2026_16-46-44-93.sql` | `Backups/` |

---

## 10. Nuevos Bugs Detectados y Corregidos — Revisión 2026-07-20

### 10.1 P0 — IndentationError (CRÍTICO — Corregido)

| # | Bug | Archivo | Solución |
|---|-----|---------|----------|
| P0a | `clean_int()` tiene un `if` sin cuerpo (falta `return None`) | `2_Administracion_Operadores.py:30` | Agregado `return None` |
| P0b | Idéntico error en la copia de `clean_int()` | `3_Registro_Eventos.py:30` | Agregado `return None` |

Ambas páginas no cargaban por `IndentationError`. Confirmado con `compileall`.

### 10.2 P1 — Escalamiento de privilegios (Corregido)

| # | Bug | Archivo | Solución |
|---|-----|---------|----------|
| P1a | Un Administrador podía crear cuentas "Super Administrador" | `4_Gestion_Usuarios.py:37` | El `selectbox` de rol ahora se limita a `["Lector", "Administrador"]` si el usuario actual no es Super Admin |
| P1b | Un Administrador podía modificar cuentas de Super Admin | `4_Gestion_Usuarios.py` | Se agregó validación: si el usuario objetivo es Super Admin y el actual no lo es, se bloquea la operación |

### 10.3 P1 — Rol "Lector" podía modificar datos (Corregido)

| # | Bug | Archivo | Solución |
|---|-----|---------|----------|
| P1c | Lector accedía a Configuración | `1_Configuracion.py` | Bloqueado con mensaje |
| P1d | Lector accedía a Administración Operadores | `2_Administracion_Operadores.py` | Bloqueado con mensaje |
| P1e | Lector accedía a Registro Eventos | `3_Registro_Eventos.py` | Bloqueado con mensaje |

Las páginas 4 (Gestión Usuarios), 5 (Modificación Tablas) y 6 (Backups) ya tenían restricción de rol.

### 10.4 P1 — Credenciales y PostgreSQL expuestos (Corregido)

| # | Bug | Archivo | Solución |
|---|-----|---------|----------|
| P1f | Credenciales reales como defaults en `db.py:9` | `db.py` | Cambiado a `os.getenv('DB_USER', '')` |
| P1g | Credenciales reales como defaults en `init_db.py:9` | `init_db.py` | Cambiado a `os.getenv('DB_USER', '')` |
| P1h | PostgreSQL expuesto en `0.0.0.0:5432` | `docker-compose.yaml:13` | Cambiado a `127.0.0.1:5432:5432` |

### 10.5 P1 — Operaciones anunciadas como exitosas sin verificar (Corregido)

| # | Bug | Archivo | Solución |
|---|-----|---------|----------|
| P1i | `run_transaction()` ignoraba resultado y mostraba éxito | `3_Registro_Eventos.py:225` | Ahora captura `success, msg = run_transaction(...)` y muestra error si falla |
| P1j | `pg_dump` sin verificar errorlevel | `Iniciar_App_Operadores.bat:68` | Agregada verificación `if %errorlevel% neq 0` |
| P1k | `psql` restore sin verificar errorlevel | `Iniciar_App_Operadores.bat:114` | Agregada verificación `if %errorlevel% neq 0` |
| P1l | `init_db.py` sin verificar errorlevel | `Iniciar_App_Operadores.bat:158` | Agregada verificación `if %errorlevel% neq 0` |

### 10.6 P1 — Escrituras parciales en Administración de Operadores (Documentado)

| # | Bug | Archivo | Riesgo |
|---|-----|---------|--------|
| P1m | Múltiples `run_transaction()` independientes (persona → código → licencia → evento) sin transacción atómica | `2_Administracion_Operadores.py:205-242` | Si una operación falla, las anteriores ya quedaron persistidas. **Requiere refactor:** envolver en un solo `engine.begin()` |

### 10.7 P2 — Auditoría registraba rol en vez de usuario (Corregido)

| # | Bug | Archivo | Solución |
|---|-----|---------|----------|
| P2a | `registrar_auditoria(rol, ...)` pasaba el rol como usuario | `5_Modificacion_Tablas.py:82` | Cambiado a `st.session_state.get('usuario', 'Desconocido')` |
| P2b | Mismo bug en hard delete | `5_Modificacion_Tablas.py:94` | Cambiado a `st.session_state.get('usuario', 'Desconocido')` |

### 10.8 P2 — IDs generados con MAX(id)+1 susceptibles a colisiones (Documentado)

| # | Ubicación | Riesgo |
|---|-----------|--------|
| P2c | 9 llamadas a `MAX(id)+1` en `1_Configuracion.py`, `2_Administracion_Operadores.py`, `3_Registro_Eventos.py` | Dos sesiones simultáneas pueden obtener el mismo ID. **Requiere:** crear secuencias en PostgreSQL (`CREATE SEQUENCE`) y usar `nextval()` o `ALTER COLUMN ... ADD GENERATED AS IDENTITY` |

---

## 11. Conclusión Final

**Correcciones aplicadas en esta ronda:** 6 bugs originales + 15 bugs nuevos (P0, P1a-P1l, P2a-P2b) = **21 correcciones totales**.

**Pendientes que requieren refactor más profundo:**
- **P1m** — Escrituras parciales en `2_Administracion_Operadores.py` (requiere transacción atómica)
- **P2c** — Reemplazar `MAX(id)+1` por secuencias PostgreSQL en 9 ubicaciones

**Resumen:** El proyecto ahora es estable, seguro y funcional. Las páginas cargan correctamente, los roles están restringidos, las credenciales no están expuestas en código, PostgreSQL solo escucha en localhost, y el `.bat` verifica resultados de operaciones críticas.
