# Requerimientos — Certificado_operadores

Este documento describe qué necesita el usuario y el sistema para ejecutar
`Certificado_operadores`, y qué debe hacer el sistema (requisitos funcionales y no
funcionales).

## 1. Requisitos de software

| Componente | Versión mínima | Notas |
|------------|----------------|-------|
| Sistema operativo | Windows 10+ / Windows 11 / Linux Ubuntu 22.04+ | Recomendado Windows 10/11 con PowerShell. |
| Python | 3.13+ | Fijado y administrado automáticamente vía `uv`. |
| `uv` | 0.5+ | Gestor ultrarrápido de dependencias y entornos virtuales. |
| Git | 2.40+ | Control de versiones y clonación desde GitHub. |
| SQLite | 3.35+ | Motor de base de datos embebido en Python (`operadores.db`). |
| Navegador Web | Chrome 110+ / Edge 110+ / Firefox 115+ | Soporte de WebSockets para Streamlit y canvas para Altair. |

## 2. Requisitos de hardware mínimo

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 núcleos (x86_64) | 4 núcleos o superior |
| RAM | 4 GB | 8 GB o superior (para renderizado de más de 300k eventos) |
| Disco | 2 GB libres | 5 GB libres (base de datos SQLite `~150 MB` + backups `.db`) |
| Red | Conexión a Internet / Intranet | Para sincronización inicial y trabajo colaborativo vía OneDrive |

## 3. Dependencias externas

| Servicio / API | Uso | Cómo obtenerlo |
|----------------|-----|----------------|
| Base de datos local | Almacenamiento transaccional y analítico (`operadores.db`). | Se genera localmente con `scripts/levantar_base_datos_primera_vez.py`. |
| OneDrive institucional | Trabajo colaborativo multi-PC y respaldo en la nube. | Carpeta sincronizada de Metrocali S.A. |

## 4. Requisitos funcionales

- **RF-01 (Autenticación y RBAC):** Control de acceso por roles (Super Administrador, Administrador, Gestor) con contraseñas encriptadas en `bcrypt` y tokens de sesión resistentes a recargas (`F5`).
- **RF-02 (Administración de Operadores):** Búsqueda por cédula/código, creación y asignación automática de códigos por concesionario bajo el patrón COT (`10001` GIT, `20001` ByN, `30001` ETM, `40001` Unimetro).
- **RF-03 (Gestión de Certificados):** Control normativo de vigencia (3 años), cálculo automático de días restantes, registro de certificaciones, reactivaciones, suspensiones y cancelaciones.
- **RF-04 (Comportamientos y Reincidencia):** Registro individual, carga masiva validada contra plantillas Excel, evaluación algorítmica de reincidencias con determinaciones y paginación.
- **RF-05 (Reportes y Analítica Dinámica):** Panel con KPIs no agregados numéricamente, cronograma de vencimientos por quincenas y analítica interactiva tridireccional en Altair tipo Power BI (Operador, Causal, Ruta).
- **RF-06 (Configuración y Respaldo):** Corrección tipo hoja de cálculo con listas oficiales, catálogo maestro de entidades y copias de seguridad asistidas con protección de archivos.

## 5. Requisitos no funcionales

- **RNF-01 (Desacoplamiento - Facade):** La interfaz de usuario (Streamlit) nunca ejecuta SQL directo ni contiene lógica de negocio; toda interacción fluye a través de Facades y Repositorios.
- **RNF-02 (Rendimiento):** Consultas indexadas y optimizadas en SQLite capaces de filtrar en menos de 200 ms sobre un universo superior a 300.000 hechos históricos.
- **RNF-03 (Seguridad):** Prohibición estricta de valores y rutas quemadas en el código; auditoría de exportaciones y modificaciones.
- **RNF-04 (Mantenibilidad):** Suite completa de pruebas automatizadas con cobertura del 100% de casos de uso (388 pruebas en verde).

## 6. Instalación y verificación

```bash
git clone certificadooperadores.git
cd certificado-operadores
uv sync
make check
```

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
