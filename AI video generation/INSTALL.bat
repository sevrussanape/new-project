@echo off
cd /d "%~dp0"
call ONE_CLICK.bat install
exit /b %errorlevel%
