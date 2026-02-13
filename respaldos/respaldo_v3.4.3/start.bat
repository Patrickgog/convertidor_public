@echo off
title Conversor Universal Profesional
echo ======================================================
echo   📡 INICIANDO CONVERSOR UNIVERSAL PROFESIONAL
echo ======================================================
echo.

:: Intentar abrir el navegador en paralelo antes de que streamlit bloquee la consola
echo Intentando abrir el navegador en http://localhost:8501...
start http://localhost:8501

:: Verificar si existe el entorno virtual
if exist .venv\Scripts\activate (
    echo Activando entorno virtual .venv...
    call .venv\Scripts\activate
) else (
    echo [AVISO] .venv no encontrado. Asegurate de tener streamlit instalado globalmente.
)

echo.
echo Ejecutando servidor...
streamlit run app.py --server.port 8501 --server.address localhost

pause
