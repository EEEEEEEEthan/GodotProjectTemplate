# Dev Loop 启动脚本
$ErrorActionPreference = "Stop"
$LoopRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $LoopRoot
Set-Location $LoopRoot

if (-not $env:CURSOR_API_KEY) {
    $envFile = Join-Path $ProjectRoot ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line -match '^\s*CURSOR_API_KEY\s*=\s*(.+)\s*$') {
                $env:CURSOR_API_KEY = $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
}
if (-not $env:CURSOR_API_KEY) {
    Write-Error "请先设置环境变量 CURSOR_API_KEY，或在项目根目录 .env 中配置"
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
& .\.venv\Scripts\python.exe main.py
