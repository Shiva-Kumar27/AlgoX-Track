@echo off
REM AlgoX Track - run from DsaTracker folder
cd /d "%~dp0"
set PYTHONPATH=.
"venv\Scripts\python.exe" app.py
