@echo off
cd /d "%~dp0"

python -m pip install --quiet colorama >nul 2>&1
python run_cli.py

pause