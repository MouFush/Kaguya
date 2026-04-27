@echo off
chcp 65001 >nul
echo ============================================================
echo LLaMA-Factory 多模态数据集配置工具
echo ============================================================
echo.
echo 正在配置数据集...
echo.

python "%~dp0setup_llama_factory.py"

echo.
echo 按任意键退出...
pause >nul
