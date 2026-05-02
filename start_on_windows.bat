@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM == Configuration
REM ============================================================================
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "APP_DIR=%ROOT%\app"
set "SERVER_DIR=%APP_DIR%\server"
set "CLIENT_DIR=%APP_DIR%\client"
set "SETTINGS_DIR=%ROOT%\settings"
set "RUNTIMES_DIR=%ROOT%\runtimes"

set "PYTHON_DIR=%RUNTIMES_DIR%\python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHON_PTH_FILE=%PYTHON_DIR%\python314._pth"
set "UV_EXE=%RUNTIMES_DIR%\uv\uv.exe"
set "UV_DIR=%RUNTIMES_DIR%\uv"
set "UV_ZIP_PATH=%UV_DIR%\uv.zip"
set "UV_CACHE_DIR=%RUNTIMES_DIR%\.uv-cache"

set "NODEJS_DIR=%RUNTIMES_DIR%\nodejs"
set "NODE_EXE=%NODEJS_DIR%\node.exe"
set "NPM_CMD=%NODEJS_DIR%\npm.cmd"
set "NODEJS_ZIP_PATH=%NODEJS_DIR%\node.zip"

set "DOTENV=%SETTINGS_DIR%\.env"
set "PYPROJECT=%SERVER_DIR%\pyproject.toml"
set "FRONTEND_DIST=%CLIENT_DIR%\dist"

set "PY_VERSION=3.14.2"
set "PYTHON_ZIP_FILENAME=python-%PY_VERSION%-embed-amd64.zip"
set "PYTHON_ZIP_URL=https://www.python.org/ftp/python/%PY_VERSION%/%PYTHON_ZIP_FILENAME%"
set "PYTHON_ZIP_PATH=%PYTHON_DIR%\%PYTHON_ZIP_FILENAME%"

set "UV_CHANNEL=latest"
set "UV_ZIP_AMD=https://github.com/astral-sh/uv/releases/%UV_CHANNEL%/download/uv-x86_64-pc-windows-msvc.zip"
set "UV_ZIP_ARM=https://github.com/astral-sh/uv/releases/%UV_CHANNEL%/download/uv-aarch64-pc-windows-msvc.zip"

set "NODEJS_VERSION=22.12.0"
set "NODEJS_ZIP_FILENAME=node-v%NODEJS_VERSION%-win-x64.zip"
set "NODEJS_ZIP_URL=https://nodejs.org/dist/v%NODEJS_VERSION%/%NODEJS_ZIP_FILENAME%"

set "FASTAPI_HOST=127.0.0.1"
set "FASTAPI_PORT=8000"
set "UI_HOST=127.0.0.1"
set "UI_PORT=8001"
set "RELOAD=false"
set "OPTIONAL_DEPENDENCIES=false"

set "TMPDL=%TEMP%\app_dl.ps1"
set "TMPEXP=%TEMP%\app_expand.ps1"
set "TMPTXT=%TEMP%\app_txt.ps1"
set "TMPFIND=%TEMP%\app_find_uv.ps1"
set "TMPVER=%TEMP%\app_pyver.ps1"

set "UV_LINK_MODE=copy"

if not exist "%RUNTIMES_DIR%" md "%RUNTIMES_DIR%" >nul 2>&1
if not exist "%PYTHON_DIR%" md "%PYTHON_DIR%" >nul 2>&1
if not exist "%UV_DIR%" md "%UV_DIR%" >nul 2>&1
if not exist "%NODEJS_DIR%" md "%NODEJS_DIR%" >nul 2>&1

> "%TMPDL%"  echo $ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri $args[0] -OutFile $args[1]
> "%TMPEXP%" echo $ErrorActionPreference='Stop'; Expand-Archive -LiteralPath $args[0] -DestinationPath $args[1] -Force
> "%TMPTXT%" echo $ErrorActionPreference='Stop'; (Get-Content -LiteralPath $args[0]) -replace '#import site','import site' ^| Set-Content -LiteralPath $args[0]
> "%TMPFIND%" echo $ErrorActionPreference='Stop'; (Get-ChildItem -LiteralPath $args[0] -Recurse -Filter 'uv.exe' ^| Select-Object -First 1).FullName
> "%TMPVER%" echo $ErrorActionPreference='Stop'; ^& $args[0] -c "import platform;print(platform.python_version())"

