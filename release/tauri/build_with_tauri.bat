@echo off
setlocal enabledelayedexpansion

set "script_dir=%~dp0"
for %%I in ("%script_dir%..\..") do set "repo_root=%%~fI"
set "app_dir=%repo_root%\app"
set "client_dir=%app_dir%\client"
set "tauri_dir=%client_dir%\src-tauri"
set "bundle_source_dir=%tauri_dir%\runtime"
set "release_dir=%tauri_dir%\target\release"
set "bundle_dir=%tauri_dir%\target\release\bundle"
set "release_export_dir=%repo_root%\release\windows"

set "runtime_python_exe=%repo_root%\runtimes\python\python.exe"
set "runtime_uv_exe=%repo_root%\runtimes\uv\uv.exe"
set "runtime_uv_lock=%repo_root%\app\server\uv.lock"
set "runtime_node_dir=%repo_root%\runtimes\nodejs"
set "node_cmd=%runtime_node_dir%\node.exe"
set "npm_cmd=%runtime_node_dir%\npm.cmd"
set "runtime_database_file=%app_dir%\resources\database.db"

echo [TAURI] Release build helper

echo [CHECK] Validating bundled runtimes...
call :require_file "%runtime_python_exe%" "embedded Python runtime" || goto build_error
call :require_file "%runtime_uv_exe%" "embedded uv runtime" || goto build_error
call :require_file "%runtime_uv_lock%" "backend uv lockfile" || goto build_error
call :require_file "%node_cmd%" "embedded Node.js runtime" || goto build_error
call :require_file "%npm_cmd%" "embedded npm runtime" || goto build_error
call :require_file "%app_dir%\server\pyproject.toml" "backend pyproject.toml" || goto build_error
call :require_file "%runtime_database_file%" "runtime sqlite database" || goto build_error

echo [CHECK] Preparing Tauri bundle sources...
call :prepare_bundle_sources || goto build_error

echo [CHECK] Resolving Cargo...
set "cargo_cmd="
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" set "cargo_cmd=%USERPROFILE%\.cargo\bin\cargo.exe"
if not defined cargo_cmd (
  cargo --version >nul 2>&1
  if not errorlevel 1 set "cargo_cmd=cargo"
)
if not defined cargo_cmd (
  echo [FATAL] Rust/Cargo not found. Install Rust first: https://rustup.rs/
  goto build_error
)

