@echo off
REM Script para activar el entorno virtual y configurar el proyecto
REM Uso: activate_env.bat

echo ========================================
echo Activando entorno virtual de Dahell...
echo ========================================

REM Activar el venv
call .\venv\Scripts\activate.bat

REM Verificar que estamos en el venv
echo.
echo Python activo:
python --version
echo.
echo Pip activo:
pip --version
echo.

REM Configurar variables de entorno para UTF-8
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ========================================
echo Entorno virtual activado correctamente
echo Variables de encoding configuradas (UTF-8)
echo ========================================
echo.
echo Para instalar dependencias faltantes:
echo   pip install selenium transformers sentence-transformers torchvision
echo.
echo Para ejecutar scripts:
echo   python backend/manage.py [comando]
echo   python scripts/diagnose_system.py
echo.
