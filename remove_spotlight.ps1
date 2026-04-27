# 禁用 Windows Spotlight "了解此图片" 图标
# 方法：通过修改注册表和组策略彻底隐藏该图标

Write-Host "正在禁用 Windows Spotlight 桌面图标..." -ForegroundColor Cyan

# 1. 禁用 ContentDeliveryManager 的所有 Spotlight 相关功能
$cdmPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
$settings = @(
    @{Name="SpotlightOnDesktop"; Value=0},
    @{Name="SubscribedContent-338387Enabled"; Value=0},
    @{Name="SubscribedContent-338388Enabled"; Value=0},
    @{Name="SubscribedContent-338389Enabled"; Value=0},
    @{Name="SubscribedContent-353698Enabled"; Value=0},
    @{Name="RotatingLockScreenOverlayEnabled"; Value=0}
)

foreach ($setting in $settings) {
    New-ItemProperty -Path $cdmPath -Name $setting.Name -Value $setting.Value -PropertyType DWord -Force | Out-Null
    Write-Host "✓ 已设置: $($setting.Name) = $($setting.Value)" -ForegroundColor Green
}

# 2. 在 Explorer Advanced 中禁用 Spotlight 显示
$advancedPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
$advancedSettings = @(
    @{Name="ShowWindowsSpotlightOnDesktop"; Value=0},
    @{Name="ShowSyncProviderNotifications"; Value=0}
)

foreach ($setting in $advancedSettings) {
    New-ItemProperty -Path $advancedPath -Name $setting.Name -Value $setting.Value -PropertyType DWord -Force | Out-Null
    Write-Host "✓ 已设置: $($setting.Name) = $($setting.Value)" -ForegroundColor Green
}

# 3. 隐藏桌面上特定的系统图标（包括 Spotlight）
$hideIconsPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel"
if (-not (Test-Path $hideIconsPath)) {
    New-Item -Path $hideIconsPath -Force | Out-Null
}
New-ItemProperty -Path $hideIconsPath -Name "{2cc5ca98-6795-4fcf-9f92-7f2b10f0b8e1}" -Value 1 -PropertyType DWord -Force | Out-Null
Write-Host "✓ 已隐藏 Spotlight 图标" -ForegroundColor Green

# 4. 禁用 Wallpaper Spotlight
$wallpaperPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Wallpapers"
New-ItemProperty -Path $wallpaperPath -Name "SpotlightsEnabled" -Value 0 -PropertyType DWord -Force | Out-Null
Write-Host "✓ 已禁用壁纸 Spotlight" -ForegroundColor Green

Write-Host "`n正在重启资源管理器以应用更改..." -ForegroundColor Yellow

# 5. 重启资源管理器
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process explorer.exe

Write-Host "`n✅ 完成！'了解此图片' 图标应该已经消失。" -ForegroundColor Green
Write-Host "如果没有立即生效，请稍等几秒钟或重新登录。" -ForegroundColor Yellow