set "cargo_probe="
for /f "usebackq delims=" %%V in (`"%cargo_cmd%" --version 2^>^&1`) do (
  if not defined cargo_probe set "cargo_probe=%%V"
)
if not defined cargo_probe set "cargo_probe=unknown cargo probe output"
"%cargo_cmd%" --version >nul 2>&1
if errorlevel 1 (
  echo [WARN] Cargo version probe failed: !cargo_probe!
  echo(!cargo_probe!| findstr /I /C:"rustup could not choose a version of cargo to run" /C:"no default toolchain configured" >nul
  if not errorlevel 1 (
    echo [FATAL] Cargo was found but no default Rust toolchain is configured.
    echo         Run:
    echo           rustup toolchain install stable-x86_64-pc-windows-msvc
    echo           rustup default stable-x86_64-pc-windows-msvc
    echo           rustup show active-toolchain
    goto build_error
  )
  echo [FATAL] Cargo is installed but not runnable.
  echo         Details: !cargo_probe!
  goto build_error
)

set "rustup_cmd="
set "active_toolchain="
if exist "%USERPROFILE%\.cargo\bin\rustup.exe" set "rustup_cmd=%USERPROFILE%\.cargo\bin\rustup.exe"
if not defined rustup_cmd (
  rustup --version >nul 2>&1
  if not errorlevel 1 set "rustup_cmd=rustup"
)
if not defined rustup_cmd (
  echo [WARN] rustup not found; skipping explicit default-toolchain validation.
) else (
  for /f "delims=" %%V in ('"%rustup_cmd%" show active-toolchain 2^>nul') do set "active_toolchain=%%V"
  if not defined active_toolchain (
    echo [FATAL] Cargo was found but no active Rust toolchain is configured.
    echo         Run:
    echo           rustup toolchain install stable-x86_64-pc-windows-msvc
    echo           rustup default stable-x86_64-pc-windows-msvc
    echo           rustup show active-toolchain
    goto build_error
  )
  echo !active_toolchain! | findstr /I /C:"no default toolchain" >nul
  if not errorlevel 1 (
    echo [FATAL] Cargo was found but no default Rust toolchain is configured.
    echo         Run:
    echo           rustup toolchain install stable-x86_64-pc-windows-msvc
    echo           rustup default stable-x86_64-pc-windows-msvc
    echo           rustup show active-toolchain
    goto build_error
  )
  echo [INFO] Rust active toolchain: !active_toolchain!
)
for /f "delims=" %%V in ('"%cargo_cmd%" --version 2^>nul') do set "cargo_version=%%V"
echo [INFO] Cargo command: %cargo_cmd%
if defined cargo_version echo [INFO] !cargo_version!
if /I not "%cargo_cmd%"=="cargo" (
  for %%I in ("%cargo_cmd%") do set "PATH=%%~dpI;%PATH%"
)
set "CARGO=%cargo_cmd%"

if /I not "%node_cmd%"=="node" (
  for %%I in ("%node_cmd%") do set "PATH=%%~dpI;%PATH%"
)

for /f "delims=" %%V in ('"%node_cmd%" --version 2^>nul') do set "node_version=%%V"
for /f "delims=" %%V in ('"%npm_cmd%" --version 2^>nul') do set "npm_version=%%V"
echo [INFO] npm command: %npm_cmd%
echo [INFO] node command: %node_cmd%
if defined node_version echo [INFO] Node.js version: !node_version!
if defined npm_version echo [INFO] npm version: !npm_version!

if not exist "%client_dir%\package.json" (
  echo [FATAL] Missing client package.json at "%client_dir%"
  goto build_error
)

set "RUST_BACKTRACE=1"
set "CARGO_TERM_PROGRESS_WHEN=auto"

echo [STEP 1/2] Installing frontend dependencies
pushd "%client_dir%" >nul
if exist "package-lock.json" (
  echo [CMD] "%npm_cmd%" ci --foreground-scripts
  call "%npm_cmd%" ci --foreground-scripts
) else (
  echo [CMD] "%npm_cmd%" install --foreground-scripts
  call "%npm_cmd%" install --foreground-scripts
)
if errorlevel 1 (
  popd >nul
  echo [FATAL] npm dependency installation failed.
  goto build_error
)

echo [CHECK] Refreshing Tauri bundle sources...
call :prepare_bundle_sources || (
  popd >nul
  goto build_error
)
call :cleanup_stale_release_payload

echo [STEP 2/2] Building Tauri application
echo [CMD] "%npm_cmd%" run tauri:build:release
call "%npm_cmd%" run tauri:build:release
if errorlevel 1 (
  popd >nul
  echo [FATAL] Tauri build failed.
  goto build_error
)
popd >nul

if exist "%bundle_source_dir%" rd /s /q "%bundle_source_dir%" >nul 2>&1

echo [OK] Build completed successfully.
if exist "%release_export_dir%" (
  echo [INFO] User-facing release artifacts:
  echo        %release_export_dir%
) else if exist "%bundle_dir%" (
  echo [INFO] Release artifacts:
  echo        %bundle_dir%
) else (
  echo [WARN] Build finished but release directories were not found.
  echo        %release_export_dir%
  echo        %bundle_dir%
)

endlocal & exit /b 0

:require_file
if exist "%~1" (
  echo [OK] %~2 found: %~1
  exit /b 0
)
echo [FATAL] Missing %~2 at "%~1"
echo         Run start_on_windows.bat first to install portable runtimes.
exit /b 1

:prepare_bundle_sources
if exist "%bundle_source_dir%" rd /s /q "%bundle_source_dir%" >nul 2>&1

md "%bundle_source_dir%" >nul 2>&1
if errorlevel 1 (
  echo [FATAL] Failed to create bundle source directory "%bundle_source_dir%".
  exit /b 1
)
md "%bundle_source_dir%\app" >nul 2>&1
md "%bundle_source_dir%\app\client" >nul 2>&1
md "%bundle_source_dir%\app\client\dist" >nul 2>&1
md "%bundle_source_dir%\app\resources" >nul 2>&1
md "%bundle_source_dir%\app\server" >nul 2>&1
md "%bundle_source_dir%\app\scripts" >nul 2>&1
md "%bundle_source_dir%\runtimes" >nul 2>&1
md "%bundle_source_dir%\runtimes\python" >nul 2>&1
md "%bundle_source_dir%\runtimes\uv" >nul 2>&1
md "%bundle_source_dir%\settings" >nul 2>&1

if not exist "%client_dir%\dist" md "%client_dir%\dist" >nul 2>&1

if not exist "%app_dir%\server" (
  echo [FATAL] Missing server source directory "%app_dir%\server".
  exit /b 1
)
robocopy "%app_dir%\server" "%bundle_source_dir%\app\server" /E /NFL /NDL /NJH /NJS /NP /XD ".venv" "__pycache__" ".pytest_cache" "target" /XF "*.pyc" "*.pyo" >nul
set "robocopy_exit=%errorlevel%"
if !robocopy_exit! GEQ 8 (
  echo [FATAL] Failed to stage filtered backend sources for Tauri bundling.
  exit /b 1
)
robocopy "%app_dir%\scripts" "%bundle_source_dir%\app\scripts" /E /NFL /NDL /NJH /NJS /NP >nul
set "robocopy_exit=%errorlevel%"
if !robocopy_exit! GEQ 8 (
  echo [FATAL] Failed to stage scripts payload.
  exit /b 1
)
robocopy "%repo_root%\settings" "%bundle_source_dir%\settings" /E /NFL /NDL /NJH /NJS /NP >nul
set "robocopy_exit=%errorlevel%"
if !robocopy_exit! GEQ 8 (
  echo [FATAL] Failed to stage settings payload.
  exit /b 1
)
robocopy "%client_dir%\dist" "%bundle_source_dir%\app\client\dist" /E /NFL /NDL /NJH /NJS /NP >nul
set "robocopy_exit=%errorlevel%"
if !robocopy_exit! GEQ 8 (
  echo [FATAL] Failed to stage client dist payload.
  exit /b 1
)
robocopy "%repo_root%\runtimes\python" "%bundle_source_dir%\runtimes\python" /E /NFL /NDL /NJH /NJS /NP >nul
set "robocopy_exit=%errorlevel%"
if !robocopy_exit! GEQ 8 (
  echo [FATAL] Failed to stage python runtime payload.
  exit /b 1
)
robocopy "%repo_root%\runtimes\uv" "%bundle_source_dir%\runtimes\uv" /E /NFL /NDL /NJH /NJS /NP >nul
set "robocopy_exit=%errorlevel%"
if !robocopy_exit! GEQ 8 (
  echo [FATAL] Failed to stage uv runtime payload.
  exit /b 1
)
copy /y "%runtime_database_file%" "%bundle_source_dir%\app\resources\database.db" >nul
if errorlevel 1 (
  echo [FATAL] Failed to stage sqlite database for Tauri bundling.
  exit /b 1
)
exit /b 0

:cleanup_stale_release_payload
if exist "%release_dir%\app" rd /s /q "%release_dir%\app" >nul 2>&1
if exist "%release_dir%\settings" rd /s /q "%release_dir%\settings" >nul 2>&1
if exist "%release_dir%\runtimes" rd /s /q "%release_dir%\runtimes" >nul 2>&1
if exist "%release_dir%\runtime" rd /s /q "%release_dir%\runtime" >nul 2>&1
if exist "%release_dir%\resources" rd /s /q "%release_dir%\resources" >nul 2>&1
if exist "%release_dir%\nsis" rd /s /q "%release_dir%\nsis" >nul 2>&1
if exist "%release_dir%\wix" rd /s /q "%release_dir%\wix" >nul 2>&1
if exist "%bundle_dir%" rd /s /q "%bundle_dir%" >nul 2>&1
exit /b 0

:build_error
if exist "%bundle_source_dir%" rd /s /q "%bundle_source_dir%" >nul 2>&1
if /I "%CI%"=="1" endlocal & exit /b 1
if /I "%CI%"=="true" endlocal & exit /b 1
echo.
echo Press any key to close this build script...
pause >nul
endlocal & exit /b 1
