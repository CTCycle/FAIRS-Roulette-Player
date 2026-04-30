@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "APP_DIR=%ROOT%\app"
set "SERVER_DIR=%APP_DIR%\server"
set "CLIENT_DIR=%APP_DIR%\client"
set "SETTINGS_DIR=%ROOT%\settings"
set "RUNTIMES_DIR=%ROOT%\runtimes"
set "PYTHON_DIR=%RUNTIMES_DIR%\python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "UV_EXE=%RUNTIMES_DIR%\uv\uv.exe"
set "NODE_EXE=%RUNTIMES_DIR%\nodejs\node.exe"
set "NPM_CMD=%RUNTIMES_DIR%\nodejs\npm.cmd"
set "UV_RUN="
set "NODE_RUN="
set "PYTHON_SYNC="
set "NPM_RUN="
set "DOTENV=%SETTINGS_DIR%\.env"
set "UV_CACHE_DIR=%RUNTIMES_DIR%\.uv-cache"
set "PYPROJECT=%SERVER_DIR%\pyproject.toml"
set "FRONTEND_DIST=%CLIENT_DIR%\dist"
set "FASTAPI_HOST=127.0.0.1"
set "FASTAPI_PORT=8000"
set "UI_HOST=127.0.0.1"
set "UI_PORT=8001"
set "RELOAD=false"
set "OPTIONAL_DEPENDENCIES=false"

if not exist "%PYPROJECT%" (
  echo [FATAL] Missing backend pyproject at "%PYPROJECT%".
  exit /b 1
)
if exist "%UV_EXE%" (
  set "UV_RUN=%UV_EXE%"
) else (
  where uv >nul 2>&1
  if errorlevel 1 (
    echo [FATAL] Missing runtime uv and uv not available in PATH.
    exit /b 1
  )
  set "UV_RUN=uv"
)
if exist "%NODE_EXE%" (
  set "NODE_RUN=%NODE_EXE%"
) else (
  where node >nul 2>&1
  if errorlevel 1 (
    echo [FATAL] Missing runtime node and node not available in PATH.
    exit /b 1
  )
  set "NODE_RUN=node"
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [FATAL] npm not available in PATH.
  exit /b 1
)
set "NPM_RUN=npm"

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
)

if exist "%PYTHON_EXE%" (
  set "PYTHON_SYNC=--python %PYTHON_EXE%"
)

set "UV_EXTRAS="
if /i "%OPTIONAL_DEPENDENCIES%"=="true" set "UV_EXTRAS=--all-extras"

echo [STEP 1/4] Sync Python env in app\server
pushd "%SERVER_DIR%" >nul
call "%UV_RUN%" sync %PYTHON_SYNC% %UV_EXTRAS%
if errorlevel 1 (
  call "%UV_RUN%" sync %UV_EXTRAS%
  if errorlevel 1 (
    if exist "%SERVER_DIR%\.venv\Scripts\python.exe" (
      echo [WARN] uv sync failed; continuing with existing "%SERVER_DIR%\.venv".
    ) else (
      popd >nul
      echo [FATAL] uv sync failed in "%SERVER_DIR%".
      exit /b 1
    )
  )
)
popd >nul

if not exist "%SERVER_DIR%\.venv\Scripts\python.exe" (
  echo [FATAL] Missing venv Python at "%SERVER_DIR%\.venv\Scripts\python.exe".
  exit /b 1
)

echo [STEP 2/4] Install frontend dependencies
pushd "%CLIENT_DIR%" >nul
if not exist "%CLIENT_DIR%\node_modules" (
  if exist "%CLIENT_DIR%\package-lock.json" (
    call "%NPM_RUN%" ci
  ) else (
    call "%NPM_RUN%" install
  )
  if errorlevel 1 (
    popd >nul
    echo [FATAL] npm install failed.
    exit /b 1
  )
)
echo [STEP 3/4] Build frontend
if not exist "%FRONTEND_DIST%" (
  call "%NPM_RUN%" run build
  if errorlevel 1 (
    popd >nul
    echo [FATAL] Frontend build failed.
    exit /b 1
  )
)
popd >nul

if not exist "%FRONTEND_DIST%" (
  echo [FATAL] Frontend dist not found at "%FRONTEND_DIST%".
  exit /b 1
)

echo [STEP 4/4] Launch backend and frontend preview
set "PYTHONPATH=%APP_DIR%"
set "PYTHONNOUSERSITE=1"
set "MPLBACKEND=Agg"
set "KERAS_BACKEND=torch"
if exist "%UV_CACHE_DIR%" rd /s /q "%UV_CACHE_DIR%" >nul 2>&1
start "" /b "%SERVER_DIR%\.venv\Scripts\python.exe" -m uvicorn server.app:app --app-dir "%APP_DIR%" --host %FASTAPI_HOST% --port %FASTAPI_PORT%
start "" /b /d "%CLIENT_DIR%" "%NPM_RUN%" run preview -- --host %UI_HOST% --port %UI_PORT% --strictPort
start "" "http://%UI_HOST%:%UI_PORT%"
echo [SUCCESS] Services started.
exit /b 0
