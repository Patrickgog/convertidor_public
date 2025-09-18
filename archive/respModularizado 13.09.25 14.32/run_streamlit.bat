@echo off
setlocal
set "DIR=%~dp0"
set "PS1=%TEMP%\run_streamlit_%RANDOM%.ps1"

rem Crear script PowerShell temporal con los comandos deseados
echo Set-Location -LiteralPath '%DIR%' > "%PS1%"
echo if (Test-Path '.\.venv\Scripts\Activate.ps1') { . '.\.venv\Scripts\Activate.ps1' } >> "%PS1%"
echo streamlit run app.py >> "%PS1%"

rem Lanzar PowerShell normal y ejecutar el script, manteniendo la ventana abierta
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "Start-Process PowerShell -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-File','%PS1%'"

endlocal
exit /b 0
