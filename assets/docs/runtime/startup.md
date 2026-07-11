## Startup

Last updated: 2026-07-11

## Local Application Startup

From repository root in PowerShell:

```powershell
.\start_on_windows.ps1
```

`start_on_windows.ps1` is the single interactive entry point. Its menu supports launching the application, installing or updating dependencies, initializing the database, running tests, removing logs, clearing caches, and uninstalling local runtime dependencies.

What the launcher does:

- prepares or validates portable runtimes in `runtimes/`
- targets the runtime virtual environment through `UV_PROJECT_ENVIRONMENT`
- syncs Python dependencies with `uv`
- installs frontend dependencies as needed
- launches backend with `uvicorn`
- builds the frontend and launches its Vite preview server
- opens the configured frontend URL in the default browser

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

- Read `modes.md` for the supported runtime surface.
- Read `configuration.md` for the settings consumed by these launchers.
