@echo off
chcp 65001 >nul
echo ============================================================
echo 辉夜 AI助手 (专业增强版 v3.1.1 - 安全加固版)
echo ============================================================
echo.
echo 正在激活DL虚拟环境...
call conda activate DL
if errorlevel 1 (
    echo 错误: 无法激活DL环境，请确保已创建该环境
    pause
    exit /b 1
)
echo.
echo 正在启动服务器...
echo ============================================================
python "%~dp0qwen3_web.py"
pause
