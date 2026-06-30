@echo off
python -m pip install -r "%~dp0addons\egent\requirements.txt" --quiet
if errorlevel 1 exit /b 1
python "%~dp0egent_handlers\main.py" %*
