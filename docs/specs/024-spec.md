# Spec 024 — Refinamiento UX de Reportes, Ancho Fluido y Patrón de Códigos por COT

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| Estado  | aprobada                                                             |
| Autor   | Ing. Miguel Angel Ortiz Roldan                                       |
| Fecha   | 2026-10-10                                                           |
| Rama    | `feat/redisenio-ui-metrocali`                                        |
| Relaciona | `023-spec.md`, `010-spec.md` (Reportes), `003-spec.md` (Operadores) |

## 1. Contexto y problema

Tras la implementación de la Spec 023, se identificaron varios problemas de experiencia de usuario (UX), presentación y consistencia:
1. **Layout Estrangulado en el Centro:** `.block-container` tiene `max-width: 1200px;` en `estilos.py`, lo que fuerza a Streamlit a comprimir toda la interfaz en un bloque angosto en el centro de la pantalla, dejando enormes márgenes en blanco a los lados y arruinando la vista de tablas y formularios.
2. **Gráficos Forzados e Inútiles en Reportes:** Se agregó un `st.bar_chart` genérico en todos los reportes, dibujando barras idénticas horizontales para cada código de operador (`11016`, `11017`...), lo cual carece de valor analítico.
   - En el **Consolidado UTRyT**, el usuario especificó que la tabla debe quedar igual pero **sin ningún gráfico**.
   - En listados operacionales (Reincidencias con Determinación, Comportamientos por Operador), no se debe forzar gráficos por fila individual.
3. **Falta de Nombres de Tipología en Reporte de Operadores por Empresa y Tipología:** Muestra números `1, 2, 3` en lugar de los nombres reales (`Articulado`, `Padrón`, `Alimentador`) de `dim_perfil_tipologia`.
4. **Falta de Filtro por Concesionario en Licencias y Certificados por Vencer:** Se perdió el filtro de empresa concesionaria. El usuario requiere poder filtrar por concesionario y ver una visualización temporal útil (distribución por concesionario y rangos de días de vencimiento).
5. **Métricas KPI Absurdas:** Se calcula `sum()` sobre columnas de identificadores numéricos (`df["Codigo"].sum()`, `df["METROCALI ID"].sum()`), mostrando números gigantescos sin sentido (ej. `203638886`), y una tarjeta con el conteo de "Columnas".
6. **Patrón de Códigos de Operación por Concesionario (COT):** El siguiente código se calculaba con `MAX(id_codigo) + 1` global. Cada concesionario tiene su propio rango numérico de acuerdo a su ID:
   - Concesionario 1 (GIT): Rango 10001 - 19999 (base 10000)
   - Concesionario 2 (Blanco y Negro / ByN): Rango 20001 - 29999 (base 20000)
   - Concesionario 3 (ETM): Rango 30001 - 39999 (base 30000)
   - Concesionario 4 (UNIMETRO): Rango 40001 - 49999 (base 40000)

## 2. Requerimientos

### R-01: Ancho Fluido y Espacio de Pantalla (`estilos.py`)
- En `src/certificado_operadores/estilos.py`, remover `max-width: 1200px;` de `.block-container`.
- Configurar ancho fluido completo: `max-width: none;` y padding horizontal equilibrado (`padding-left: 2.5rem; padding-right: 2.5rem;`).

### R-02: Supresión de Gráficos Innecesarios en Reportes Tabulares
- En `src/certificado_operadores/modulos/reportes/ui.py`:
  - **Consolidado UTRyT:** Conservar la tabla oficial y eliminar la sección de gráficos por completo.
  - En reportes operacionales de auditoría (**Reincidencias con Determinación**, **Comportamientos por Operador**, **Eventos por Tipo**): no renderizar `st.bar_chart` por fila individual.

### R-03: Nombres Reales de Tipología y Gráfico con Sentido
- En `src/certificado_operadores/infra/reportes_repository.py`:
  - En la consulta del reporte `operadores_empresa`, hacer `JOIN dim_perfil_tipologia t ON dc.id_perfil_tipologia = t.id_perfil_tipologia` y proyectar el nombre legible de la tipología (`t.tipologia` o similar) como columna `"Tipologia"`.
- En la UI de este reporte, permitir visualizar gráfico de barras o torta con las etiquetas legibles de Tipología por Concesionario.

### R-04: Filtro de Concesionario y Agrupación Temporal en Licencias y Certificados
- En los reportes `licencias_vencer` y `certificados_vencer`:
  - Incorporar selector de filtro por **Empresa Concesionaria**.
  - Si se muestra gráfico, graficar la distribución agregada de licencias/certificados por Concesionario en intervalos de tiempo (ej. `<30 días`, `30-60 días`, `60-90 días`), nunca una barra por cada operador individual.

### R-05: Estandarización de KPIs de Negocio
- Reemplazar las métricas actuales:
  - Eliminar `.sum()` sobre IDs o códigos numéricos.
  - Eliminar la tarjeta de "Columnas".
  - Mostrar: `Total Registros`, `Operadores Únicos` o métricas semánticas contextuales.

### R-06: Generación de Códigos según Patrón de Concesionario (COT)
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

### R-07: Botones de Exportación en la Parte Superior
- En `src/certificado_operadores/modulos/reportes/ui.py`:
  - Mover los botones `Exportar a Excel` y `Exportar a CSV` a la cabecera de la tabla (inmediatamente encima de ella, alineados con el resumen de registros o en una barra de acciones superior), evitando que el usuario deba desplazarse verticalmente hasta el final de cientos de filas para exportar.

## 3. Criterios de Aceptación

- [ ] **CA-01:** `.block-container` no restringe el ancho a 1200px; la aplicación ocupa el ancho completo de pantalla.
- [ ] **CA-02:** El reporte "Consolidado UTRyT" mantiene su tabla oficial intacta y no muestra ningún gráfico.
- [ ] **CA-03:** El reporte "Operadores por Empresa y Tipología" muestra nombres legibles de tipología (no números `1, 2, 3`).
- [ ] **CA-04:** "Licencias por Vencer" y "Certificados por Vencer" incluyen filtro por Empresa Concesionaria.
- [ ] **CA-05:** Ningún KPI suma identificadores numéricos ni muestra el número de columnas.
- [ ] **CA-06:** La generación del siguiente código respeta el patrón del concesionario (`10001+` para Git, `20001+` para ByN, `30001+` para ETM, `40001+` para Unimetro).
- [ ] **CA-07:** Los botones `Exportar a Excel` y `Exportar a CSV` se ubican en la parte superior, directamente sobre la tabla de datos.
- [ ] **CA-08:** `pytest -q -W error` ejecuta con 100% de pruebas en verde y cero advertencias.
