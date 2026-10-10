# Manual de usuario — Certificado_operadores

Guía de uso para cargar datos masivos al sistema mediante las plantillas de Excel y los scripts de procesamiento.

## 1. Plantillas de Datos

El sistema utiliza plantillas estándar en formato Excel (`.xlsx`) para importar la información de los operadores y sus eventos. Estas plantillas se encuentran en la carpeta `docs/plantillas/`:

- **`Plantilla_Operadores_Maestra.xlsx`**: Se utiliza para registrar o actualizar los datos maestros de los operadores (nombres, cédula, empresa, tipología).
- **`Plantilla_Eventos_Operadores.xlsx`**: Se utiliza para registrar el historial de eventos (certificaciones, capacitaciones, suspensiones, cancelaciones) que afectan el estado del certificado.

**Nota importante:** No cambie los nombres de las columnas ni el formato de las hojas en estas plantillas para evitar errores durante la carga.

## 2. Cómo cargar los datos (Scripts)

Actualmente, la carga de los archivos Excel hacia la base de datos se realiza mediante scripts de Python ubicados en la carpeta `scripts/`. Siga estos pasos:

1. Llene las plantillas de Excel con la información requerida.
2. Abra una terminal en la carpeta principal del proyecto (`Certificado_operadores`).
3. Ejecute el script correspondiente según lo que desee procesar usando la herramienta `uv` para garantizar que las dependencias funcionen:

```bash
# Para procesar los datos de la plantilla maestra de operadores:
uv run python scripts/generar_modelo_estrella_maestro.py

# Para procesar el historial de comportamientos/eventos:
uv run python scripts/generar_modelo_estrella_comportamiento.py

# Para cargar los datos transformados finalmente a la base de datos SQLite:
uv run python scripts/cargar_excel_a_sqlite.py
```

## 3. Mensajes y errores frecuentes

| Mensaje / Problema | Causa probable | Cómo resolverlo |
|--------------------|----------------|-----------------|
| `FileNotFoundError` | El script no encuentra el archivo Excel. | Verifique que las plantillas llenas estén guardadas en la ruta esperada por los scripts (consulte el interior del script si la ruta cambió). |
| `KeyError` (columna no encontrada) | Se alteró el encabezado en la plantilla Excel. | Restaure el formato original descargando la plantilla limpia desde `docs/plantillas/`. |

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
