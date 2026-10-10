# Manual de Usuario — Certificado_operadores

Guía integral de uso y manual operativo de la plataforma para la gestión del certificado de idoneidad, eventos normativos, control de novedades y analítica operacional de los operadores del sistema masivo MIO (Metrocali S.A.).

---

## 1. Acceso a la Plataforma e Inicio de Sesión

### 1.1 Pantalla de Autenticación
* **Diseño Institucional Centrado:** El formulario de acceso se presenta en una tarjeta central enfocada (`[1, 1.3, 1]`) con la identidad visual corporativa de Metrocali, evitando distorsiones panorámicas.
* **Credenciales:** Ingrese su nombre de **Usuario** y **Contraseña** asignados. La validación se procesa de forma segura a través de `UsuariosFacade` con cifrado irreversible `bcrypt`.
* **Persistencia de Sesión (Token URL):** Al autenticarse satisfactoriamente, el sistema genera un token de sesión criptográfico (`HMAC-SHA256`) reflejado en los parámetros de la URL. Esto permite recargar la página (`F5`) sin perder la sesión de trabajo ni el estado actual.
* **Tiempo de Inactividad:** Por motivos de seguridad de la información institucional, la sesión expira automáticamente tras 20 minutos de inactividad continua.

### 1.2 Barra Lateral y Menú de Navegación
* **Identidad Institucional:** Despliegue del logotipo oficial de Metrocali y distintivos institucionales.
* **Control de Sesión:** Muestra el usuario activo, su rol asignado y el botón **Cerrar Sesión**.
* **Botón 🔄 Refrescar Datos:** Purga la memoria en caché de Streamlit y reconecta las vistas con la base de datos física (`operadores.db`), permitiendo reflejar cambios realizados por otros usuarios o procesos en segundo plano.
* **Indicador de Versión de Base de Datos:** Badge dinámico que muestra la última versión de respaldo activa y advierte si existe una copia de seguridad más reciente disponible.

---

## 2. Roles y Control de Acceso (RBAC)

La plataforma aplica un modelo de control de acceso estricto basado en roles para asegurar la confidencialidad e integridad de la base histórica:

| Módulo / Funcionalidad | Super Administrador | Administrador | Gestor |
| :--- | :---: | :---: | :---: |
| **Inicio de Sesión y Perfil** | Sí | Sí | Sí |
| **Administración de Operadores** (Datos maestros, vinculación) | Sí | Sí | Sí |
| **Gestión de Certificados** (Novedades, eventos, vigencia) | Sí | Sí | Sí |
| **Reporte de Comportamientos** (Individual, masivo, reincidencia) | Sí | Sí | Sí |
| **Reportes y Exportaciones** (Bitácora, consultas, KPIs, analítica dinámica) | Sí | Sí | Sí |
| **Configuración: Gestión de Usuarios** | Sí (Total) | Sí (Limitado) | No |
| **Configuración: Corrección de Registros** | Sí (Edición y Eliminación) | Sí (Solo Edición) | No |
| **Configuración: Catálogos del Sistema** | Sí | Sí | No |
| **Configuración: Administrar Backups** | Sí | No | No |

### Perfiles de Usuario:
1. **Super Administrador:**
   * Control maestro de toda la plataforma.
   * Único rol con facultades para gestionar, proteger, desproteger y restaurar copias de respaldo de la base de datos (**Administrar Backups**).
   * Único rol autorizado para realizar la **eliminación física** de registros en el módulo de Corrección.
   * Gestión completa de usuarios y asignación del rol Super Administrador.
2. **Administrador:**
   * Diseñado para coordinadores y supervisores de área.
   * Acceso total a la operación y al módulo de **Configuración** (Gestión de Usuarios, Corrección de Registros y Catálogos).
   * *Restricciones de seguridad:* No puede alterar cuentas de Super Administradores, no puede auto-asignarse dicho rol ni auto-inactivarse. No tiene acceso al panel de Backups ni a la eliminación física de registros.
3. **Gestor:**
   * Perfil operativo para analistas, inspectores y personal de bitácora.
   * Acceso a consultas, registro de operadores, emisión de eventos normativos, ingreso de novedades e informes analíticos.
   * El menú de Configuración se encuentra completamente oculto.

---

## 3. Módulo: Administración de Operadores

Permite gestionar el ciclo de vida del operador desde su vinculación, asignación de código institucional y datos maestros:

