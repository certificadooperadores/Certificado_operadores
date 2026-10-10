@echo off
chcp 65001 > nul
title Plataforma de Gestion de Operadores - Metrocali MIO

:: Cambiar al directorio raiz donde reside este script .bat
cd /d "%~dp0"

echo ======================================================================
echo    INICIANDO PLATAFORMA DE GESTION DE OPERADORES (METROCALI MIO)
echo ======================================================================
echo.

:: Verificar que exista uv instalado
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se encontro 'uv' instalado en el sistema.
    echo Por favor instala uv desde https://docs.astral.sh/uv/
    echo.
    pause
    exit /b 1
)

:: Verificar si la base de datos existe; si no, avisar
if not exist "operadores.db" (
    echo [AVISO] No se encontro la base de datos 'operadores.db'.
    echo Si es la primera vez que ejecutas el proyecto, ejecuta antes:
    echo   uv run python scripts/levantar_base_datos_primera_vez.py
    echo.
)

echo Lanzando aplicacion Streamlit...
uv run streamlit run src/certificado_operadores/Inicio.py
pause
