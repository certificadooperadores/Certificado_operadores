# Manual de usuario — Certificado_operadores

Guía integral de uso de la plataforma de gestión de certificados de operadores del sistema masivo MIO.

---

## 1. Roles y Permisos del Sistema

La plataforma implementa un control de acceso basado en roles (RBAC) para garantizar la seguridad y segregación de funciones:

| Módulo / Funcionalidad | Super Administrador | Administrador | Gestor |
| :--- | :---: | :---: | :---: |
| **Inicio de Sesión y Perfil** | Sí | Sí | Sí |
| **Administración de Operadores** (Datos maestros, vinculación) | Sí | Sí | Sí |
| **Gestión de Certificados** (Novedades, eventos, vigencia) | Sí | Sí | Sí |
| **Reporte de Comportamientos** (Individual, masivo, reincidencia) | Sí | Sí | Sí |
| **Reportes y Exportaciones** (Bitácora, consultas, KPIs, analítica) | Sí | Sí | Sí |
| **Configuración: Gestión de Usuarios** | Sí (Total) | Sí (Limitado) | No |
| **Configuración: Corrección de Registros** | Sí | Sí | No |
| **Configuración: Catálogos del Sistema** | Sí | Sí | No |
| **Configuración: Administrar Backups** | Sí | No | No |

### Descripción de Roles:
* **Super Administrador:**
  * Acceso total a todos los módulos y opciones de la plataforma.
  * Único rol facultado para crear, proteger, desproteger y restaurar copias de respaldo de la base de datos (**Administrar Backups**).
  * Puede asignar y revocar el rol de Super Administrador a otros usuarios.
* **Administrador:**
  * Diseñado para coordinadores y administradores del sistema.
  * Acceso a la operación completa y al módulo de **Configuración** (Gestión de Usuarios, Corrección de Registros y Catálogos).
  * *Restricción de seguridad:* No puede modificar cuentas con rol de Super Administrador, no puede asignarse dicho rol ni inactivar su propio usuario. No tiene acceso a la pestaña de Backups.
* **Gestor:**
  * Diseñado para el equipo operativo, analistas e inspectores de campo.
  * Acceso a la consulta y actualización de operadores, gestión de certificados, novedades de comportamiento e informes analíticos.
  * No tiene acceso a la pestaña de Configuración.

---

## 2. Módulo: Administración de Operadores

Permite gestionar el ciclo de vida del operador desde su creación o vinculación inicial.

* **Filtros por Concesionario y Tipología:** Permite consultar operadores activos por empresa (GIT, Blanco y Negro, ETM, Unimetro).
* **Validación de Código:** El sistema asigna o valida automáticamente la serie según el operador (10001+ GIT, 20001+ ByN, 30001+ ETM, 40001+ Unimetro).
* **Ficha del Operador:** Visualiza cédula, nombres completos, vigencia y tipología autorizada (Articulado, Padrón o Complementario).

---

## 3. Módulo: Gestión de Certificados

Controla los eventos normativos y la vigencia del certificado de idoneidad (3 años de validez legal).

