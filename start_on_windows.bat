@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_and_maintenance.ps1" -Launch
set "LAUNCHER_EXIT_CODE=%ERRORLEVEL%"
exit /b %LAUNCHER_EXIT_CODE%
