# Spec 024 — Refinamiento UX de Reportes, Ancho Fluido y Patrón de Códigos por COT

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Estado  | aprobada                                                             |
| Autor   | Ing. Miguel Angel Ortiz Roldan                                       |
| Fecha   | 2026-10-10                                                           |
| Rama    | `feat/redisenio-ui-metrocali`                                        |
| Relaciona | `023-spec.md`, `010-spec.md` (Reportes), `003-spec.md` (Operadores) |

## 1. Contexto y problema

Tras la implementación de la Spec 023, se identificaron varios problemas graves de experiencia de usuario (UX) en toda la sección de reportes:
1. **Layout Estrangulado en el Centro:** `.block-container` tiene `max-width: 1200px;` en `estilos.py`, comprimiendo toda la interfaz en un bloque angosto en el centro de la pantalla y dejando enormes márgenes en blanco a los lados.
2. **Gráficos Forzados e Inútiles en Reportes:** Se forzó un `st.bar_chart` genérico en todos los reportes, dibujando barras idénticas horizontales para cada código de operador individual (`11016`, `11017`...), lo cual no dice nada ni aporta valor analítico.
   - En el **Consolidado UTRyT**, el usuario especificó que la tabla debe quedar igual pero **sin ningún gráfico**.
   - En listados de auditoría y operacionales (Reincidencias con Determinación, Comportamientos por Operador, Eventos por Tipo), no se deben forzar gráficos por fila de código.
3. **Métricas KPI Absurdas en Todos los Reportes:**
   - Se sumaron numéricamente columnas de códigos y cédulas (`df["Codigo"].sum()`, `df["METROCALI ID"].sum()`), produciendo números monstruosos sin sentido como `203638886` o `2423301`.
   - Se muestra una tarjeta que dice `"Columnas: 8"` o `"Columnas: 10"`, lo cual no agrega ningún valor al usuario.
   - Se deben eliminar totalmente la suma de códigos y la tarjeta de "Columnas".
4. **Empresa `None` y Falta de Filtro de Fechas en Reincidencias:**
   - En el reporte de Reincidencias, códigos genéricos de concesionario (10000, 20000, 30000) muestran `Empresa: None` porque no cruzan con `dim_codigo`. Deben resolverse por su prefijo COT: 1 = Git, 2 = Blanco y Negro (Bnm), 3 = ETM, 4 = Unimetro.
   - El reporte no tiene filtro de rango de fechas y trae todo el histórico de golpe. Debe incluir selector de rango de fechas (o últimos 6 meses por defecto).
5. **Botones de Exportación Perdidos al Final:** Los botones `Exportar a Excel` y `Exportar a CSV` están al final de la página debajo de cientos de filas. El usuario no hace scroll; deben ir en la parte superior, directamente sobre la tabla.
6. **Falta de Nombres de Tipología en Reporte de Operadores por Empresa y Tipología:** Muestra números `1, 2, 3` en lugar de los nombres reales (`Articulado`, `Padrón`, `Alimentador`) de `dim_perfil_tipologia`.
7. **Falta de Filtro por Concesionario en Licencias y Certificados por Vencer:** Se perdió el filtro de empresa concesionaria. El usuario requiere poder filtrar por concesionario.
8. **Patrón de Códigos de Operación por Concesionario (COT):** El siguiente código se calculaba con `MAX(id_codigo) + 1` global. Cada concesionario tiene su propio rango numérico de acuerdo a su ID:
   - Concesionario 1 (GIT): Rango 10001 - 19999 (base 10000)
   - Concesionario 2 (Blanco y Negro / ByN): Rango 20001 - 29999 (base 20000)
   - Concesionario 3 (ETM): Rango 30001 - 39999 (base 30000)
   - Concesionario 4 (UNIMETRO): Rango 40001 - 49999 (base 40000)

## 2. Requerimientos

### R-01: Ancho Fluido y Espacio de Pantalla (`estilos.py`)
- En `src/certificado_operadores/estilos.py`, remover `max-width: 1200px;` de `.block-container`.
- Configurar ancho fluido completo: `max-width: none;` y padding horizontal equilibrado (`padding-left: 2.5rem; padding-right: 2.5rem;`).

### R-02: Supresión Total de Gráficos Innecesarios y Tratamiento de UTRyT
- En `src/certificado_operadores/modulos/reportes/ui.py`:
  - **Consolidado UTRyT se queda como está:** Tabla oficial limpia para exportación, con un simple indicador de `Total Operadores: N` (sin inventar KPIs raros, sin tarjetas técnicas y **sin ningún gráfico**).
  - En reportes operacionales de auditoría (**Reincidencias**, **Comportamientos**, **Eventos por Tipo**): no renderizar gráficos forzados por código individual.

