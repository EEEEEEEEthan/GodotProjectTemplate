# Dev Loop 启动脚本
$ErrorActionPreference = "Stop"
$LoopRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $LoopRoot

if (-not $env:CURSOR_API_KEY) {
    Write-Error "请先设置环境变量 CURSOR_API_KEY"
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
& .\.venv\Scripts\python.exe main.py
