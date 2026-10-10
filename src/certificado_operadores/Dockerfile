# 1. IMAGEN BASE: Arrancamos con un Linux que ya tiene Python 3.10 instalado. 
# La versión "slim" significa que es una versión ligera, sin cosas innecesarias.
FROM python:3.10-slim

# 2. CARPETA DE TRABAJO: Le decimos a Docker que todo lo que hagamos 
# a partir de ahora, ocurrirá dentro de la carpeta "/app" del mini-computador.
WORKDIR /app

# 3. LIBRERÍAS DE LINUX: Streamlit y PostgreSQL a veces necesitan herramientas 
# internas del sistema operativo para funcionar bien. Aquí las instalamos.
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. INSTALAR DEPENDENCIAS DE PYTHON: Copiamos el archivo que acabas de 
# crear y le decimos a "pip" que instale todo lo que pusiste ahí.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. COPIAR NUESTRO CÓDIGO: Copiamos todos los archivos de tu proyecto 
# desde tu PC hacia el interior del contenedor.
COPY . .

# 6. ABRIR EL PUERTO: Streamlit usa el puerto 8505.
# Le decimos a Docker que deje esa "puerta" abierta para poder acceder desde el navegador.
EXPOSE 8505

# 7. LA ORDEN FINAL: ¿Qué debe hacer el contenedor apenas se encienda?
# Respuesta: Ejecutar el comando de Streamlit para arrancar tu app.py.
CMD ["streamlit", "run", "Inicio.py", "--server.port=8505", "--server.address=0.0.0.0"]

