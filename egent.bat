@echo off
setlocal
cd /d "%~dp0addons"
python -m egent %*
