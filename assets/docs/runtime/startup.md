## Startup

Last updated: 2026-08-06

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

- creates `settings/.env` from `settings/.env.example` when the active file is missing, without overwriting an existing file
- prepares or validates portable Python `3.14.2`, uv, and Node.js `22.13.0` in `runtimes/`
- targets the runtime virtual environment through `UV_PROJECT_ENVIRONMENT`
- checks whether the application environment is ready before installing
- syncs Python dependencies with `uv` in `Standard` mode when installation is needed
- installs the server's test extra when option 2 is run with `Development` selected
- installs frontend dependencies as needed
- stops a frontend listener on the configured UI port before replacing frontend dependencies
- builds the frontend during dependency installation when `ALWAYS_REBUILD=true`
- launches the backend with `uvicorn` and the built frontend with Vite preview
- opens the configured frontend URL in the default browser
- verifies backend health and frontend preview readiness before reporting success

Database behavior:

- SQLite is created automatically only when its configured `.db` file is missing.
- PostgreSQL is never created or initialized by normal application startup. Select option 3, `Initialize database`, after configuring PostgreSQL.
- Option 3 is non-destructive for an existing SQLite database and is the explicit PostgreSQL initialization path.

If the readiness check passes, normal application start skips dependency installation and proceeds directly to the two services. Use option 2 when source changes require a fresh dependency sync or frontend build.

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
