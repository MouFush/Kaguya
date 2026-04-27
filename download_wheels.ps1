# 下载 causal-conv1d 和 mamba-ssm 的预编译 wheel

$urls = @(
    "https://github.com/Dao-AILab/causal-conv1d/releases/download/v1.1.3.post1/causal_conv1d-1.1.3.post1+cu118cxx11abiFALSE-cp310-cp310-win_amd64.whl",
    "https://github.com/state-spaces/mamba/releases/download/v1.1.3.post1/mamba_ssm-1.1.3.post1+cu118cxx11abiFALSE-cp310-cp310-win_amd64.whl"
)

$outputDir = "$env:TEMP\wheels"
$webClient = New-Object System.Net.WebClient
$webClient.DownloadFile($urls[0], "$outputDir\causal_conv1d.whl")
$webClient.DownloadFile($urls[1], "$outputDir\mamba_ssm.whl")

Write-Host "下载完成！文件保存在: $outputDir
Write-Host "请手动安装这些 wheel 文件： pip install $outputDir\causal_conv1d.whl"
Write-Host "然后安装 mamba_ssm"
