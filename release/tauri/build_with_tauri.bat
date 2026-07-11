@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows-release.ps1" %*
exit /b %ERRORLEVEL%
