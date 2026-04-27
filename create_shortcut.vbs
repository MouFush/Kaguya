Set WshShell = WScript.Shell
set DesktopPath = WScript.Shell.SpecialFolders("Desktop")
set ShortcutPath = DesktopPath & "\Easy Dataset.lnk"

set shortcut = WshShell.CreateShortcut(ShortcutPath)
shortcut.TargetPath = "c:\Users\林智涵\.conda\start_easy_dataset.bat"
shortcut.WorkingDirectory = "c:\Users\林智涵\.conda"
shortcut.Description = "Easy Dataset - 大模型微调数据集工具"
shortcut.Save
WScript.Echo "桌面快捷方式已创建成功！"
WScript.Echo "位置: " &ShortcutPath
WScript.Echo "双击即可启动 Easy Dataset"
