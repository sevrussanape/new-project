@echo off
cd /d "%~dp0"
call ONE_CLICK.bat channel
exit /b %errorlevel%
