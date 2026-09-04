## Startup

Last updated: 2026-09-03

## Local Application Startup

From repository root in PowerShell:

```powershell
.\start_on_windows.ps1
```

`start_on_windows.ps1` is the single interactive entry point. Its menu supports:

- launching the application
- closing the application terminal to stop the local application
- checking the locally known `origin/main` status without downloading or applying updates
- updating the application from a non-detached, clean checkout of `main` with `git pull --ff-only origin main`; the launcher never switches branches or modifies local changes
- installing or updating dependencies
- rebuilding the frontend without updating dependencies
- initializing the database
- running the test suite
- removing logs
- clearing Python, uv, and tool caches
- removing saved checkpoints as a separate action
- removing local database and log data while preserving checkpoints
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
- rebuilds the frontend when option 2 is executed, when standalone option 3 is selected, or during option 1 recovery when the environment or frontend build is missing or unusable
- launches the backend with `uvicorn` in a dedicated application terminal and the built frontend with Vite preview
- opens the configured frontend URL in the default browser after both services are ready
- verifies backend health, backend listener presence, frontend HTTP success, and frontend listener presence before reporting success
- uses the application terminal as the local service lifecycle boundary; close it to stop the application and keep the configured ports dedicated to FAIRS
- keeps the backend and in-memory inference sessions alive when the browser or tab closes
- requires one Uvicorn worker because live training and inference state are process-local

Cache layout and cleanup:

- uv, npm, pip, Python bytecode, and other runtime caches are rooted at `runtimes/cache`
- pytest, Ruff, coverage, mypy, Playwright, and other test-tool caches are rooted at `app/tests/cache`
- option 9 removes the canonical runtime and test cache roots; cleanup inventories nested entries deepest-first, preserves required sentinels, and reports locked or administrator-protected entries as skipped
- options 8 through 12 require the exact case-sensitive passphrase `DELETE` before removing logs, caches, checkpoints, local user data, runtimes, dependencies, or build outputs

Database behavior:

- FastAPI lifespan and the explicit CLI/launcher initializer run the same Alembic create/upgrade state machine before repositories and services are constructed.
- Empty SQLite databases upgrade to Alembic `head`; non-empty unversioned databases are rejected unchanged and must be migrated explicitly.
- Partial, unknown, drifted, or ahead schemas fail unchanged with an actionable error. Known revisions behind `head` are upgraded in order; current `head` is a strict-validation no-op.
- SQLite migration locking uses `BEGIN IMMEDIATE`; PostgreSQL database creation uses a deterministic admin advisory lock and target migrations use a transaction advisory lock with a bounded timeout.
- PostgreSQL startup may create a missing configured database only when the initial target connection returns SQLSTATE `3D000`; the configured role must have `CREATEDB`, or an administrator must pre-create the database.
- Option 4 is **Create / upgrade database** and is idempotent. Option 2 runs it after dependency installation and frontend setup. Option 3 remains frontend-only.
- Option 7 updates source only from a non-detached, clean `main` checkout with `git pull --ff-only origin main`. Option 6 compares the current checkout with the locally known `origin/main` reference only; it does not fetch, download, or apply updates.
- Option 10 removes saved checkpoint files separately. Option 11 removes the local embedded database, SQLite sidecars, and log files while preserving checkpoints and tracked application files. An externally configured PostgreSQL database is not deleted by the local launcher.
- Options 8 through 12 cancel without changes unless the `[y/N]` confirmation prompt receives an affirmative response.

`server.app` is import-safe: constructing the FastAPI object and its routes does not load Keras/Torch, read mutable runtime paths, create directories, load `.env`, or configure application logging. The FastAPI lifespan performs `server.bootstrap.bootstrap_runtime()` first, then loads the Keras-backed repositories and services, initializes the database, and publishes the ready state. Shutdown runs in reverse ownership order and isolates cleanup failures.

The runtime state is `starting` during bootstrap, `ready` while serving requests, `stopping` during cleanup, and `stopped` after resources have been released. A startup failure rolls back resources already acquired and does not publish a partially ready application.

`RELOAD=true` is development-only. Uvicorn reloads replace the in-memory process and therefore discard active training jobs and inference sessions; production and normal local runs use one non-reloading worker.

If the readiness check passes, normal application start skips dependency installation and proceeds directly to the two services. If the environment or built frontend is missing or unusable, option 1 recovers dependencies and rebuilds the frontend. Use option 2 when source changes require a deliberate dependency sync, or option 3 when only the frontend needs rebuilding and its dependencies are already installed. Maintenance, database, test, data-removal, update, and uninstall actions require the application terminal to be closed first.

## Test Startup

From repository root in CMD:

```cmd
app\tests\run_tests.bat
```

From repository root in PowerShell:

```powershell
cmd /c app\tests\run_tests.bat
```

The test runner starts live services only when the configured health/HTTP checks are unavailable, records the PIDs it created, and cleans up only those processes. Pre-existing backend or frontend services are left running.

## Related Files

- Read `modes.md` for the supported runtime surface.
- Read `configuration.md` for the settings consumed by these launchers.
