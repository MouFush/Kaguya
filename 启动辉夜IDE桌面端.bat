@echo off
chcp 65001 >nul 2>&1
title Kaguya IDE Desktop v3.1.1
color 0A

echo.
echo ================================================
echo   Kaguya IDE Desktop v3.1.1
echo ================================================
echo.

cd /d "%~dp0"

set BASE_DIR=c:\Users\林智涵\.conda\kaguya-desktop\dist\KaguyaIDE-3.1.0-full
set PYTHON_EXE=D:\Anoconda\envs\DL\python.exe

echo [INFO] Base: %BASE_DIR%
echo [INFO] Python: %PYTHON_EXE%

if not exist "%BASE_DIR%\app\qwen3_web.py" (
    echo [ERROR] Application not found!
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at %PYTHON_EXE%
    pause
    exit /b 1
)

echo [OK] Environment ready
echo.

:: Check Electron
if not exist "%BASE_DIR%\electron\node_modules\electron\dist\electron.exe" (
    echo [INFO] Installing Electron...
    cd /d "%BASE_DIR%\electron"
    call npm install --silent --no-fund --no-audit
    if errorlevel 1 (
        echo [ERROR] Failed to install Electron
        pause
        exit /b 1
    )
    cd /d "%BASE_DIR%"
)

:: Set environment
set KAGUYA_DESKTOP_MODE=1
set PYTHONIOENCODING=utf-8
set KAGUYA_PORT=58000

echo [INFO] Starting server...
echo.

:: Start Electron (it will start the Python server internally)
cd /d "%BASE_DIR%\electron"
call npx electron .

echo.
echo [INFO] Application closed
pause >nul
