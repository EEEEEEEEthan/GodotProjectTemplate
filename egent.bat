@echo off
setlocal
python -c "import egent" 2>nul || pip install -q -e "%~dp0.python\egent"
python "%~dp0.python\example.py" %*
