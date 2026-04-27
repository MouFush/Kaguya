@echo off
chcp 65001 >nul 2>&1
set KAGUYA_SOURCE_DIR=%~dp0..
set KAGUYA_DESKTOP_MODE=1
set KAGUYA_ELECTRON=1
set KAGUYA_PERMISSION_MODE=bypassPermissions
cd /d "%~dp0"
npm start
pause
