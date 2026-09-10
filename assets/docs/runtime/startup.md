## Startup

Last updated: 2026-09-10

## Local Application Startup

From repository root in PowerShell:

```powershell
.\start_on_windows.ps1
```

`start_on_windows.ps1` is the single interactive Windows entry point for launching, dependency setup, frontend rebuilds, database create/upgrade, testing, maintenance, source updates, and uninstall operations.

## Environment Initialization

- If `settings/.env` does not exist, the launcher copies `settings/.env.example` once.
- An existing `.env` is never supplemented with a hidden compatibility/default map.
- Launcher-critical values must be explicitly present in `.env`: `FASTAPI_HOST`, `FASTAPI_PORT`, `UI_HOST`, `UI_PORT`, `RELOAD`, `BACKEND_LOGS_VISIBLE`, and `EMBEDDED_DATABASE`.
- If one of those values is absent or blank, the launcher fails with an instruction to update `.env` from the current template.

## Runtime Preparation

The launcher prepares or validates:

- portable Python `3.14.2`
- portable `uv`
- Node.js `22.13.0`
- `app/server/.venv`
- frontend dependencies and built `app/client/dist`

`UV_PROJECT_ENVIRONMENT` targets the single server virtual environment. A failed `uv sync` is reported as a failure; the launcher no longer assumes that failure means a legacy environment path and does not delete/recreate the environment as an automatic compatibility retry.

Normal launch skips dependency installation and frontend rebuilding when the runtime is already usable. Missing current runtimes or build output can still be installed/rebuilt through the normal current setup path.

## Cache Ownership

There are two canonical cache roots:

- runtime caches: `runtimes/cache`
- test/tool caches: `app/tests/cache`

The cache action removes only these owned roots and recreates them as needed. The launcher does not discover or clean historical project-local cache names. Obsolete cache directories, if manually left in an old checkout, are not part of current application ownership.

## Application Lifecycle

- Uvicorn is launched with exactly one worker.
- The built frontend is served through Vite preview in the local launcher flow.
- Startup succeeds only after backend health, backend listener, frontend HTTP, and frontend listener checks succeed.
- Closing the browser does not stop the backend or live inference session.
- Closing the application terminal is the local application stop boundary.
- `RELOAD=true` is development-only because a reload discards process-local training and inference state.

## Database Behavior

FastAPI lifespan, the CLI, and the launcher use the same Alembic initializer.

- Empty databases upgrade to `head`.
- Known older Alembic revisions upgrade in order.
- Current `head` performs strict metadata validation.
- Non-empty unversioned databases are rejected unchanged.
- Unknown/ahead revisions, multiple heads, and schema drift fail unchanged.
- PostgreSQL and SQLite use the same schema and repositories.

The current database head is `0002_rename_relative_preference`.

Checkpoint format migration is separate from database migration. Before using pre-v1 checkpoint configuration files, run the explicit one-time checkpoint migration preflight described in `../architecture/persistence.md`.

## Destructive Maintenance

Log removal, cache clearing, checkpoint deletion, local data removal, and uninstall require interactive confirmation.

Uninstall removes only current application-owned runtime/dependency/build locations:

- `runtimes`
- `app/tests/cache`
- `app/server/.venv`
- `app/client/node_modules`
- `app/client/dist`

It does not carry permanent knowledge of obsolete root virtual environments, Angular artifacts, or historical cache paths.

## Source Updates

The update action requires a clean, non-detached `main` checkout and uses `git pull --ff-only origin main`. It does not switch branches, rewrite local changes, or silently merge.

The check-for-updates action compares against the locally known `origin/main` reference and does not fetch.

## Test Startup

From repository root in CMD:

```cmd
app\tests\run_tests.bat
```

From PowerShell:

```powershell
cmd /c app\tests\run_tests.bat
```

## Related Files

- Read `configuration.md` for configuration ownership.
- Read `../architecture/persistence.md` for database and checkpoint migration rules.
- Read `../coding/windows_automation.md` for launcher maintenance conventions.
