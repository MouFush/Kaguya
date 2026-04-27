@echo off
title KaguyaIDE v3.0.0
echo ============================================
echo   KaguyaIDE v3.0.0
echo   AI-Powered Coding Assistant
echo ============================================
echo.
cd /d "%~dp0"
if exist "KaguyaIDE\KaguyaIDE.exe" (
    start "" "KaguyaIDE\KaguyaIDE.exe" %*
) else (
    echo Starting in Python mode...
    python -m start_server %*
)
