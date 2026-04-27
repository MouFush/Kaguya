# 全面清理弹窗软件脚本
# 请以管理员身份运行此脚本

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "全面清理弹窗软件和360残留" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan

$deletedItems = @()
$failedItems = @()

# 1. 删除启动项中的360安全龙虾
Write-Host "`n[1/8] 清理启动项..." -ForegroundColor Yellow

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$startupItems = @("namiclaw", "360ClawSafe")

foreach ($item in $startupItems) {
    try {
        Remove-ItemProperty -Path $runKey -Name $item -Force -ErrorAction Stop
        Write-Host "  ✓ 已删除启动项: $item" -ForegroundColor Green
        $deletedItems += "启动项: $item"
    } catch {
        Write-Host "  - 启动项不存在或已删除: $item" -ForegroundColor Gray
    }
}

# 2. 停止并删除360服务
Write-Host "`n[2/8] 清理系统服务..." -ForegroundColor Yellow

$service = Get-Service -Name "Q360AMPPL" -ErrorAction SilentlyContinue
if ($service) {
    try {
        Stop-Service -Name "Q360AMPPL" -Force -ErrorAction SilentlyContinue
        sc.exe delete "Q360AMPPL" | Out-Null
        Write-Host "  ✓ 已删除服务: Q360AMPPL" -ForegroundColor Green
        $deletedItems += "服务: Q360AMPPL"
    } catch {
        Write-Host "  ✗ 服务删除失败: Q360AMPPL" -ForegroundColor Red
        $failedItems += "服务: Q360AMPPL"
    }
} else {
    Write-Host "  - 服务不存在" -ForegroundColor Gray
}

# 3. 强制关闭所有360相关进程
Write-Host "`n[3/8] 关闭相关进程..." -ForegroundColor Yellow

$processes = Get-Process | Where-Object { 
    $_.ProcessName -like "*360*" -or 
    $_.ProcessName -like "*namiclaw*" -or 
    $_.ProcessName -like "*claw*" 
}

if ($processes) {
    $processes | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ 已关闭 $($processes.Count) 个进程" -ForegroundColor Green
} else {
    Write-Host "  - 没有运行中的进程" -ForegroundColor Gray
}

# 4. 删除360安全龙虾安装目录
Write-Host "`n[4/8] 删除360安全龙虾安装目录..." -ForegroundColor Yellow

$paths = @(
    "C:\Users\林智涵\AppData\Roaming\namiclaw",
    "C:\Users\林智涵\AppData\Local\360Safe",
    "C:\Users\林智涵\AppData\Roaming\360Safe",
    "C:\Users\林智涵\AppData\LocalLow\360WD"
)

foreach ($path in $paths) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ 已删除: $path" -ForegroundColor Green
            $deletedItems += "目录: $path"
        } catch {
            Write-Host "  ✗ 删除失败: $path" -ForegroundColor Red
            $failedItems += "目录: $path"
        }
    } else {
        Write-Host "  - 不存在: $path" -ForegroundColor Gray
    }
}

# 5. 删除桌面和开始菜单快捷方式
Write-Host "`n[5/8] 删除快捷方式..." -ForegroundColor Yellow

$shortcuts = @(
    "C:\Users\林智涵\Desktop\360安全龙虾.lnk",
    "C:\Users\林智涵\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\360安全龙虾",
    "C:\Users\林智涵\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\360软件管家.lnk",
    "C:\Users\林智涵\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\360安全卫士.lnk"
)

foreach ($shortcut in $shortcuts) {
    if (Test-Path $shortcut) {
        try {
            Remove-Item -Path $shortcut -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ 已删除: $shortcut" -ForegroundColor Green
            $deletedItems += "快捷方式: $shortcut"
        } catch {
            Write-Host "  ✗ 删除失败: $shortcut" -ForegroundColor Red
            $failedItems += "快捷方式: $shortcut"
        }
    } else {
        Write-Host "  - 不存在: $shortcut" -ForegroundColor Gray
    }
}

# 6. 删除Program Files中的360文件夹
Write-Host "`n[6/8] 删除Program Files中的360..." -ForegroundColor Yellow

$programPaths = @(
    "C:\Program Files (x86)\360"
)

foreach ($path in $programPaths) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ 已删除: $path" -ForegroundColor Green
            $deletedItems += "程序目录: $path"
        } catch {
            Write-Host "  ✗ 删除失败: $path" -ForegroundColor Red
            $failedItems += "程序目录: $path"
        }
    } else {
        Write-Host "  - 不存在: $path" -ForegroundColor Gray
    }
}

# 7. 清理注册表
Write-Host "`n[7/8] 清理注册表..." -ForegroundColor Yellow

$regPaths = @(
    "HKCU:\Software\360Safe",
    "HKLM:\Software\360Safe"
)

foreach ($regPath in $regPaths) {
    if (Test-Path $regPath) {
        try {
            Remove-Item -Path $regPath -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ 已删除注册表: $regPath" -ForegroundColor Green
            $deletedItems += "注册表: $regPath"
        } catch {
            Write-Host "  ✗ 注册表删除失败: $regPath" -ForegroundColor Red
            $failedItems += "注册表: $regPath"
        }
    } else {
        Write-Host "  - 注册表不存在: $regPath" -ForegroundColor Gray
    }
}

# 删除卸载项
$uninstall = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue | 
    Where-Object { $_.DisplayName -like "*龙虾*" -or $_.DisplayName -like "*360*" }

if ($uninstall) {
    Remove-Item -Path $uninstall.PSPath -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ 已删除卸载注册表项" -ForegroundColor Green
}

# 8. 清理计划任务
Write-Host "`n[8/8] 清理计划任务..." -ForegroundColor Yellow

$tasks = Get-ScheduledTask | Where-Object { 
    $_.TaskPath -like "*360*" -or 
    $_.TaskName -like "*360*" -or
    $_.TaskName -like "*namiclaw*"
}

if ($tasks) {
    foreach ($task in $tasks) {
        try {
            Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false -ErrorAction Stop
            Write-Host "  ✓ 已删除计划任务: $($task.TaskName)" -ForegroundColor Green
            $deletedItems += "计划任务: $($task.TaskName)"
        } catch {
            Write-Host "  ✗ 计划任务删除失败: $($task.TaskName)" -ForegroundColor Red
            $failedItems += "计划任务: $($task.TaskName)"
        }
    }
} else {
    Write-Host "  - 没有找到相关计划任务" -ForegroundColor Gray
}

# 总结
Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "清理完成!" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Cyan

Write-Host "`n成功删除的项目:" -ForegroundColor Green
$deletedItems | ForEach-Object { Write-Host "  ✓ $_" -ForegroundColor Green }

if ($failedItems.Count -gt 0) {
    Write-Host "`n删除失败的项目(请手动删除):" -ForegroundColor Red
    $failedItems | ForEach-Object { Write-Host "  ✗ $_" -ForegroundColor Red }
}

Write-Host "`n建议重启电脑以完成清理!" -ForegroundColor Yellow
Write-Host "`n按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
