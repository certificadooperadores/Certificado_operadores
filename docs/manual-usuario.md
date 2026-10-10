# Manual de usuario — Certificado_operadores

Guía integral de uso de la plataforma de gestión de certificados de operadores del sistema masivo MIO.

---

## 1. Roles y Permisos del Sistema

La plataforma implementa un control de acceso basado en roles (RBAC) para garantizar la seguridad y segregación de funciones:

| Módulo / Funcionalidad | Super Administrador | Administrador | Gestor |
| :--- | :---: | :---: | :---: |
| **Inicio de Sesión y Perfil** | Si | Si | Si |
| **Administración de Operadores** (Datos maestros) | Si | Si | Si |
| **Gestión de Certificados** (Novedades, eventos) | Si | Si | Si |
| **Reporte de Comportamientos** (Infracciones, reincidencias) | Si | Si | Si |
| **Reportes y Exportaciones** (Bitácora, consultas, Excel) | Si | Si | Si |
| **Configuración: Gestión de Usuarios** | Si (Total) | Si (Limitado) | No |
| **Configuración: Corrección de Registros** | Si | Si | No |
| **Configuración: Catálogos del Sistema** | Si | Si | No |
| **Configuración: Administrar Backups** | Si | No | No |

### Descripción de Roles:
* **Super Administrador:**
  * Acceso total a todos los módulos y opciones de la plataforma.
  * Único rol facultado para crear, modificar y descargar copias de respaldo de la base de datos (**Administrar Backups**).
  * Puede asignar y revocar el rol de Super Administrador a otros usuarios.
* **Administrador:**
  * Diseñado para coordinadores y administradores del sistema.
  * Acceso a la operación completa y al módulo de **Configuración** (Gestión de Usuarios, Corrección de Registros y Catálogos).
  * *Restricción de seguridad:* No puede modificar cuentas con rol de Super Administrador, no puede asignarse el rol de Super Administrador ni puede inactivar su propio usuario. No tiene acceso a la pestaña de Backups.
* **Gestor:**
  * Diseñado para el equipo operativo y analistas de campo.
  * Acceso a la consulta y actualización de operadores, gestión de certificados, comportamientos e informes generales.
  * No tiene acceso a la pestaña de Configuración.

---

## 2. Panel: Gestión de Usuarios del Sistema

Ubicación: **Configuración** -> Pestaña **Gestion de Usuarios** (Accesible para Administradores y Super Administradores).

Este panel centraliza la administración de accesos, credenciales y estados de las cuentas de usuario de la plataforma.

### 2.1 Tabla de Usuarios Registrados
Muestra el inventario actualizado de usuarios en la base de datos con las siguientes columnas:
* **ID:** Identificador numérico interno del usuario.
* **Usuario:** Nombre de usuario único utilizado para iniciar sesión.
* **Rol:** Nivel de privilegios asignado (`Super Administrador`, `Administrador` o `Gestor`).
* **Estado:** Condición de la cuenta (`Activo` o `Inactivo`).
* **Registro:** Fecha y hora en la que fue creada la cuenta.

### 2.2 Formulario: Agregar Nuevo Usuario (Columna Izquierda)
Permite dar de alta a un nuevo integrante del equipo:
1. **Nombre de Usuario:** Ingrese el identificador único (sin espacios).
2. **Contraseña:** Ingrese la clave de acceso inicial. La plataforma la almacenará automáticamente cifrada mediante hash criptográfico (bcrypt).
3. **Rol:** Seleccione el rol correspondiente:
   * Si usted es *Super Administrador*, puede asignar cualquier rol (`Gestor`, `Administrador` o `Super Administrador`).
   * Si usted es *Administrador*, solo puede asignar `Gestor` o `Administrador`.
4. Haga clic en **Crear Usuario**. El sistema auditará la acción y mostrará el mensaje de confirmación.

### 2.3 Formulario: Modificar Usuario Existente (Columna Derecha)
Permite actualizar el rol, estado o restablecer la contraseña de una cuenta existente:
1. **Seleccione Usuario:** Elija en la lista desplegable el usuario que desea modificar.
2. **Nuevo Rol:** Seleccione el nuevo nivel de privilegios.
3. **Estado:**
   * `Activo`: Permite al usuario iniciar sesión con normalidad.
   * `Inactivo`: Bloquea inmediatamente el acceso a la plataforma.
4. **Nueva Contraseña (Opcional):**
   * *Si desea conservar la contraseña actual:* Deje este campo completamente en blanco.
   * *Si desea restablecer la clave:* Escriba la nueva contraseña en este campo.
5. Haga clic en **Actualizar Usuario**.

#### Reglas de Protección y Seguridad:
* **No auto-inactivación:** Un usuario conectado no puede inactivar su propia cuenta.
* **Protección de Super Administradores:** Si un usuario con rol *Administrador* intenta modificar una cuenta de *Super Administrador*, el sistema rechazará la operación con un mensaje de advertencia.

---

## 3. Sesión, Refresco de Datos y Navegación

### 3.1 Persistencia de Sesión (Recarga del Navegador)
* La sesión del usuario permanece activa incluso al presionar `F5` o recargar la página del navegador, evitando cierres de sesión accidentales mientras trabaja.
* Para salir de forma segura, utilice siempre el botón **Cerrar Sesión** ubicado en la barra lateral.

### 3.2 Botón Refrescar Datos (Barra Lateral)
* Para actualizar las vistas y consultar los últimos cambios de la base de datos (por ejemplo, tras una sincronización de OneDrive o un cargue masivo), utilice el botón **Refrescar Datos** en la barra lateral.
* Esto limpia la caché interna y reconecta la información sin necesidad de cerrar su sesión ni recargar el navegador.

---

## 4. Carga Masiva de Datos Iniciales (Scripts)

Para cargas iniciales o migraciones masivas desde archivos Excel (`.xlsx`):

1. Diligencie las plantillas en `docs/plantillas/`:
   * `Plantilla_Operadores_Maestra.xlsx`
   * `Plantilla_Eventos_Operadores.xlsx`
2. Ejecute los scripts de procesamiento en su terminal con `uv`:
   ```powershell
   # Procesamiento de operadores maestros
   uv run python scripts/generar_modelo_estrella_maestro.py

   # Procesamiento de eventos y comportamientos
   uv run python scripts/generar_modelo_estrella_comportamiento.py

   # Carga final consolidada a operadores.db
   uv run python scripts/cargar_excel_a_sqlite.py
   ```

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
