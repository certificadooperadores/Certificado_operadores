@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title GESTOR DE PLATAFORMA DE OPERADORES

:menu_principal
cls
echo ==========================================================
echo       GESTOR DE LA PLATAFORMA DE OPERADORES
echo ==========================================================
echo    MENU PRINCIPAL
echo ==========================================================
echo 1. Iniciar Plataforma (ultimo estado guardado)
echo 2. Crear Backup (copia de seguridad de los datos actuales)
echo 3. Restaurar desde un Backup anterior
echo 4. Detener Plataforma
echo 5. Modo Desarrollador (Reconstruir base desde CSV)
echo 6. Info Power BI (conexion desde otro PC)
echo 0. Salir
echo ==========================================================
set /p opcion="Seleccione una opcion (0-6): "

if "%opcion%"=="1" goto normal
if "%opcion%"=="2" goto backup
if "%opcion%"=="3" goto restore
if "%opcion%"=="4" goto stop
if "%opcion%"=="5" goto zero
if "%opcion%"=="6" goto bi
if "%opcion%"=="0" exit

goto menu_principal

:check_docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker no esta abierto. Iniciando Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Esperando a que el motor de Docker arranque ^(esto puede tardar unos minutos^)...
:wait_docker
    timeout /t 5 /nobreak >nul
    docker info >nul 2>&1
    if errorlevel 1 goto wait_docker
    echo Docker iniciado exitosamente!
)
exit /b

:normal
call :check_docker
echo.
echo Levantando plataforma...
cd Contenedor_Proyecto
docker-compose up -d
timeout /t 3 >nul
echo.
echo Consultando version activa de la base de datos...
docker exec operadores_db psql -U mao -d Operadores_bd -t -c "SELECT archivo_origen FROM dim_version_bd ORDER BY id_version DESC LIMIT 1;" > temp_ver.txt 2>nul
set /p version_activa=<temp_ver.txt
del temp_ver.txt 2>nul
echo.
echo ==========================================================
echo   PLATAFORMA INICIADA
echo ==========================================================
echo   Web App:      http://localhost:8505
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do (
    set ip=%%a
    set ip=!ip: =!
    echo   Red local:    http://!ip!:8505
)
echo.
echo   Power BI (Solo Lectura):
echo     Servidor: localhost
echo     Puerto:   5432
echo     Base:     Operadores_bd
echo     Usuario:  consulta
echo     Clave:    consulta2026
if not "%version_activa%"=="" echo.
if not "%version_activa%"=="" echo   Version BD: %version_activa%
echo ==========================================================
echo.
echo Abriendo navegador...
timeout /t 2 >nul
start http://localhost:8505
cd ..
pause
goto menu_principal

:backup
call :check_docker
if not exist "Backups" mkdir Backups

set fecha_hoy=%date:/=-%
set /a version=1
for %%F in (Backups\%fecha_hoy%_V*.sql) do (
    for /f "tokens=2 delims=_V." %%V in ("%%~nF") do (
        if %%V geq !version! set /a version=%%V+1
    )
)
set filename=Backups\%fecha_hoy%_V%version%.sql

echo.
echo Creando backup: %fecha_hoy%_V%version%.sql
echo (Copia de seguridad de los datos ACTUALES de la plataforma)
echo.
docker exec operadores_db pg_dump -U mao -d Operadores_bd --clean > "%filename%"
if %errorlevel% neq 0 (
    echo.
    echo ==========================================================
    echo ERROR: El backup fallo. Verifica que el contenedor este corriendo.
    echo ==========================================================
    pause
    goto menu_principal
)
echo.
echo ==========================================================
echo EXITO: Backup guardado como %fecha_hoy%_V%version%.sql
echo ==========================================================
pause
goto menu_principal

:restore
call :check_docker
if not exist "Backups" mkdir Backups
cls
echo ==========================================================
echo                 RESTAURAR BACKUP
echo ==========================================================
set /a count=0
for %%F in (Backups\*.sql) do (
    set /a count+=1
    set "file!count!=%%~nxF"
    echo !count!. %%~nxF
)
if %count%==0 (
    echo No hay backups disponibles en la carpeta 'Backups'.
    pause
    goto menu_principal
)
echo 0. Cancelar
echo ==========================================================
set /p res_opcion="Seleccione el numero del backup a restaurar: "
if "%res_opcion%"=="0" goto menu_principal

