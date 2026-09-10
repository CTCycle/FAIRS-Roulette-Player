## Windows Automation

Last updated: 2026-09-10

## Scope

This file defines repository-specific rules for the PowerShell launcher and Windows automation.

## PowerShell Rules

- Keep startup and maintenance flows consolidated in `start_on_windows.ps1`.
- Do not introduce parallel bootstrap or compatibility paths unless a current requirement is demonstrated.
- `Standard` installation syncs runtime dependencies. `Development` additionally installs the server test extra.
- `settings/.env.example` is the canonical launcher environment template. The launcher may create a missing `.env` from it once, but must not supply a separate hardcoded defaults map for stale existing files.
- Existing `.env` files missing launcher-critical keys must fail clearly rather than inherit obsolete behavior.

## Runtime Layout

Current launcher-owned runtime locations are:

- `runtimes/python`
- `runtimes/uv`
- `runtimes/nodejs`
- `app/server/.venv`
- `app/client/node_modules`
- `app/client/dist`

The launcher may create or replace these current runtimes when their expected executable/version is unavailable. This is current setup behavior, not legacy compatibility.

A failed dependency sync is surfaced directly. Do not interpret it as evidence of an old checkout location and automatically destroy/recreate the virtual environment.

## Cache Ownership

Only two cache roots are owned by current automation:

- `runtimes/cache`
- `app/tests/cache`

Tool-specific cache environment variables point below these roots. Cache clearing and uninstall operate on these canonical locations. Do not recursively discover historical `.uv-cache`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, Vite cache, or similar paths elsewhere in the repository.

## Lifecycle Rules

- Maintenance, database, testing, update, uninstall, and data-removal actions require the application terminal to be closed.
- There is no separate stop daemon. Closing the application terminal is the local stop action; closing the browser is not.
- Startup is complete only after backend and frontend readiness checks succeed.
- Uvicorn runs with one worker because training jobs and live inference models are process-local.
- `RELOAD=true` is development-only and replaces process-local state.
- Destructive operations require the launcher's explicit interactive confirmation.

## Uninstall Scope

Uninstall removes current runtime, dependency, cache, and build targets only. It does not retain permanent cleanup knowledge for superseded root virtual environments, Angular build directories, or old cache conventions.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/configuration.md` for configuration ownership.
- Read `../runtime/deployment.md` for the supported local distribution boundary.
