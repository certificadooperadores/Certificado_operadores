"""Script integral para levantar la base de datos por primera vez.

Ejecuta secuencialmente:
1. Generación del modelo estrella de operadores maestros desde Excel.
2. Generación del modelo estrella de eventos y comportamientos desde Excel.
3. Consolidación e inicialización de la base de datos SQLite (operadores.db).

Uso recomendado:
    uv run python scripts/levantar_base_datos_primera_vez.py

Autor: Ing. Miguel Angel Ortiz Roldan
"""

import sys
import time
from pathlib import Path

# Raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cargar_excel_a_sqlite
import generar_modelo_estrella_comportamiento
import generar_modelo_estrella_maestro


def main() -> None:
    print("=" * 70)
    print("🚀 INICIALIZACIÓN DE BASE DE DATOS METROCALI MIO (PRIMERA VEZ)")
    print("=" * 70)
    inicio = time.time()

    # Paso 1
    print("\n[PASO 1/3] Generando Modelo Estrella Maestro (Operadores y Eventos)...")
    generar_modelo_estrella_maestro.main()

    # Paso 2
    print("\n[PASO 2/3] Generando Modelo Estrella de Comportamiento e Infracciones...")
    generar_modelo_estrella_comportamiento.main()

    # Paso 3
    print("\n[PASO 3/3] Consolidando hacia SQLite (operadores.db) y configurando tablas...")
    cargar_excel_a_sqlite.main()

    duracion = time.time() - inicio
    print("\n" + "=" * 70)
    print(f"✅ BASE DE DATOS 'operadores.db' LEVANTADA CON ÉXITO en {duracion:.1f}s")
    print("   Ahora puedes iniciar la aplicación con:")
    print("   uv run streamlit run src/certificado_operadores/Inicio.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
