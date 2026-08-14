@echo off
setlocal
title StudyAI Local - Setup
echo ==========================================
echo          StudyAI Local Setup
echo ==========================================
where python >nul 2>nul
if errorlevel 1 (echo Python 3.11+ was not found. Install Python first.&pause&exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
where ollama >nul 2>nul
if errorlevel 1 (echo Ollama is not installed. Install it from https://ollama.com/download then run setup.bat again.&pause&exit /b 0)
echo Detecting hardware and downloading the recommended local model...
python -c "from app.hardware import detect,recommended_model; from app.setup import ensure_model; h=detect(); m,s,_=recommended_model(h); print(f'Recommended model: {m} (~{s} GB)'); ensure_model(m,print); print('Model ready.')"
if errorlevel 1 (echo Setup failed. Check Ollama and try again.&pause&exit /b 1)
echo Setup complete. Run run.bat.
pause