* **Estructura de Códigos por Concesionario (Patrón COT):**
  Cada empresa operadora cuenta con un prefijo y rango numérico exclusivo de 5 dígitos para prevenir solapamientos:
  * **Prefijo 1 — GIT Masivo (Empresa 1):** Serie `10001` a `19999` (Código base bitácora: `10000` = Git Masivo)
  * **Prefijo 2 — Blanco y Negro Masivo (Empresa 2):** Serie `20001` a `29999` (Código base bitácora: `20000` = Blanco y Negro)
  * **Prefijo 3 — ETM (Empresa 3):** Serie `30001` a `39999` (Código base bitácora: `30000` = ETM)
  * **Prefijo 4 — Unimetro (Empresa 4):** Serie `40001` a `49999` (Código base bitácora: `40000` = Unimetro)
  *(Nota institucional: Los códigos cerrados `10000`, `20000`, `30000` y `40000` identifican a la empresa concesionaria para novedades globales de bitácora cuando no se individualizó al conductor en la vía. Por regla de negocio, se excluyen de los rankings y evaluaciones de operadores individuales para no distorsionar las métricas de personas reales).*
* **Búsqueda y Ficha del Operador:** Búsqueda inmediata por número de cédula o por código de operación. Muestra nombres completos, género, concesionario, tipología autorizada y vigencia.
* **Creación y Actualización Segura:** Formulario validado con cálculo automático del siguiente código disponible en la serie del concesionario y verificación de no duplicidad de cédula activa.

---

## 4. Módulo: Gestión de Certificados

Controla los eventos normativos y la vigencia del certificado de idoneidad (3 años de validez legal).

