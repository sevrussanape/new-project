@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -u studio.py >> "%~dp0logs\studio.log" 2>&1
