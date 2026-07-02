@echo off
setlocal
python -c "import egent" 2>nul || pip install -q "%~dp0.loops"
python "%~dp0.loops\agent_dev.py" %*