* **Registro de Eventos:** Certificación, Reactivación, Renovación, Suspensión y Retiro.
* **Alertas Preventivas:** Notifica automáticamente los certificados próximos a vencer en los rangos de 30, 60 y 90 días.
* **Control de Cancelación:** Si un operador presenta un evento de retiro o cancelación (evento #7), se excluye automáticamente de las alertas activas y se refleja como inactivo.

---

## 5. Módulo: Reporte de Comportamientos e Infracciones

Estructurado en tres pestañas operacionales para garantizar orden y agilidad:

### 5.1 Ingreso Individual
* Registro rápido de una novedad o infracción de bitácora seleccionando código de operador, fecha, vehículo, viaje, tarea, ruta y detalle del comportamiento.

### 5.2 Carga Masiva (Excel)
* **Plantillas Oficiales:** Disponibles para descarga directa en la plataforma y ubicadas como respaldo en la carpeta `docs/plantillas/`:
  * `Plantilla_Operadores_Maestra.xlsx` (Carga masiva de datos maestros de operadores)
  * `Plantilla_Eventos_Operadores.xlsx` (Carga masiva de novedades de comportamiento y eventos)
* **Descarga y Diligenciamiento:** Descargue la plantilla institucional desde el botón `📥 Descargar Plantilla` en la interfaz o tómela de `docs/plantillas/`.
* **Subida con Validación Previa Automática:** El sistema valida la integridad de cada fila antes de la inserción: detecta registros duplicados, valida la existencia de códigos de operador y muestra un resumen previo diferenciando registros nuevos vs. actualizaciones.

### 5.3 Pestaña: Reincidencia de Comportamientos
* **Evaluación Automatizada:** Botón `🔎 Evaluar Reincidencia` en la cabecera que procesa los impactos y frecuencias según reglas normativas de Metrocali.
* **Barra de Filtros Horizontal Compacta:**
  * Filtro por **Empresa** concesionaria.
  * Filtro por **Código** de operador (excluyendo automáticamente los códigos genéricos de empresa).
  * Filtro por **Caso** de reincidencia.
  * Selector de límite de visualización (`Por página`: 10, 20 o 50 casos) para evitar listas infinitas en pantalla.
* **Exportación Inmediata:** Botón `⬇️ Exportar Excel` ubicado directamente en la barra superior de herramientas.
* **Determinación Metrocali:** Menú desplegable por caso para asignar la decisión (`Amonestación`, `Suspensión`, `Capacitación`, etc.), fecha de acción y registro en el historial.
* **Importación Masiva de Acciones:** Panel expandible opcional `📥 Importar Acciones desde Excel` que no invade el espacio visual principal.

---

## 6. Módulo: Reportes y Analítica Interactiva

Panel analítico centralizado con **ancho completo responsivo**, **KPIs de negocio inteligentes** y gráficos interactivos con **Altair**:

### 6.1 Operadores por Empresa y Tipología
* **KPIs Directos:**
  * `Total Activos`: Suma total de operadores en servicio.
  * `Articulado`: Total de operadores habilitados para articulado (autoriza articulado, padrón y complementario).
  * `Padrón`: Total autorizados para padrón y complementario.
  * `Complementario`: Total con tipología complementaria.
* **Gráficos Cromáticos Diferenciados:**
  * Gráfico de barras de operadores activos por concesionario con esquema de color institucional `tableau10` para identificar a cada empresa de forma inequívoca.
  * Gráfico de distribución por tipología autorizada con paleta semántica (Articulado en Azul `#2563EB`, Padrón en Verde Azulado `#0D9488` y Complementario en Ámbar `#F59E0B`).

### 6.2 Licencias por Vencer y Certificados por Vencer
* **KPIs Clave:** Total por vencer, casos críticos (< 30 días), concesionarios involucrados y operadores únicos.
* **Cronograma Interactivo por Quincenas:**
  * Agrupación visual por rangos cada 15 días: `0 a 15 días (Crítico)`, `16 a 30 días (Crítico)`, `31 a 45 días (Alerta)`, `46 a 60 días (Alerta)`, `61 a 90 días` y `Más de 90 días`.
  * Barras apiladas interactivas por concesionario con paleta de criticidad semaforizada y tooltips explicativos.
  * Opción expandible para consultar el diagrama tradicional (Matplotlib) si se requiere.

### 6.3 Certificados Vencidos
* **KPIs:** Total certificados vencidos, concesionarios afectados y operadores vencidos.
* **Filtros:** Filtro por empresa concesionaria para aislar la flota.
* **Gráfico Interactivo:** Gráfico de barras con el total de certificados vencidos clasificados por concesionario.

### 6.4 Comportamientos por Operador (Cross-Filtering Tridireccional tipo Power BI)
* **Filtrado Limpio de Datos Históricos:** Los registros generales sin operador (`id_codigo IS NULL`) y los códigos genéricos de concesionario (`10000`, `20000`, `30000`, `40000`) se excluyen automáticamente de los rankings, garantizando que solo figuren operadores reales debidamente identificados y con códigos enteros limpios.
* **Analítica Operativa en 3 Columnas Coordinadas:**
  1. **Top 10 Operadores con más Novedades:** Identificación de conductores reales que requieren acompañamiento o reentrenamiento.
  2. **Causales Más Frecuentes:** Extracción automática de la causal raíz a partir de la jerarquía (`abandono de tarea`, `no relevo`, `desvío`, etc.).
  3. **Top 10 Rutas con Más Novedades:** Identificación de corredores y servicios con mayor impacto en la operación.
* **Interacción Dinámica Total:** Al hacer clic en una barra de cualquiera de las tres gráficas (Operador, Causal o Ruta), las otras dos se filtran de forma instantánea y coordinada en el navegador. Para restablecer la vista, basta con hacer clic fuera de las barras.

### 6.5 Exportación de Datos
* Botones `Exportar a Excel` y `Exportar a CSV` ubicados en la parte superior, directamente sobre las tablas de datos para descarga inmediata.

---

## 7. Módulo: Configuración del Sistema

### 7.1 Panel: Gestión de Usuarios (RBAC)
Centraliza cuentas, credenciales y niveles de acceso:
* **Tabla de Usuarios:** ID, Usuario, Rol, Estado y Fecha de registro.
* **Alta de Usuarios:** Asignación segura con cifrado `bcrypt`.
* **Modificación y Bloqueo:** Actualización de roles, restablecimiento de contraseña e inactivación preventiva.
* **Reglas de Seguridad:** Prohibición de autoinactivación y protección contra modificación de cuentas Super Administrador por parte de Administradores estándar.

### 7.2 Panel: Corrección de Registros (Editor Tipo Hoja de Cálculo)
* **Pestañas por Tabla:** Sub-pestañas para cada tabla del sistema (`Eventos`, `Licencias`, `Comportamientos`, `Operadores` y `Códigos`).
* **Filtrado Especializado por Tipo de Evento:**
  * En la pestaña **Eventos**, el selector superior permite aislar categorías específicas (`Certificación`, `Suspensión`, `Retiro`, etc.).
  * La consulta a la base de datos filtra directamente por `id_tipo_evento` en SQL, asegurando la visualización inmediata de los registros reales de cada categoría sin quedar truncados por el límite de visualización (`LIMIT 500`).
  * Proyección dinámica de columnas: solo se muestran y habilitan las columnas legalmente aplicables a cada categoría de evento.
* **Editor Seguro (`st.data_editor`):** Edición directa en celda con listas desplegables restringidas a catálogos oficiales.
* **Acciones en Bloque:** Casillas de selección para marcar registros como `Vigente`, `Anulado` o solicitar `Eliminación` (esta última exclusiva para Super Administradores y condicionada a que no existan dependencias referenciales).
* **Botón Explícito:** Las modificaciones solo se consolidan al presionar el botón `💾 Guardar Cambios`.

### 7.3 Panel: Catálogos del Sistema
* Mantenimiento de catálogos maestros: empresas, tipologías, flota de vehículos, tipos de eventos e impactos de comportamiento.

### 7.4 Panel: Administrar Backups (Exclusivo Super Administrador)
* **Creación de Respaldos:** Botón `Crear Respaldo Ahora` con nomenclatura versionada por fecha y secuencia (`DD-MM-AAAA_VX.db`).
* **Protección de Archivos:** Marcado `.protegido.db` para evitar purgas o borrados accidentales.
* **Restauración Asistida:** Comparador de registros antes de restaurar, semáforo de impacto y respaldo preventivo de rescate automático (`pre_restauracion_...db`).

---

## 8. Sesión, Refresco de Datos y Navegación

### 8.1 Persistencia de Sesión
* La sesión del usuario permanece activa ante recargas de página (`F5`), garantizando continuidad laboral.
* Expiración por inactividad tras 20 minutos de desatención.
* Cierre seguro desde el botón **Cerrar Sesión** en la barra lateral.

### 8.2 Botón Refrescar Datos
* Ubicado en la barra lateral: purga la memoria caché de Streamlit y reconecta las vistas con la base de datos física sin cerrar la sesión.

---

---

## 9. Clonación del Repositorio e Instalación del Entorno (`uv`)

Para desplegar la aplicación en un nuevo equipo de trabajo:

### 9.1 Clonación desde GitHub
Abra su terminal (PowerShell en Windows o Bash) y clone el repositorio oficial en la ubicación deseada:

```powershell
# 1. Clonar el repositorio
git clone https://github.com/certificadooperadores/Certificado_operadores.git

# 2. Entrar a la carpeta raíz del proyecto
cd Certificado_operadores
```

### 9.2 Inicialización del Entorno con `uv`
La plataforma utiliza [`uv`](https://docs.astral.sh/uv/) como gestor moderno de dependencias y entornos virtuales (prohibido `pip` o `requirements.txt` directos):

```powershell
# 1. Sincronizar el entorno e instalar dependencias automáticamente
uv sync

# 2. (Opcional para desarrollo) Instalar hooks de validación
uv run pre-commit install
```

---

## 10. Inicialización de la Base de Datos por Primera Vez (Script Único)

Para **levantar la base de datos desde cero por primera vez**, se procesan los libros Excel institucionales originales.

### 10.1 Ubicación de los Archivos Excel Requeridos
Los archivos fuentes deben estar depositados dentro de la carpeta `scripts/Archivos_excel_iniciales/` en la raíz del proyecto (las rutas son relativas al repositorio, sin rutas fijas absolutas):

1. **Maestro de Operadores:**
   * Archivo: `scripts/Archivos_excel_iniciales/BASE DE DATOS OPERADORESv4.xlsm`
2. **Novedades y Comportamientos:**
   * Carpeta: `scripts/Archivos_excel_iniciales/Comportamiento/`
   * Archivos requeridos:
     * `auxiliares_reporte.xlsx` (Catálogos de impacto, comportamiento y jerarquías)
     * `Gestión del Certificado de Idoneidad del Operador.xlsx`
     * `Accidentalidad Consolidada.xlsx`
     * `Consolidado Infracciones Operadores.xlsx`
     * `Consolidado Quejas Operadores.xlsx`

### 10.2 Ejecución con un Solo Comando
Abra la terminal en la raíz del proyecto (`Certificado_operadores`) y ejecute:

```powershell
# Asegúrese de estar ubicado en la raíz del proyecto:
cd "C:\ruta\hacia\Certificado_operadores"

# Ejecutar el proceso unificado
uv run python scripts/levantar_base_datos_primera_vez.py
```

**¿Qué hace este script automáticamente?**
1. **Paso 1:** Procesa el maestro de operadores y genera las dimensiones de personas, códigos, empresas, tipologías y eventos de certificación en `data/Modelo_Estrella_Final_CSVs/`.
2. **Paso 2:** Procesa los libros de accidentalidad, quejas, infracciones y bitácora generando la tabla `fact_comportamiento.csv` normalizada con más de 300.000 hechos.
3. **Paso 3:** Crea la base de datos SQLite física (`operadores.db`), crea las tablas de configuración (`dim_usuarios`, logs de auditoría, control de reincidencias) y genera la cuenta inicial de administrador (`admin` / `admin123`).

---

## 11. Ejecución e Inicio de la Aplicación

Para iniciar la plataforma web dispone de dos alternativas:

### Opción A — Ejecutable directo de Windows (Recomendada)
Haga doble clic en el archivo [ejecutar_app.bat](file:///c:/Users/maortiz/OneDrive%20-%20metrocali.gov.co/App/Certificado_operadores/ejecutar_app.bat) ubicado en la raíz del repositorio. Este archivo se sitúa automáticamente en el directorio correcto y lanza Streamlit de forma directa.

### Opción B — Desde Terminal PowerShell
Abra PowerShell, ubíquese en la raíz del proyecto con `cd` y lance el comando:

```powershell
cd "C:\ruta\hacia\Certificado_operadores"
uv run streamlit run src/certificado_operadores/Inicio.py
```

---

**Autor:** Ing. Miguel Angel Ortiz Roldan  
**Institución:** Metrocali S.A. — Dirección de Operación - Evaluación de la Operación
