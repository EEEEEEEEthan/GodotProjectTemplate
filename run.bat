@echo off

if "%CURSOR_API_KEY%"=="" (
    echo ERROR: set CURSOR_API_KEY first
    exit /b 1
)

if not exist ".venv" (
    python -m venv .venv
)

".venv\Scripts\python.exe" -m pip install -q -r .loop/requirements.txt
".venv\Scripts\python.exe" .loop/main.py
