@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'studio.py' -and $_.Name -match 'python' }; if($p){$p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host 'Offline Studio process stopped.'} else {Write-Host 'No Offline Studio Python process found.'}"
pause
