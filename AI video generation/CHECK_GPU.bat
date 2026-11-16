@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  echo.
  echo OFFLINE STUDIO - HARDWARE AND MODEL DIAGNOSTIC
  echo ==============================================
  ".venv\Scripts\python.exe" hardware_scanner.py
  if errorlevel 1 goto failed
  echo.
  ".venv\Scripts\python.exe" -c "from hardware_scanner import scan_hardware; from model_selector import recommend_models; from engine.video_engine import ltx_capability; h=scan_hardware(); r=recommend_models(h); c=ltx_capability(h); print('MODEL ADVISOR:',r['headline']); print('SELECTED MODEL:',(r['selected_model'] or {}).get('id','None')); print('RUNTIME AVAILABLE:',c['available']); print('BLOCKERS:'); [print(' - '+x) for x in c['blockers']]; print(); print('Note: this diagnostic never installs packages or downloads model weights.')"
  if errorlevel 1 goto failed
) else (
  echo Run ONE_CLICK.bat install first.
)
pause
exit /b 0
:failed
echo Hardware/model diagnostic failed. Check the Python error above.
pause
exit /b 1
