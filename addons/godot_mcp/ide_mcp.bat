@echo off
cd /d "%~dp0.."
python -m pip install -q -r "godot_mcp\requirements.txt" >nul 2>&1
python -m godot_mcp.ide_mcp
