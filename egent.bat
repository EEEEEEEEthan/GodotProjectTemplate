@echo off
cd /d "%~dp0"
pip install -r addons\egent\requirements.txt -q
python addons\egent\builtin\main.py %*