REM ============================================================================
REM == Step 1: Ensure Python (embeddable)
REM ============================================================================
echo [STEP 1/5] Setting up Python (embeddable) locally
if not exist "%PYTHON_EXE%" (
  echo [DL] %PYTHON_ZIP_URL%
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPDL%" "%PYTHON_ZIP_URL%" "%PYTHON_ZIP_PATH%" || goto error
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPEXP%" "%PYTHON_ZIP_PATH%" "%PYTHON_DIR%" || goto error
  del /q "%PYTHON_ZIP_PATH%" >nul 2>&1
)
if exist "%PYTHON_PTH_FILE%" (
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPTXT%" "%PYTHON_PTH_FILE%" || goto error
)
for /f "delims=" %%V in ('powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPVER%" "%PYTHON_EXE%"') do set "FOUND_PY=%%V"
echo [OK] Python ready: !FOUND_PY!

REM ============================================================================
REM == Step 2: Ensure uv (portable)
REM ============================================================================
echo [STEP 2/5] Installing uv (portable)
set "UV_ZIP_URL=%UV_ZIP_AMD%"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "UV_ZIP_URL=%UV_ZIP_ARM%"
if not exist "%UV_EXE%" (
  echo [DL] %UV_ZIP_URL%
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPDL%" "%UV_ZIP_URL%" "%UV_ZIP_PATH%" || goto error
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPEXP%" "%UV_ZIP_PATH%" "%UV_DIR%" || goto error
  del /q "%UV_ZIP_PATH%" >nul 2>&1
  for /f "delims=" %%F in ('powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPFIND%" "%UV_DIR%"') do set "FOUND_UV=%%F"
  if not defined FOUND_UV (
    echo [FATAL] uv.exe not found after extraction.
    goto error
  )
  if /i not "%FOUND_UV%"=="%UV_EXE%" copy /y "%FOUND_UV%" "%UV_EXE%" >nul
)
"%UV_EXE%" --version >nul 2>&1 && for /f "delims=" %%V in ('"%UV_EXE%" --version') do echo %%V

REM ============================================================================
REM == Step 3: Ensure Node.js (portable)
REM ============================================================================
echo [STEP 3/5] Installing Node.js (portable)
if not exist "%NODE_EXE%" (
  echo [DL] %NODEJS_ZIP_URL%
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPDL%" "%NODEJS_ZIP_URL%" "%NODEJS_ZIP_PATH%" || goto error
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPEXP%" "%NODEJS_ZIP_PATH%" "%NODEJS_DIR%" || goto error
  del /q "%NODEJS_ZIP_PATH%" >nul 2>&1
)
set "NODE_ARCHIVE_DIR=%NODEJS_DIR%\node-v%NODEJS_VERSION%-win-x64"
if exist "%NODE_ARCHIVE_DIR%\node.exe" (
  call :promote_node_runtime "%NODE_ARCHIVE_DIR%"
  if errorlevel 1 goto error
)
if not exist "%NODE_EXE%" (
  echo [FATAL] node.exe not found in "%NODEJS_DIR%".
  goto error
)
if not exist "%NPM_CMD%" (
  echo [FATAL] npm.cmd not found in "%NODEJS_DIR%".
  goto error
)
for /f "delims=" %%V in ('"%NODE_EXE%" --version') do echo [OK] Node.js ready: %%V

if exist "%DOTENV%" (
  for /f "usebackq tokens=* delims=" %%L in ("%DOTENV%") do (
    set "line=%%L"
    if not "!line!"=="" if "!line:~0,1!" NEQ "#" if "!line:~0,1!" NEQ ";" (
      for /f "tokens=1,* delims==" %%A in ("!line!") do (
        set "k=%%A"
        set "v=%%B"
        if defined v (
          for /f "tokens=* delims= " %%Q in ("!v!") do set "v=%%Q"
          set "v=!v:"=!"
          if "!v:~0,1!"=="'" if "!v:~-1!"=="'" set "v=!v:~1,-1!"
        )
        set "!k!=!v!"
      )
    )
  )
) else (
  echo [INFO] No .env overrides found at "%DOTENV%". Using defaults.
)

