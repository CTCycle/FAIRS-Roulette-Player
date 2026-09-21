## Windows Automation

Last updated: 2026-09-21

## Scope

This file defines repository-specific rules for the PowerShell launcher and Windows automation.

## PowerShell Rules

- Keep startup and maintenance flows consolidated in `start_on_windows.ps1`.
- Do not introduce parallel bootstrap or compatibility paths unless a current requirement is demonstrated.
- `Standard` installation syncs runtime dependencies. `Development` additionally installs the server test extra and Playwright Chromium below `runtimes/cache/playwright-browsers`.
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

`runtimes/cache` is the only cache root owned by current automation. Fixed child directories hold uv, npm, pip, Python bytecode, pytest, pytest basetemp, Ruff, mypy, coverage, Playwright, Vite, TypeScript, Keras, Torch, Triton, Matplotlib, XDG, and CUDA cache data. Cache clearing and uninstall operate on this root only. Do not recursively discover or create cache directories elsewhere in the repository.

## Lifecycle Rules

- Maintenance, database, testing, update, uninstall, and data-removal actions require the application terminal to be closed.
- There is no separate stop daemon. Closing the application terminal is the local stop action; closing the browser is not.
- The maintenance menu's `Stop all app processes` action requires confirmation and stops repository-owned backend/frontend processes together with their child process tree; it does not target browser processes.
- Startup launches the backend and frontend preview independently. The launcher waits for the frontend listener; the browser owns the bounded `/api/health` readiness poll and displays the loading or failure state.
- A launch resolves configured-port conflicts before runtime, dependency, or build work. Conflict records are grouped by PID, show only process name and executable path metadata (never command lines), and are terminated only after one interactive confirmation. Each confirmed PID is targeted once; the resolver re-queries the configured ports without killing replacement listeners and fails closed if a port remains occupied or termination is denied.
- A launch checks backend and frontend dependency fingerprints independently. Successful `uv sync` and `npm ci` operations publish their own generated `.fairs-install-state.json` files; automatic backend recovery does not imply a frontend rebuild.
- Frontend freshness is determined by the SHA-256 content fingerprint of the exact build inputs plus the Node.js baseline. A successful `npm run build` publishes `app/client/dist/.fairs-build-state.json`; state is written only after the build succeeds. Do not use file timestamps, README changes, lint-only configuration, or Vite cache contents as build invalidation signals.
- Browser URL handoff is best-effort after service readiness; a handoff failure must leave the healthy services running and print the configured URL.
- Uvicorn runs with one worker because training jobs and live inference models are process-local.
- `RELOAD=true` is development-only and replaces process-local state.
- Destructive operations require the launcher's explicit interactive confirmation.

## Uninstall Scope

Uninstall removes current runtime, dependency, cache, and build targets only. It does not retain permanent cleanup knowledge for superseded root virtual environments, Angular build directories, or old cache conventions.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/configuration.md` for configuration ownership.
- Read `../runtime/deployment.md` for the supported local distribution boundary.
