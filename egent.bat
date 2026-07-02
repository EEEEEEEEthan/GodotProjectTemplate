@echo off
setlocal
python -c "import egent" 2>nul || pip install -q "%~dp0.python"
python "%~dp0.python\example.py" %*
