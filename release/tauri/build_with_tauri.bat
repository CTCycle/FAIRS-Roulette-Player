@echo off
setlocal enabledelayedexpansion

set "script_dir=%~dp0"
for %%I in ("%script_dir%..\..") do set "repo_root=%%~fI"
set "project_folder=%repo_root%\FAIRS\"
set "client_dir=%project_folder%client"
set "tauri_dir=%client_dir%\src-tauri"
set "bundle_source_dir=%tauri_dir%\r"
set "bundle_dir=%tauri_dir%\target\release\bundle"
set "release_export_dir=%repo_root%\release\windows"
set "runtime_root=%repo_root%\runtimes"
set "runtime_python_exe=%runtime_root%\python\python.exe"
set "runtime_uv_exe=%runtime_root%\uv\uv.exe"
set "runtime_uv_lock=%runtime_root%\uv.lock"
set "runtime_node_dir=%runtime_root%\nodejs"
set "node_cmd=%runtime_node_dir%\node.exe"
set "npm_cmd=%runtime_node_dir%\npm.cmd"


echo [TAURI] Release build helper

echo [CHECK] Validating bundled runtimes...
call :require_file "%runtime_python_exe%" "embedded Python runtime" || goto build_error
call :require_file "%runtime_uv_exe%" "embedded uv runtime" || goto build_error
call :require_file "%node_cmd%" "embedded Node.js runtime" || goto build_error
call :require_file "%npm_cmd%" "embedded npm runtime" || goto build_error
call :require_file "%runtime_uv_lock%" "runtime backend lockfile runtimes\\uv.lock" || goto build_error

echo [CHECK] Preparing short Tauri bundle sources...
call :prepare_bundle_sources || goto build_error


echo [CHECK] Resolving Cargo...
set "cargo_cmd="
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" set "cargo_cmd=%USERPROFILE%\.cargo\bin\cargo.exe"
if not defined cargo_cmd (
  where cargo >nul 2>&1
  if not errorlevel 1 set "cargo_cmd=cargo"
)
if not defined cargo_cmd (
  echo [FATAL] Rust/Cargo not found. Install Rust first: https://rustup.rs/
  goto build_error
)
if /I not "%cargo_cmd%"=="cargo" (
  for %%I in ("%cargo_cmd%") do set "PATH=%%~dpI;%PATH%"
)
set "cargo_version="
for /f "delims=" %%V in ('"%cargo_cmd%" --version 2^>nul') do set "cargo_version=%%V"
if not defined cargo_version (
  call :handle_unusable_cargo "%cargo_cmd%" || goto build_error
  for /f "delims=" %%V in ('"%cargo_cmd%" --version 2^>nul') do set "cargo_version=%%V"
)
if not defined cargo_version (
  echo [FATAL] Unable to read cargo version from "%cargo_cmd%".
  goto build_error
)
echo [INFO] Cargo command: %cargo_cmd%
echo [INFO] !cargo_version!
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

echo [STEP 2/2] Building Tauri application
if exist "%release_export_dir%" (
  echo [INFO] Removing previous exported release folder: "%release_export_dir%"
)
echo [CMD] "%npm_cmd%" run tauri:build:release
call "%npm_cmd%" run tauri:build:release
if errorlevel 1 (
  popd >nul
  echo [FATAL] Tauri build failed.
  goto build_error
)
popd >nul

call :cleanup_bundle_sources

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
echo         Run FAIRS\start_on_windows.bat first to install the portable runtimes.
exit /b 1

:prepare_bundle_sources
call :cleanup_bundle_sources

md "%bundle_source_dir%" >nul 2>&1
if errorlevel 1 (
  echo [FATAL] Failed to create bundle source directory "%bundle_source_dir%".
  exit /b 1
)
md "%bundle_source_dir%\resources" >nul 2>&1
md "%bundle_source_dir%\client" >nul 2>&1
md "%bundle_source_dir%\runtimes" >nul 2>&1

copy /y "%repo_root%\pyproject.toml" "%bundle_source_dir%\pyproject.toml" >nul
if errorlevel 1 (
  echo [FATAL] Failed to stage pyproject.toml for Tauri bundling.
  exit /b 1
)
copy /y "%runtime_uv_lock%" "%bundle_source_dir%\uv.lock" >nul
if errorlevel 1 (
  echo [FATAL] Failed to stage runtime lockfile from "%runtime_uv_lock%" to "%bundle_source_dir%\uv.lock".
  exit /b 1
)
copy /y "%runtime_uv_lock%" "%bundle_source_dir%\runtimes\uv.lock" >nul
if errorlevel 1 (
  echo [FATAL] Failed to stage runtime lockfile at "%bundle_source_dir%\runtimes\uv.lock".
  exit /b 1
)

if exist "%project_folder%resources\database.db" (
  copy /y "%project_folder%resources\database.db" "%bundle_source_dir%\resources\database.db" >nul
) else (
  type nul > "%bundle_source_dir%\resources\database.db"
)

call :make_junction "%bundle_source_dir%\server" "%project_folder%server" || exit /b 1
call :make_junction "%bundle_source_dir%\scripts" "%project_folder%scripts" || exit /b 1
call :make_junction "%bundle_source_dir%\settings" "%project_folder%settings" || exit /b 1
call :make_junction "%bundle_source_dir%\client\dist" "%client_dir%\dist" || exit /b 1
call :make_junction "%bundle_source_dir%\resources\checkpoints" "%project_folder%resources\checkpoints" || exit /b 1
call :make_junction "%bundle_source_dir%\resources\logs" "%project_folder%resources\logs" || exit /b 1
call :make_junction "%bundle_source_dir%\runtimes\python" "%runtime_root%\python" || exit /b 1
call :make_junction "%bundle_source_dir%\runtimes\uv" "%runtime_root%\uv" || exit /b 1
call :make_junction "%bundle_source_dir%\runtimes\nodejs" "%runtime_root%\nodejs" || exit /b 1
exit /b 0

:make_junction
cmd /c mklink /J "%~1" "%~2" >nul
if errorlevel 1 (
  echo [FATAL] Failed to create junction "%~1" -> "%~2".
  exit /b 1
)
exit /b 0

:cleanup_bundle_sources
if exist "%bundle_source_dir%" rd /s /q "%bundle_source_dir%" >nul 2>&1
exit /b 0

:handle_unusable_cargo
set "cargo_probe=%~1"
"%cargo_probe%" --version >nul 2>&1
if not errorlevel 1 exit /b 0
set "rustup_cmd="
if exist "%USERPROFILE%\.cargo\bin\rustup.exe" set "rustup_cmd=%USERPROFILE%\.cargo\bin\rustup.exe"
if not defined rustup_cmd (
  rustup --version >nul 2>&1
  if not errorlevel 1 set "rustup_cmd=rustup"
)
if defined rustup_cmd (
  "%rustup_cmd%" show active-toolchain >nul 2>&1
  if errorlevel 1 (
    echo [FATAL] Cargo exists but no default Rust toolchain is configured.
    echo         Remediation:
    echo           "%rustup_cmd%" toolchain install stable
    echo           "%rustup_cmd%" default stable
    exit /b 1
  )
)
echo [FATAL] Cargo command "%cargo_probe%" is not usable.
if defined rustup_cmd (
  echo         Try:
  echo           "%rustup_cmd%" default stable
) else (
  echo         Install Rust via https://rustup.rs/ and configure a default toolchain.
)
exit /b 1

:build_error
call :cleanup_bundle_sources
echo.
echo Press any key to close this build script...
pause >nul
endlocal & exit /b 1
