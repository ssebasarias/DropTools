@echo off
REM Inicia Backend (Django) en puerto 8000
REM Ejecutar desde la raiz del proyecto: scripts\iniciar_desarrollo.bat
cd /d "%~dp0..\backend"
echo Iniciando Backend Django en http://localhost:8000 ...
python manage.py runserver 0.0.0.0:8000
pause
