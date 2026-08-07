@echo off
echo ==========================================
echo  Step 1: Video to Text (Transcribing...)
echo ==========================================
"C:\Users\kashy\AppData\Local\Programs\Python\Python312\python.exe" transcribe.py %1
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo ==========================================
echo  Step 2: Text to Document (Generating MoM...)
echo ==========================================
"C:\Users\kashy\AppData\Local\Programs\Python\Python312\python.exe" create_mom.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo ==========================================
echo  DONE!
echo ==========================================
pause