### R-03: KPIs de Negocio Inteligentes por Tipo de Reporte (Prohibido Sumar IDs o Contar Columnas)
- En `src/certificado_operadores/modulos/reportes/ui.py`:
  - **Prohibido terminantemente** hacer `sum()` sobre códigos, cédulas o IDs, y **eliminada por completo** la tarjeta `"Columnas: N"`.
  - Cada reporte debe mostrar KPIs lógicos que aporten valor real de toma de decisiones:
    - **Licencias por Vencer:**
      - `Total por Vencer`
      - `Críticas (< 30 días)`: conteo con `Dias Restantes <= 30`
      - `Concesionarios`: conteo de empresas involucradas
    - **Certificados por Vencer / Vencidos:**
      - `Total Certificados`
      - `Próximos a Vencer (< 30 días)` o `Críticos`
      - `Operadores Únicos`
    - **Operadores por Empresa y Tipología:**
      - `Total Operadores Activos`
      - `Concesionarios Activos`
      - Nombres reales de tipología (`Articulado`, `Padrón`, `Alimentador`) tanto en tabla como en resumen
    - **Reincidencias con Determinación:**
      - `Total Casos`
      - `Pendientes de Determinación`: casos donde `Determinacion` está vacía o es `Pendiente`
      - `Casos Graves`: casos con `Impacto == 'Grave'`
    - **Comportamientos por Operador:**
      - `Total Novedades`
      - `Vehículos Involucrados`: conteo único de vehículos
      - `Rutas Afectadas`: conteo único de rutas

### R-04: Botones de Exportación en la Parte Superior
- En `src/certificado_operadores/modulos/reportes/ui.py`:
  - Mover los botones `Exportar a Excel` y `Exportar a CSV` a la cabecera, inmediatamente encima de la tabla de datos, para que el usuario exporte de inmediato sin tener que desplazarse por toda la tabla.

### R-05: Corrección de Empresa y Filtro de Fechas en Reincidencias
- En `src/certificado_operadores/infra/reportes_repository.py`:
  - En la consulta de `reincidencias`, resolver la Empresa mediante:
    ```sql
    COALESCE(e.nombre_empresa, 
             CASE CAST(SUBSTR(CAST(r.id_codigo AS TEXT), 1, 1) AS INTEGER)
                 WHEN 1 THEN 'Git'
                 WHEN 2 THEN 'Bnm'
                 WHEN 3 THEN 'Etm'
                 WHEN 4 THEN 'Unm'
                 ELSE 'Sin Concesionario'
             END) AS "Empresa"
    ```
  - Incorporar filtro por rango de fechas `r.fecha_inicio` en el toolbar de Reincidencias para evitar cargar todo el histórico sin acotar.

### R-06: Nombres Reales de Tipología en Reporte de Operadores por Empresa y Tipología
- En `src/certificado_operadores/infra/reportes_repository.py`:
  - En la consulta del reporte `operadores_empresa`, hacer `JOIN dim_perfil_tipologia t ON dc.id_perfil_tipologia = t.id_perfil_tipologia` y proyectar el nombre legible de la tipología (`t.tipologia` / `t.nombre_tipologia`) como columna `"Tipologia"`.

### R-07: Filtro de Concesionario en Licencias y Certificados por Vencer
- En los reportes `licencias_vencer` y `certificados_vencer`:
  - Incorporar selector de filtro por **Empresa Concesionaria** (GIT, ByN, ETM, etc.).

### R-08: Generación de Códigos según Patrón de Concesionario (COT)
- En `src/certificado_operadores/infra/repository.py`:
  - `siguiente_codigo(id_empresa: int)` debe calcular:
    - `base = int(id_empresa) * 10000`
    - `limite = (int(id_empresa) + 1) * 10000`
    - Consulta:
      ```sql
      SELECT COALESCE(MAX(id_codigo), :base) + 1 
      FROM dim_codigo 
      WHERE id_codigo >= :base AND id_codigo < :limite
      ```

## 3. Criterios de Aceptación

- [ ] **CA-01:** `.block-container` no restringe el ancho a 1200px; la aplicación ocupa el ancho completo de pantalla.
- [ ] **CA-02:** El reporte "Consolidado UTRyT" mantiene su tabla oficial intacta y no muestra ningún gráfico.
- [ ] **CA-03:** Ningún reporte muestra gráficos de barras por código individual de fila.
- [ ] **CA-04:** Ningún KPI suma identificadores numéricos (códigos/cédulas) ni muestra la tarjeta de "Columnas".
- [ ] **CA-05:** Los botones `Exportar a Excel` y `Exportar a CSV` se ubican en la parte superior, directamente sobre la tabla de datos.
- [ ] **CA-06:** En Reincidencias, la columna `Empresa` nunca muestra `None` (resuelve códigos 10000, 20000, 30000 por prefijo COT) y cuenta con filtro de fechas.
- [ ] **CA-07:** El reporte "Operadores por Empresa y Tipología" muestra nombres legibles de tipología (no números `1, 2, 3`).
- [ ] **CA-08:** "Licencias por Vencer" y "Certificados por Vencer" incluyen filtro por Empresa Concesionaria.
- [ ] **CA-09:** La generación del siguiente código respeta el patrón del concesionario (`10001+` para Git, `20001+` para ByN, `30001+` para ETM, `40001+` para Unimetro).
- [ ] **CA-10:** `pytest -q -W error` ejecuta con 100% de pruebas en verde y cero advertencias.
