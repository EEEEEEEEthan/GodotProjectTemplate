@echo off
setlocal
cd /d "%~dp0.python"
python -m egent %*