set "UV_EXTRAS="
if /i "%OPTIONAL_DEPENDENCIES%"=="true" set "UV_EXTRAS=--all-extras"

echo [INFO] FASTAPI_HOST=%FASTAPI_HOST% FASTAPI_PORT=%FASTAPI_PORT% UI_HOST=%UI_HOST% UI_PORT=%UI_PORT% RELOAD=%RELOAD%

REM ============================================================================
REM == Step 4: Sync Python env
REM ============================================================================
echo [STEP 4/5] Sync Python env in app\server
pushd "%SERVER_DIR%" >nul
"%UV_EXE%" sync --python "%PYTHON_EXE%" %UV_EXTRAS%
if errorlevel 1 (
  "%UV_EXE%" sync %UV_EXTRAS%
  if errorlevel 1 (
    if exist "%SERVER_DIR%\.venv\Scripts\python.exe" (
      echo [WARN] uv sync failed; continuing with existing "%SERVER_DIR%\.venv".
    ) else (
      popd >nul
      echo [FATAL] uv sync failed in "%SERVER_DIR%".
      goto error
    )
  )
)
popd >nul

if not exist "%SERVER_DIR%\.venv\Scripts\python.exe" (
  echo [FATAL] Missing venv Python at "%SERVER_DIR%\.venv\Scripts\python.exe".
  goto error
)

REM ============================================================================
REM == Step 5: Prune uv cache
REM ============================================================================
echo [STEP 5/5] Pruning uv cache
if exist "%UV_CACHE_DIR%" rd /s /q "%UV_CACHE_DIR%" >nul 2>&1

echo [STEP] Installing frontend dependencies...
pushd "%CLIENT_DIR%" >nul
if not exist "%CLIENT_DIR%\node_modules" (
  if exist "%CLIENT_DIR%\package-lock.json" (
    call "%NPM_CMD%" ci
  ) else (
    call "%NPM_CMD%" install
  )
  if errorlevel 1 (
    popd >nul
    echo [FATAL] npm install failed.
    goto error
  )
)

echo [STEP] Building frontend
if not exist "%FRONTEND_DIST%" (
  call "%NPM_CMD%" run build
  if errorlevel 1 (
    popd >nul
    echo [FATAL] Frontend build failed.
    goto error
  )
) else (
  echo [INFO] Frontend build already present at "%FRONTEND_DIST%".
)
popd >nul

if not exist "%FRONTEND_DIST%" (
  echo [FATAL] Frontend dist not found at "%FRONTEND_DIST%".
  goto error
)

set "PYTHONPATH=%APP_DIR%"
set "PYTHONNOUSERSITE=1"
set "MPLBACKEND=Agg"
set "KERAS_BACKEND=torch"

echo [RUN] Launching backend
start "" /b "%SERVER_DIR%\.venv\Scripts\python.exe" -m uvicorn server.app:app --app-dir "%APP_DIR%" --host %FASTAPI_HOST% --port %FASTAPI_PORT%
echo [RUN] Launching frontend
start "" /b /d "%CLIENT_DIR%" "%NPM_CMD%" run preview -- --host %UI_HOST% --port %UI_PORT% --strictPort
start "" "http://%UI_HOST%:%UI_PORT%"
echo [SUCCESS] Services started.
goto cleanup

:promote_node_runtime
set "node_source_dir=%~1"
if not defined node_source_dir exit /b 1
for %%D in ("%~1") do set "node_source_dir=%%~fD"
if /i "!node_source_dir!"=="%NODEJS_DIR%" exit /b 0
robocopy "!node_source_dir!" "%NODEJS_DIR%" /MOVE /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NC /NS >nul
set "node_move_ec=!ERRORLEVEL!"
if !node_move_ec! geq 8 exit /b !node_move_ec!
if exist "!node_source_dir!" rd /s /q "!node_source_dir!" >nul 2>&1
exit /b 0

:cleanup
del /q "%TMPDL%" "%TMPEXP%" "%TMPTXT%" "%TMPFIND%" "%TMPVER%" >nul 2>&1
endlocal & exit /b 0

:error
echo.
echo !!! An error occurred during execution. !!!
pause
del /q "%TMPDL%" "%TMPEXP%" "%TMPTXT%" "%TMPFIND%" "%TMPVER%" >nul 2>&1
endlocal & exit /b 1
