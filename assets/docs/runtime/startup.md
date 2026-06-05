## Startup

Last updated: 2026-06-05

## Local Application Startup

From repository root in CMD:

```cmd
start_on_windows.bat
```

From repository root in PowerShell:

```powershell
cmd /c start_on_windows.bat
```

What the launcher does:

- prepares or validates portable runtimes in `runtimes/`
- targets the runtime virtual environment through `UV_PROJECT_ENVIRONMENT`
- syncs Python dependencies with `uv`
- installs frontend dependencies as needed
- launches backend with `uvicorn`
- launches the frontend preview server

## Desktop Build Startup

From repository root in CMD:

```cmd
release\tauri\build_with_tauri.bat
```

From repository root in PowerShell:

```powershell
cmd /c release\tauri\build_with_tauri.bat
```

Prerequisites:

- Rust and Cargo installed and usable
- prepared runtimes from at least one successful local startup
- frontend build output available for packaging

## Maintenance Startup

From repository root in CMD:

```cmd
setup_and_maintenance.bat
```

From repository root in PowerShell:

```powershell
cmd /c setup_and_maintenance.bat
```

The maintenance menu supports:

- database initialization
- log cleanup
- Python `__pycache__` cleanup
- desktop build cleanup
- runtime-local uninstall or cleanup tasks

## Test Startup

From repository root in CMD:

```cmd
app\tests\run_tests.bat
```

From repository root in PowerShell:

```powershell
cmd /c app\tests\run_tests.bat
```

## Related Files

- Read `modes.md` for when to use each startup path.
- Read `configuration.md` for the settings consumed by these launchers.
