# Spec 023 — Estandarización Visual Institucional Metrocali MIO y Rediseño Integral de Paneles

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Estado  | aprobada                                                             |
| Autor   | Ing. Miguel Angel Ortiz Roldan                                       |
| Fecha   | 2026-10-10                                                           |
| Rama    | `feat/redisenio-ui-metrocali`                                        |
| Relaciona | `003-spec.md` (Admin Operadores), `010-spec.md` (Reportes)         |

## 1. Contexto y problema

La interfaz actual presenta varias deficiencias de diseño visual y usabilidad identificadas por el usuario:
1. **Exceso de Emojis en Títulos y Pestañas:** Emojis gigantescos (`🗓️`, `📋`, `🔄`, `📊`, `📥`) en encabezados de páginas y pestañas, generando una imagen de "prototipo genérico de IA" poco profesional e informal.
2. **Desalineación Cromática con la Identidad Oficial:** La app utiliza el rojo de acento por defecto de Streamlit y estilos genéricos en lugar de la identidad visual limpia, luminosa y moderna del portal oficial **metrocali.gov.co** (fondo blanco `#FFFFFF`, fondos suaves `#F8FAFC`, azul institucional vivo `#046BD2`, texto grafito `#111827`).
3. **Baja Densidad y Desperdicio de Espacio:** En la pantalla de reportes y eventos, los filtros se apilan verticalmente ocupando filas completas vacías, obligando al usuario a desplazarse innecesariamente.
4. **Módulo de Operadores Desarticulado e Incompleto:** La pantalla de `Administración de Operadores` no tiene inputs ordenados horizontalmente (Cédula, Nombres, Apellidos, Género), permite texto libre para Empresa y Tipología en lugar de desplegables oficiales validados, y carece de un botón funcional de guardado conectado a base de datos.
5. **Logo Institucional Desconectado:** El logo oficial de Metrocali no está integrado en la barra de navegación lateral ni en el encabezado.

## 2. Requerimientos de Diseño y Funcionalidad

### R-01: Configuración de Tema Global Institucional en Streamlit
- En `.streamlit/config.toml`, declarar el bloque `[theme]`:
  ```toml
  [theme]
  primaryColor = "#046BD2"
  backgroundColor = "#FFFFFF"
  secondaryBackgroundColor = "#F8FAFC"
  textColor = "#111827"
  font = "sans serif"
  ```
- Crear `src/certificado_operadores/estilos.py` con una función `inyectar_estilos_metrocali()`:
  - Elimina márgenes superiores excesivos (`.block-container`).
  - Estandariza bordes limpios en tarjetas (`#E5E7EB`).
  - Aplica estilo sobrio y azul institucional en pestañas (`st.tabs`), sin subrayados rojos.
  - Carga el logo oficial `assets/logo_metrocali.png` en la barra lateral con `st.logo` o `st.sidebar.image`.

### R-02: Remoción de Emojis Gigantes y Estandarización de Encabezados
- En todas las páginas (`Inicio.py`, `1_Configuracion.py`, `2_Administracion_Operadores.py`, `3_Reportes.py`):
  - Retirar emojis en `st.title` y en títulos de tabs (`st.tabs`).
  - Usar tipografía limpia institucional: Título claro + subtítulo descriptivo en gris neutro (`#6B7280`).
  - Solo se permiten iconos funcionales o indicadores de color pequeños para estados o alertas del sistema.

### R-03: Rediseño del Formulario de Administración de Operadores
- En `src/certificado_operadores/modulos/admin_operadores/ui.py`:
  - **Fila 1 (Datos Personales):** Columnas alineadas con `st.columns`: `Código Operador`, `Cédula`, `Nombres`, `Apellidos`, `Género` (desplegable: Masculino / Femenino / Otro).
  - **Fila 2 (Datos de Empresa y Asignación):** `Empresa Concesionaria` (desplegable de concesionarias oficiales) y `Tipología de Bus` (desplegable de tipologías oficiales).
  - **Acción:** Botón corporativo `Guardar Operador` (estilo primario `#046BD2`) que invoca a la Facade (`guardar_operador` / `crear_operador`), valida duplicados o vigencias y emite confirmación con `st.success`.

### R-04: Toolbar Horizontal de Filtros y Gráficos Livianos en Reportes
- En `src/certificado_operadores/modulos/reportes/ui.py` y `pages/3_Reportes.py`:
  - Toolbar de filtros compacta en 1 sola fila con `st.columns([2, 2, 1.5, 2, 1])`: `[Tipo de Reporte] [Concesionaria] [Estado] [Fechas] [Filtrar]`.
  - Tarjetas métricas ejecutivas (`st.metric`) con totales y conteos rápidos.
  - Gráfico de barras horizontal nativo (`st.bar_chart`) en azul institucional generado a partir de las agregaciones en SQLite/Pandas (<2 ms).

### R-05: Suite de Pruebas y Cero Advertencias
- Mantener política estricta de cero warnings (`-W error`).
- Agregar pruebas unitarias para `OperadoresFacade.guardar_operador()` e inyección de estilos.

## 3. Criterios de Aceptación

- [ ] **CA-01:** `.streamlit/config.toml` contiene la paleta clara oficial de Metrocali (`primaryColor = "#046BD2"`, `backgroundColor = "#FFFFFF"`).
- [ ] **CA-02:** El logo `assets/logo_metrocali.png` se muestra en la barra lateral de la app.
- [ ] **CA-03:** Ningún título `st.title` ni pestaña `st.tabs` contiene emojis gigantes o informales.
- [ ] **CA-04:** El formulario de `Administración de Operadores` tiene inputs horizontales ordenados para datos personales y desplegables oficiales para Empresa y Tipología.
- [ ] **CA-05:** El botón `Guardar Operador` persiste el operador correctamente a través de la Facade.
- [ ] **CA-06:** La pantalla de reportes agrupa los filtros en una sola barra horizontal y muestra KPIs ejecutivos y gráficos nativos livianos.
- [ ] **CA-07:** La suite de pruebas completa ejecuta en verde con cero warnings (`pytest -q -W error`).
