@echo off
setlocal
title Stock Predictor Launcher

echo =========================================
echo   AI Stock Price Prediction Dashboard
echo =========================================
echo.

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend

if not exist "%BACKEND%" (
    echo [ERROR] Backend folder not found at "%BACKEND%"
    pause
    exit /b
)

if not exist "%FRONTEND%" (
    echo [ERROR] Frontend folder not found at "%FRONTEND%"
    pause
    exit /b
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    pause
    exit /b
)

echo [OK] Python and Node.js found.
echo.

echo [1] Starting Backend (Flask)...
start "Backend Server" cmd /k "cd /d "%BACKEND%" && echo Installing Python dependencies... && pip install -r requirements.txt && echo. && echo Backend running on http://localhost:5000 && echo Press Ctrl+C to stop. && python app.py"

echo [2] Starting Frontend (React)...
start "Frontend" cmd /k "cd /d "%FRONTEND%" && echo Installing npm dependencies... && npm install && echo. && echo Frontend running on http://localhost:3000 && echo Press Ctrl+C to stop. && npm start"

echo.
echo =========================================
echo Both servers are starting up...
echo   Backend  : http://localhost:5000
echo   Frontend : http://localhost:3000
echo.
echo Wait for the React dev server to compile,
echo then open http://localhost:3000 in your browser.
echo =========================================
pause
