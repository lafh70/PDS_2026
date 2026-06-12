@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title PDS_2026 - Asistente PMO

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "VENV_PY=%ROOT%venv\Scripts\python.exe"
set "VENV_ACT=%ROOT%venv\Scripts\activate.bat"

if "%~1"=="" goto MENU
if /i "%~1"=="install" goto INSTALL
if /i "%~1"=="demo" goto DEMO
if /i "%~1"=="test" goto TESTS
if /i "%~1"=="help" goto HELP
goto MENU

:CHECK_VENV
if exist "%VENV_PY%" exit /b 0
echo.
echo [ERROR] No existe el entorno virtual.
echo Ejecuta: PDS_2026.bat install
echo.
pause
exit /b 1

:MENU
cls
echo ============================================================
echo   PDS_2026 - Project Delivery System
echo   Carpeta: %ROOT%
echo ============================================================
echo.
echo   1. Instalar / actualizar (venv + dependencias)
echo   2. Demo rapido (hackathon, 3 fases)
echo   3. Crear cliente nuevo
echo   4. Validar cliente
echo   5. Fase 1 - Generar plantilla Excel
echo   6. Fase 2 - Ingestar Excel completado
echo   7. Fase 3 - Ejecutar pipeline
echo   8. Flujo guiado (crear + validar + plantilla)
echo   9. Ejecutar tests
echo   0. Salir
echo.
set /p OPCION="Elige opcion [0-9]: "

if "%OPCION%"=="1" goto INSTALL
if "%OPCION%"=="2" goto DEMO
if "%OPCION%"=="3" goto CREAR_CLIENTE
if "%OPCION%"=="4" goto VALIDAR
if "%OPCION%"=="5" goto FASE1
if "%OPCION%"=="6" goto FASE2
if "%OPCION%"=="7" goto FASE3
if "%OPCION%"=="8" goto FLUJO_GUIADO
if "%OPCION%"=="9" goto TESTS
if "%OPCION%"=="0" exit /b 0
echo Opcion invalida.
timeout /t 2 >nul
goto MENU

:INSTALL
cls
echo === Instalacion PDS_2026 ===
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta en el PATH. Instala Python 3.10+.
    pause
    goto MENU
)
if not exist "%ROOT%venv" (
    echo Creando entorno virtual...
    python -m venv "%ROOT%venv"
)
call "%VENV_ACT%"
echo Instalando dependencias...
python -m pip install --upgrade pip
pip install -r "%ROOT%requirements.txt"
pip install -e "%ROOT%"
echo.
echo [OK] Instalacion completada.
pause
goto MENU

:DEMO
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Demo hackathon (seed_demo) ===
call "%VENV_ACT%"
python "%ROOT%scripts\seed_demo.py"
echo.
pause
goto MENU

:ASK_CLIENTE
set "CLIENTE="
set /p CLIENTE="Codigo del cliente (ej: hackathon, galicia, mi_cliente): "
if "%CLIENTE%"=="" (
    echo Debes indicar un codigo de cliente.
    pause
    goto MENU
)
exit /b 0

:CREAR_CLIENTE
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Crear cliente nuevo ===
set "CLIENTE="
set /p CLIENTE="Codigo cliente (sin espacios, ej: acme): "
if "%CLIENTE%"=="" goto MENU
set "NOMBRE="
set /p NOMBRE="Nombre display (ej: ACME Corp): "
if "%NOMBRE%"=="" set "NOMBRE=%CLIENTE%"
call "%VENV_ACT%"
python "%ROOT%scripts\setup_cliente.py" %CLIENTE% --name "%NOMBRE%"
echo.
echo Edita config en: config\clients\%CLIENTE%\
pause
goto MENU

:VALIDAR
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Validar cliente ===
call :ASK_CLIENTE
call "%VENV_ACT%"
python "%ROOT%scripts\validar_cliente.py" %CLIENTE%
echo.
pause
goto MENU

:FASE1
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Fase 1 - Plantilla Excel ===
call :ASK_CLIENTE
call "%VENV_ACT%"
python "%ROOT%scripts\generar_plantilla_excel.py" --client %CLIENTE%
echo.
echo Plantilla en: entrada_canonica\
pause
goto MENU

:FASE2
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Fase 2 - Ingesta ===
call :ASK_CLIENTE
set "RUTA="
set /p RUTA="Ruta al Excel completado: "
if "%RUTA%"=="" goto MENU
if not exist "%RUTA%" (
    echo [ERROR] Archivo no encontrado: %RUTA%
    pause
    goto MENU
)
call "%VENV_ACT%"
python "%ROOT%scripts\ingestar.py" --client %CLIENTE% --ruta "%RUTA%"
echo.
pause
goto MENU

:FASE3
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Fase 3 - Pipeline ETL ===
call :ASK_CLIENTE
call "%VENV_ACT%"
python "%ROOT%scripts\run_pipeline.py" --client %CLIENTE%
echo.
echo Salidas en: out_\
pause
goto MENU

:FLUJO_GUIADO
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Flujo guiado: nuevo cliente ===
set "CLIENTE="
set /p CLIENTE="Codigo cliente (ej: acme): "
if "%CLIENTE%"=="" goto MENU
set "NOMBRE="
set /p NOMBRE="Nombre display: "
if "%NOMBRE%"=="" set "NOMBRE=%CLIENTE%"
call "%VENV_ACT%"
echo.
echo [1/3] Creando cliente...
python "%ROOT%scripts\setup_cliente.py" %CLIENTE% --name "%NOMBRE%"
echo.
echo [2/3] Validando...
python "%ROOT%scripts\validar_cliente.py" %CLIENTE%
echo.
echo [3/3] Generando plantilla Excel...
python "%ROOT%scripts\generar_plantilla_excel.py" --client %CLIENTE%
echo.
echo [OK] Siguiente paso manual:
echo   1. Editar config\clients\%CLIENTE%\
echo   2. Completar plantilla en entrada_canonica\
echo   3. Menu opcion 6 (ingesta) y luego 7 (pipeline)
pause
goto MENU

:TESTS
call :CHECK_VENV
if errorlevel 1 goto MENU
cls
echo === Tests ===
call "%VENV_ACT%"
python -m pytest "%ROOT%tests" -q
echo.
pause
goto MENU

:HELP
echo.
echo Uso:
echo   PDS_2026.bat           Menu interactivo
echo   PDS_2026.bat install   Instalar dependencias
echo   PDS_2026.bat demo      Demo hackathon
echo   PDS_2026.bat test      Ejecutar tests
echo.
exit /b 0
