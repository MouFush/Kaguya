# 辉夜 AI助手 启动脚本
# 请右键点击此文件，选择"使用 PowerShell 运行"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "辉夜 AI助手 (专业增强版 v3.1)" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Cyan

# 激活conda环境
Write-Host "`n正在激活DL虚拟环境..." -ForegroundColor Yellow
conda activate DL

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 无法激活DL环境" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "环境激活成功!" -ForegroundColor Green
Write-Host "`n正在启动服务器..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

# 切换到脚本所在目录并运行
Set-Location $PSScriptRoot
python qwen3_web.py

Read-Host "`n按回车键退出"
