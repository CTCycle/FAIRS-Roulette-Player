## Startup

Last updated: 2026-07-20

## Local Application Startup

From repository root in PowerShell:

```powershell
.\start_on_windows.ps1
```

`start_on_windows.ps1` is the single interactive entry point. Its menu supports:

- launching the application
- installing or updating dependencies
- initializing the database
- running the test suite
- removing logs
- clearing Python and uv caches
- uninstalling local runtimes and build outputs
- exiting the launcher

What the launcher does:

- prepares or validates portable runtimes in `runtimes/`
- targets the runtime virtual environment through `UV_PROJECT_ENVIRONMENT`
- syncs Python dependencies with `uv`
- installs frontend dependencies as needed
- launches backend with `uvicorn`
- builds the frontend and launches its Vite preview server
- opens the configured frontend URL in the default browser
- verifies backend health and frontend preview readiness before reporting success

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
