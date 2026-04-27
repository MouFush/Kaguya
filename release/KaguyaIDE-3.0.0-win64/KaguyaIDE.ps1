# KaguyaIDE Launcher v3.0.0
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path "KaguyaIDE\KaguyaIDE.exe") {
    & ".\KaguyaIDE\KaguyaIDE.exe" @args
} else {
    python -m start_server @args
}
