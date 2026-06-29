@echo off
cd /d "%~dp0"
pip install -r .egent\requirements.txt -q
python .egent\builtin\main.py %*
