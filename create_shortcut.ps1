$shell = New-Object -ComObject Shell.Application
$Desktop = [Environment]::GetFolderPath("Desktop")
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$Desktop\Easy Dataset.lnk")
$Shortcut.TargetPath = "C:\Users\林智涵\.conda\start_easy_dataset.bat"
$Shortcut.WorkingDirectory = "C:\Users\林智涵\.conda"
$Shortcut.Description = "Easy Dataset - 大模型微调数据集工具"
$Shortcut.Save()
Write-Host "桌面快捷方式已创建成功！"
Write-Host "位置: $Desktop\Easy Dataset.lnk"
Write-Host "双击即可启动 Easy Dataset (http://localhost:1717)"
