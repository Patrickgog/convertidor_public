@echo off
setlocal enabledelayedexpansion
title CONVERSOR UNIVERSAL PROFESIONAL (CUP) - Lanzador

echo ======================================================
echo    📡 CONVERSOR UNIVERSAL PROFESIONAL (CUP)
echo ======================================================
echo.

:: Configuración
set "APP_NAME=CUP"
set "START_PORT=8501"
set "CURRENT_PORT=%START_PORT%"

echo [1/3] 🔍 Buscando puerto libre...

:search_port
powershell -Command "$port = %CURRENT_PORT%; while ((Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) -or (Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue)) { $port++ }; Write-Output $port" > .temp_port.txt
set /p FINAL_PORT=<.temp_port.txt
del .temp_port.txt

if "%FINAL_PORT%"=="" (
    echo ❌ ERROR: No se pudo determinar un puerto libre.
    pause
    exit /b 1
)

echo ✅ Puerto libre detectado: %FINAL_PORT%
echo.

echo [2/3] 🌐 Lanzando navegador en http://localhost:%FINAL_PORT%...
start http://localhost:%FINAL_PORT%

echo [3/3] 🚀 Iniciando aplicación Streamlit...
echo.
echo Presiona Ctrl+C para detener el servidor.
echo.

:: Ejecutar Streamlit
streamlit run app.py --server.port %FINAL_PORT% --server.address=localhost

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR: Falló el inicio de la aplicación.
    echo Asegúrate de tener instalado Streamlit: pip install streamlit
    pause
)

endlocal
