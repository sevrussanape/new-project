@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title OfflineYouTubeStudio - Native Local Engine
if not exist logs mkdir logs
if not exist outputs mkdir outputs
if not exist uploads mkdir uploads
set "MODE=%~1"
if not defined MODE set "MODE=start"
if /i not "%MODE%"=="start" if /i not "%MODE%"=="install" if /i not "%MODE%"=="install-ltx" if /i not "%MODE%"=="check" if /i not "%MODE%"=="channel" if /i not "%MODE%"=="test" (
  echo Usage: ONE_CLICK.bat [start^|install^|install-ltx^|check^|channel^|test]
  pause
  exit /b 2
)
echo ============================================================
echo       OFFLINEYOUTUBESTUDIO - NATIVE PYTHON VIDEO ENGINE
echo ============================================================
echo No ComfyUI server, workflow JSON, or external AI GUI is used.
echo.
call :EnsurePython
if errorlevel 1 goto fail
call :EnsureVenv
if errorlevel 1 goto fail
if /i "%MODE%"=="install" goto install_done
if /i "%MODE%"=="install-ltx" goto install_ltx
if /i "%MODE%"=="check" goto check_hardware
if /i "%MODE%"=="channel" goto run_channel
if /i "%MODE%"=="test" goto run_tests
call :EnsureBaseDeps
if errorlevel 1 goto fail
call :StartStudio
if errorlevel 1 goto fail
exit /b 0

:EnsurePython
if exist ".venv\Scripts\python.exe" goto python_ready
where py >nul 2>&1
if not errorlevel 1 (
  py -3.11 --version >nul 2>&1
  if not errorlevel 1 set "PY_LAUNCH=py -3.11"
)
if not defined PY_LAUNCH (
  where python >nul 2>&1
  if not errorlevel 1 set "PY_LAUNCH=python"
)
if not defined PY_LAUNCH (
  echo ERROR: Python 3.11 was not found.
  echo Install Python 3.11 x64 from https://www.python.org/downloads/ and rerun.
  exit /b 1
)
:python_ready
exit /b 0

:EnsureVenv
if exist ".venv\Scripts\python.exe" goto venv_ready
if not defined PY_LAUNCH (
  where py >nul 2>&1
  if not errorlevel 1 set "PY_LAUNCH=py -3.11"
  if not defined PY_LAUNCH set "PY_LAUNCH=python"
)
echo Creating isolated Python environment...
%PY_LAUNCH% -m venv .venv
if errorlevel 1 exit /b 1
:venv_ready
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
exit /b 0

:EnsureBaseDeps
if exist ".base_deps_installed" exit /b 0
echo Installing lightweight local media dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo installed>".base_deps_installed"
exit /b 0

:install_done
call :EnsureBaseDeps
if errorlevel 1 goto fail
echo Base Offline Studio installation completed.
echo For optional LTX AI inference on a compatible GPU, run ONE_CLICK.bat install-ltx.
pause
exit /b 0

:install_ltx
call :EnsureBaseDeps
if errorlevel 1 goto fail
echo Installing CUDA-enabled PyTorch and native Diffusers libraries.
echo This is a large download. Model weights are downloaded on the first LTX generation.
".venv\Scripts\python.exe" -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu126
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --upgrade diffusers transformers accelerate safetensors huggingface_hub
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "import torch; print('PyTorch:',torch.__version__); print('CUDA available:',torch.cuda.is_available()); print('GPU:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Unavailable')"
if errorlevel 1 goto fail
echo.
echo LTX Python dependencies installed.
echo IMPORTANT: This does not guarantee your GPU meets LTX requirements. Run CHECK_GPU.bat and read the Studio model advisor.
echo The LTX model weights will be downloaded only on the first eligible generation request.
pause
exit /b 0

:check_hardware
".venv\Scripts\python.exe" hardware_scanner.py
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "from hardware_scanner import scan_hardware; from model_selector import recommend_models; from engine.video_engine import ltx_capability; h=scan_hardware(); print('\\nMODEL ADVISOR:',recommend_models(h)['headline']); print('LTX:',ltx_capability(h))"
pause
exit /b 0

:run_tests
call :EnsureBaseDeps
if errorlevel 1 goto fail
echo Running the OfflineYouTubeStudio automated test suite...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto fail
echo All automated tests passed.
pause
exit /b 0

:run_channel
call :EnsureBaseDeps
if errorlevel 1 goto fail
echo YouTube pipeline requires local Ollama. Piper and FFmpeg are optional until narration/final mux.
".venv\Scripts\python.exe" channel_pipeline.py
if errorlevel 1 goto fail
pause
exit /b 0

:StartStudio
call :EnsureBaseDeps
if errorlevel 1 exit /b 1
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8765/api/health' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto open_studio
echo Starting OfflineYouTubeStudio...
start "OfflineYouTubeStudio Native Engine" /min cmd /c ""%~dp0run_studio.bat""
set "WAIT=0"
:wait_studio
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8765/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto open_studio
set /a WAIT+=1
if %WAIT% GEQ 20 (
  echo ERROR: Studio did not start. Last log lines:
  if exist logs\studio.log powershell -NoProfile -Command "Get-Content -LiteralPath 'logs\studio.log' -Tail 50"
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_studio
:open_studio
start "" "http://127.0.0.1:8765"
echo Studio is ready: http://127.0.0.1:8765
echo Log: logs\studio.log
echo The native engine runs inside the Studio Python process.
exit /b 0

:fail
echo.
echo Setup or launch failed. Review the error above and logs\studio.log.
pause
exit /b 1