set selected_file=!file%res_opcion%!
if "%selected_file%"=="" (
    echo Opcion invalida.
    pause
    goto restore
)

echo.
echo Preparando restauracion desde: %selected_file%
echo Levantando motor de base de datos...
cd Contenedor_Proyecto
docker-compose up -d
echo Esperando unos segundos para asegurar que Postgres este listo...
timeout /t 5 >nul
echo Restaurando datos...
docker exec -i operadores_db psql -U mao -d Operadores_bd < "..\Backups\!selected_file!"
if %errorlevel% neq 0 (
    echo.
    echo ==========================================================
    echo ERROR: La restauracion fallo.
    echo ==========================================================
    pause
    goto menu_principal
)
echo Registrando version en la base de datos...
docker exec -i operadores_db psql -U mao -d Operadores_bd -c "INSERT INTO dim_version_bd (fecha_backup, archivo_origen, restaurado_por) VALUES ('N/A', '!selected_file!', 'admin_local');"
echo.
echo ==========================================================
echo EXITO: Base de datos restaurada correctamente.
echo ==========================================================
echo Abriendo navegador...
timeout /t 3 >nul
start http://localhost:8505
cd ..
pause
goto menu_principal

:zero
echo.
echo ==========================================================
echo   MODO DESARROLLADOR - Reconstruir desde CSV
echo ==========================================================
echo Esto restaura la base de datos desde los archivos CSV originales.
echo Los cambios no guardados en un backup se perderan.
echo ==========================================================
set /p confirm="Escribe BORRAR para confirmar: "
if not "%confirm%"=="BORRAR" goto menu_principal

call :check_docker
echo.
echo 1. Borrando base de datos antigua...
cd Contenedor_Proyecto
docker-compose down -v
cd ..

echo.
echo 2. (Opcional) Si necesitas regenerar los CSVs nuevos desde los Excels, 
echo    ejecuta tu archivo de python (generar_modelo_estrella_maestro.py) ahora mismo en otra ventana.
echo    Si ya tienes los CSVs listos y quieres continuar, 
pause

echo.
echo 3. Levantando servidor y creando base de datos vacia...
cd Contenedor_Proyecto
docker-compose up -d
echo Esperando a que el motor arranque correctamente...
timeout /t 5 >nul

echo 4. Inyectando CSVs a la base de datos...
docker-compose exec app python init_db.py
if %errorlevel% neq 0 (
    echo.
    echo ==========================================================
    echo ERROR: La inicializacion de la base de datos fallo.
    echo ==========================================================
    pause
    goto menu_principal
)
echo.
echo ==========================================================
echo EXITO: Reconstruccion completa desde cero finalizada.
echo ==========================================================
echo Abriendo navegador...
timeout /t 3 >nul
start http://localhost:8505
cd ..
pause
goto menu_principal

:bi
call :check_docker
cls
echo ==========================================================
echo     POWER BI - CONEXION DESDE OTRO PC
echo ==========================================================
echo.
echo  La plataforma debe estar iniciada (opcion 1).
echo.
echo  Configura estos datos en Power BI:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do (
    set ip=%%a
    set ip=!ip: =!
    echo    Servidor: !ip!
)
echo    Puerto:   5432
echo    Base:     Operadores_bd
echo    Usuario:  consulta
echo    Clave:    consulta2026
echo.
echo ==========================================================
echo  Modo de conexion en Power BI:
echo  1. Obtener datos ^> PostgreSQL
echo  2. Servidor: la IP de arriba, ej: 172.16.2.136
echo  3. Base de datos: Operadores_bd
echo  4. Autenticacion: Basic
echo  5. Usuario: consulta / Clave: consulta2026
echo ==========================================================
pause
goto menu_principal

:stop
echo.
echo Deteniendo la plataforma (los datos estan a salvo)...
cd Contenedor_Proyecto
docker-compose stop
echo Contenedores apagados correctamente.
cd ..
pause
goto menu_principal
