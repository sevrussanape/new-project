@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo       LOCAL AI SECRETARY - SETUP
echo ==========================================
echo.
python --version >nul 2>&1 || (echo Python 3.11+ is required. & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
where ollama >nul 2>&1 || echo WARNING: Ollama not found. Install from https://ollama.com/download
if exist requirements.txt python -c "from hardware import detect,recommended_model; h=detect(); print('RAM:',h['ram_gb'],'GB'); print('GPU:',h['gpu']['name']); print('VRAM:',h['gpu']['vram_gb'],'GB'); print('Recommended:',recommended_model(h))"
echo.
echo Setup complete. Run run_web.bat to start the website.
pause
