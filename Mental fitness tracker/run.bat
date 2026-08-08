@echo off
setlocal
cd /d "%~dp0"

set PYTHON=C:\Users\kashy\AppData\Local\Programs\Python\Python312\python.exe
if not exist "%PYTHON%" (
  where python >nul 2>&1 && set PYTHON=python
)
if not exist "%PYTHON%" (
  where py >nul 2>&1 && set PYTHON=py
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  "%PYTHON%" -m venv .venv
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q

if not exist "models\mental_fitness_model.joblib" (
  echo Training model...
  ".venv\Scripts\python.exe" -m src.train
)

echo Starting dashboard...
".venv\Scripts\python.exe" -m streamlit run app\streamlit_app.py
