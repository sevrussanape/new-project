@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" hardware_scanner.py
  ".venv\Scripts\python.exe" -c "from hardware_scanner import scan_hardware; from model_selector import recommend_models; from engine.video_engine import ltx_capability; h=scan_hardware(); print('\\nMODEL ADVISOR:',recommend_models(h)['headline']); print('LTX:',ltx_capability(h))"
) else (
  echo Run ONE_CLICK.bat install first.
)
pause
