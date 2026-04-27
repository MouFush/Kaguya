@echo off
chcp 65001 >nul
echo ========================================
echo 强制删除360所有文件
echo ========================================
echo.

echo [1/5] 关闭所有360进程...
taskkill /F /IM 360* >nul 2>&1
taskkill /F /IM namiclaw* >nul 2>&1
taskkill /F /IM claw* >nul 2>&1
echo 进程已关闭

echo.
echo [2/5] 删除AppData文件夹...
rd /s /q "C:\Users\林智涵\AppData\Roaming\360Safe" >nul 2>&1
rd /s /q "C:\Users\林智涵\AppData\Local\360Safe" >nul 2>&1
rd /s /q "C:\Users\林智涵\AppData\LocalLow\360WD" >nul 2>&1
rd /s /q "C:\Users\林智涵\AppData\Roaming\360zip" >nul 2>&1
rd /s /q "C:\Users\林智涵\AppData\Roaming\360Quarant" >nul 2>&1
echo AppData文件夹已删除

echo.
echo [3/5] 删除Program Files文件夹...
rd /s /q "C:\Program Files (x86)\360" >nul 2>&1
echo Program Files文件夹已删除

echo.
echo [4/5] 删除注册表项...
reg delete "HKCU\Software\360Safe" /f >nul 2>&1
reg delete "HKLM\Software\360Safe" /f >nul 2>&1
reg delete "HKLM\Software\Wow6432Node\360Safe" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v namiclaw /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v 360ClawSafe /f >nul 2>&1
echo 注册表已清理

echo.
echo [5/5] 删除快捷方式...
del /f /q "C:\Users\林智涵\Desktop\360安全龙虾.lnk" >nul 2>&1
rd /s /q "C:\Users\林智涵\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\360安全龙虾" >nul 2>&1
echo 快捷方式已删除

echo.
echo ========================================
echo 清理完成!
echo ========================================
echo.
echo 验证清理结果:
if exist "C:\Users\林智涵\AppData\Roaming\360Safe" (
    echo [✗ 残留] AppData\Roaming\360Safe
) else (
    echo [✓ 已删除] AppData\Roaming\360Safe
)

if exist "C:\Users\林智涵\AppData\Local\360Safe" (
    echo [✗ 残留] AppData\Local\360Safe
) else (
    echo [✓ 已删除] AppData\Local\360Safe
)

if exist "C:\Program Files (x86)\360" (
    echo [✗ 残留] Program Files (x86)\360
) else (
    echo [✓ 已删除] Program Files (x86)\360
)

echo.
echo 建议重启电脑以完成清理!
echo.
pause
