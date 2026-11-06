@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno virtual. Consulta README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m omnifiles
if errorlevel 1 pause