* **Registro de Eventos:** Certificación, Reactivación, Renovación, Suspensión y Retiro.
* **Alertas Preventivas:** Notifica automáticamente los certificados próximos a vencer en los rangos de 30, 60 y 90 días.
* **Control de Cancelación:** Si un operador presenta un evento de retiro o cancelación (evento #7), se excluye automáticamente de las alertas activas y se refleja como inactivo.

---

## 4. Módulo: Reporte de Comportamientos e Infracciones

Estructurado en tres pestañas operacionales para garantizar orden y agilidad:

### 4.1 Ingreso Individual
* Registro rápido de una novedad o infracción de bitácora seleccionando código de operador, fecha, vehículo, viaje, tarea, ruta y detalle del comportamiento.

### 4.2 Carga Masiva (Excel)
* Descarga de plantilla institucional preformateada.
* Subida de archivos con validación automática antes de guardar: detecta registros duplicados, valida la existencia de códigos de operador y muestra un resumen previo.

### 4.3 Pestaña: Reincidencia de Comportamientos
* **Evaluación Automatizada:** Botón `🔎 Evaluar Reincidencia` en la cabecera que procesa los impactos y frecuencias según reglas normativas de Metrocali.
* **Barra de Filtros Horizontal Compacta:**
  * Filtro por **Empresa** concesionaria.
  * Filtro por **Código** de operador.
  * Filtro por **Caso** de reincidencia.
  * Selector de límite de visualización (`Mostrar`: 10, 20, 50 o 100 casos) para evitar listas infinitas en pantalla.
* **Exportación Inmediata:** Botón `⬇️ Exportar Excel` ubicado directamente en la barra superior de herramientas.
* **Determinación Metrocali:** Menú desplegable por caso para asignar la decisión (`Amonestación`, `Suspensión`, `Capacitación`, etc.), fecha de acción y registro en el historial.
* **Importación Masiva de Acciones:** Panel expandible opcional `📥 Importar Acciones desde Excel` que no invade el espacio visual principal.

---

## 5. Módulo: Reportes y Analítica Interactiva

Panel analítico centralizado con **ancho completo responsivo**, **KPIs de negocio inteligentes** y gráficos interactivos con **Altair**:

### 5.1 Operadores por Empresa y Tipología
* **KPIs Directos:**
  * `Total Activos`: Suma total de operadores en servicio.
  * `Articulado`: Total de operadores habilitados para articulado (autoriza articulado, padrón y complementario).
  * `Padrón`: Total autorizados para padrón y complementario.
  * `Complementario`: Total con tipología complementaria.
* **Gráficos Interactivos:**
  * Gráfico de barras de operadores activos por concesionario con hover y tooltips.
  * Gráfico de distribución por tipología autorizada.

### 5.2 Licencias por Vencer y Certificados por Vencer
* **KPIs Clave:** Total por vencer, casos críticos (< 30 días), concesionarios involucrados y operadores únicos.
* **Cronograma Interactivo por Quincenas:**
  * Agrupación visual por rangos cada 15 días: `0 a 15 días (Crítico)`, `16 a 30 días (Crítico)`, `31 a 45 días (Alerta)`, `46 a 60 días (Alerta)`, `61 a 90 días` y `Más de 90 días`.
  * Barras apiladas interactivas por concesionario con paleta de criticidad semaforizada.
  * Opción expandible para consultar el diagrama tradicional si se requiere.

### 5.3 Certificados Vencidos
* **KPIs:** Total certificados vencidos, concesionarios afectados y operadores vencidos.
* **Filtros:** Filtro por empresa concesionaria para aislar la flota.
* **Gráfico Interactivo:** Gráfico de barras con el total de certificados vencidos clasificados por concesionario.

### 5.4 Comportamientos por Operador
* **Filtros Flexibles:** Filtro por código de operador opcional (permite ver todos los operadores o seleccionar uno) y filtro por concesionario.
* **KPIs Operacionales:** Total de novedades, operadores únicos con novedad, rutas afectadas y vehículos involucrados.
* **Analítica Operativa en 3 Columnas:**
  1. **Top 10 Operadores con más Novedades:** Identificación de operadores que requieren acompañamiento o capacitación.
  2. **Causales Más Frecuentes:** Extracción automática de la causal raíz a partir de la jerarquía (`abandono de tarea`, `no relevo`, `desvío`, etc.).
  3. **Top 10 Rutas con Más Novedades:** Identificación de corredores y servicios con mayor impacto en la operación.

### 5.5 Exportación de Datos
* Botones `Exportar a Excel` y `Exportar a CSV` ubicados en la parte superior, directamente sobre las tablas de datos para descarga inmediata.

---

## 6. Módulo: Configuración del Sistema

### 6.1 Panel: Gestión de Usuarios
Centraliza cuentas, credenciales y niveles de acceso (RBAC):
* **Tabla de Usuarios:** ID, Usuario, Rol, Estado y Fecha de registro.
* **Alta de Usuarios:** Asignación segura con cifrado bcrypt.
* **Modificación y Bloqueo:** Actualización de roles, restablecimiento de contraseña e inactivación preventiva.
* **Reglas de Seguridad:** Prohibición de autoinactivación y protección contra modificación de cuentas Super Administrador por parte de Administradores estándar.

### 6.2 Panel: Corrección de Registros y Catálogos
* Mantenimiento de catálogos maestros: empresas, tipologías, tipos de eventos e impactos de comportamiento.
* Corrección puntual de inconsistencias históricas con trazabilidad en log de auditoría.

### 6.3 Panel: Administrar Backups (Exclusivo Super Administrador)
* **Creación de Respaldos:** Botón `Crear Respaldo Ahora` con nomenclatura versionada por fecha y secuencia (`DD-MM-AAAA_VX.db`).
* **Protección de Archivos:** Marcado `.protegido.db` para evitar borrado involuntario.
* **Restauración Asistida:** Comparador de registros antes de restaurar, semáforo de impacto y respaldo preventivo de rescate automático (`pre_restauracion_...db`).

---

## 7. Sesión, Refresco de Datos y Navegación

### 7.1 Persistencia de Sesión
* La sesión del usuario permanece activa ante recargas de página (`F5`), garantizando continuidad laboral.
* Expiración por inactividad tras 20 minutos de desatención.
* Cierre seguro desde el botón **Cerrar Sesión** en la barra lateral.

### 7.2 Botón Refrescar Datos
* Ubicado en la barra lateral: purga la memoria caché de Streamlit y reconecta las vistas con la base de datos física sin cerrar la sesión.

---

## 8. Carga Masiva de Datos Iniciales (Scripts de Terminal)

Para inicializaciones masivas o migraciones desde hojas de cálculo institucionales:

1. Diligencie las plantillas en `docs/plantillas/`:
   * `Plantilla_Operadores_Maestra.xlsx`
   * `Plantilla_Eventos_Operadores.xlsx`
2. Ejecute los scripts en PowerShell usando `uv`:
   ```powershell
   # 1. Modelo estrella de operadores maestros
   uv run python scripts/generar_modelo_estrella_maestro.py

   # 2. Modelo estrella de eventos y novedades de comportamiento
   uv run python scripts/generar_modelo_estrella_comportamiento.py

   # 3. Consolidación a SQLite (operadores.db)
   uv run python scripts/cargar_excel_a_sqlite.py
   ```

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
