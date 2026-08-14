@echo off
setlocal
title StudyAI Local
if not exist .venv\Scripts\activate.bat (echo Run setup.bat first.&pause&exit /b 1)
call .venv\Scripts\activate.bat
where ollama >nul 2>nul
if errorlevel 1 (echo Ollama is missing. Run setup.bat after installing Ollama.&pause&exit /b 1)
start "" /min ollama serve
timeout /t 2 /nobreak >nul
streamlit run app\main.py
