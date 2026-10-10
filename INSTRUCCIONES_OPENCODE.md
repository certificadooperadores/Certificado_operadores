# Instrucciones para OpenCode (Ciclo 2 y 3)

Como Arquitecto, he detectado que nuestro script ETL falló porque `sqlalchemy` no está instalado (la instalación anterior de `uv` falló por un problema de OneDrive). Ya corregí el entorno creando `.env` con `UV_LINK_MODE=copy`.

Tu tarea como implementador (OpenCode) es ejecutar los siguientes pasos estrictamente y hacer el commit al finalizar:

## Tarea 1: Instalar dependencias y ejecutar ETL
1. Abre la terminal en la raíz (`Certificado_operadores`).
2. Ejecuta el comando para instalar las dependencias faltantes:
   ```bash
   uv add streamlit sqlalchemy bcrypt python-dotenv
   ```
3. Ejecuta el script ETL que construirá la base de datos SQLite:
   ```bash
   uv run python scripts/cargar_excel_a_sqlite.py
   ```
4. Verifica que se haya creado el archivo `operadores.db` en la raíz.

## Tarea 2: Reestructurar la Arquitectura (Mover App)
1. Mueve todo el contenido de `version_1/Proyecto_BD_operadores/Contenedor_Proyecto/` hacia `src/certificado_operadores/`.
   - `Inicio.py` -> `src/certificado_operadores/Inicio.py`
   - Las carpetas `pages/`, `views/`, `modulos/`, `utils.py` y `db.py` deben quedar dentro de `src/certificado_operadores/`.
2. Modifica **únicamente** `src/certificado_operadores/db.py` para que la conexión apunte al nuevo archivo local en lugar de PostgreSQL. Debe quedar algo así:
   ```python
   import os
   from sqlalchemy import create_engine
   
   # Conectar a SQLite en la raíz del proyecto
   BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   DB_PATH = os.path.join(BASE_DIR, "operadores.db")
   engine = create_engine(f"sqlite:///{DB_PATH}")
   ```

## Tarea 3: Verificación y Commit
1. Ejecuta la aplicación localmente para verificar que levanta con SQLite:
   ```bash
   uv run streamlit run src/certificado_operadores/Inicio.py
   ```
2. Si todo funciona, haz un commit con el mensaje: `feat: migracion a sqlite y reestructuracion a src/`

Por favor, no modifiques reglas de linting ni borres `version_1/` todavía. Ejecuta esto y confírmanos (al Arquitecto y al usuario) cuando las pruebas manuales pasen.
