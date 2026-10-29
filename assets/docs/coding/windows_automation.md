## Windows Automation

Last updated: 2026-10-22

## Scope

This file defines repository-specific rules for the PowerShell launcher and Windows automation.

## PowerShell Rules

- Keep startup and maintenance flows consolidated in `start_on_windows.ps1`.
- Do not introduce parallel bootstrap or compatibility paths unless a current requirement is demonstrated.
- `Standard` installation syncs runtime dependencies. `Development` additionally installs the server test extra and Playwright Chromium below `runtimes/cache/playwright-browsers`.
- `settings/.env.example` is the canonical launcher environment template. The launcher may create a missing `.env` from it once, but must not supply a separate hardcoded defaults map for stale existing files.
- Existing `.env` files missing launcher-critical keys (`FASTAPI_HOST`, `FASTAPI_PORT`, or `RELOAD`) must fail clearly rather than inherit obsolete behavior. `UI_HOST` and `UI_PORT` belong to the manual Vite development workflow.

- On Windows PowerShell 5.1 the launcher drops inherited PowerShell 7 `PSModulePath` entries at startup. Without this, `powershell -File start_on_windows.ps1` from a PowerShell 7 session cannot resolve built-in cmdlets such as `Get-FileHash` and fails during dependency fingerprinting.
- Production launch prints aligned `[TIME]` durations in milliseconds for its startup phases and total time to application readiness. These timings are informational and do not affect setup or launch decisions.

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

`runtimes/cache` remains the canonical location for launcher-managed uv, npm, pip, Python, pytest, Ruff, mypy, coverage, Playwright, Vite, TypeScript, Keras, Torch, Triton, Matplotlib, XDG, and CUDA caches. Clear Cache empties its contents while preserving `.gitkeep`, then discovers recognized cache directories and Python bytecode throughout `app/server` (including `.venv`), `app/client` (including `node_modules`), and `app/tests`. Recognized generated paths include `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, nested `.cache` and Vite caches, `htmlcov`, `*.pyc`, `*.pyo`, `.coverage*`, and `*.tsbuildinfo`. It removes known frontend/backend build output, Playwright traces/JUnit and named viewport/VAL screenshots under `assets/QA`, interrupted checkpoint staging files, and exact launcher temporary-file patterns. It preserves installed packages, valid checkpoints, databases, logs, settings, and unknown files. New cache types should be added only when a dependency in the current stack creates them.

## Lifecycle Rules

- Maintenance, database, testing, update, uninstall, and data-removal actions require the application to be stopped from its launcher console.
- The launcher console owns the local process lifecycle; closing the browser does not stop the app. Both menu Launch and `start_on_windows.ps1 -Launch` supervise Uvicorn until it exits. The direct `-Launch` mode then exits; menu Launch returns to the menu.
- Production serves `app/client/dist` through FastAPI on the API origin. Launch waits up to 60 seconds for `/api/health` to return `application=FAIRS` with `ok` or `recovery`, then opens the FastAPI root URL. It does not start Vite preview.
- Ctrl+C in the launcher console is the normal shutdown path and allows Uvicorn/FastAPI lifespan cleanup. On startup failure or incomplete shutdown, wait for a bounded period and terminate only the backend process tree created by that launch.
- Unexpected backend-parent exit also triggers descendant inspection and cleanup; never kill processes outside the launcher-owned tree. Run the Windows PowerShell maintenance harness in CI and verify interactive Ctrl+C locally.
- The confirmed `Stop all app processes` action is for orphaned FAIRS backends, older Vite preview processes, and their descendants; it does not target browser or unrelated repository processes.
- Production checks only `FASTAPI_PORT` before build/start. Port conflict records are grouped by PID, show process name and executable path metadata (never command lines), and are terminated only after one interactive confirmation. Each confirmed PID is targeted once; the resolver re-queries the port without killing replacement listeners and fails closed if a listener remains or termination is denied.
- Vite `npm run dev` is a manual development workflow using `UI_HOST` and `UI_PORT`; its `/api` proxy points to the configured FastAPI host/port. `npm run preview` remains for preview/test use only.
- A launch checks backend and frontend dependency fingerprints independently. Successful `uv sync` and `npm ci` operations publish their own generated `.fairs-install-state.json` files; automatic backend recovery does not imply a frontend rebuild.
- Frontend freshness is determined by the SHA-256 content fingerprint of the exact build inputs plus the Node.js baseline. A successful `npm run build` publishes `app/client/dist/.fairs-build-state.json`; state is written only after the build succeeds. Do not use file timestamps, README changes, lint-only configuration, or Vite cache contents as build invalidation signals.
- Browser URL handoff is best-effort after service readiness; a handoff failure must leave the healthy services running and print the configured URL.
- Uvicorn runs with one worker because training jobs and live inference models are process-local.
- `RELOAD=true` is development-only and replaces process-local state.
- Destructive operations require the launcher's explicit interactive confirmation.

## Uninstall Scope

Standard uninstall removes the known launcher runtime directories (`runtimes/python`, `runtimes/uv`, and `runtimes/nodejs`), the disposable runtime-cache contents, `app/server/.venv`, `app/client/node_modules`, frontend/backend build output, recognized caches and temporary artifacts, Playwright reports, and application `.log` files. Runtime/cache markers and unknown runtime siblings are kept. The local database, checkpoints, `database-config.json`, `settings/.env`, and other unknown data-root files remain.

The Uninstall menu offers Complete removal after displaying the exact targets. It first confirms generated-file removal, then requires typing `REMOVE` before deleting the configured local SQLite database and sidecars, checkpoint contents, application logs, `database-config.json`, and `settings/.env`. A malformed or unsafe database configuration stops complete removal before any deletion. A PostgreSQL server is never modified. Unknown data-root files and browser-managed `localStorage` remain; the launcher has no application-specific AppData filesystem targets.

Menu cleanup actions print a target preview and a cleaned/skipped/failed summary. Read-only previews can also be run from any working directory:

```powershell
.\start_on_windows.ps1 -Action Cache -WhatIf
.\start_on_windows.ps1 -Action Uninstall -WhatIf
.\start_on_windows.ps1 -Action Uninstall -CompleteRemoval -WhatIf
```

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/configuration.md` for configuration ownership.
- Read `../runtime/deployment.md` for the supported local distribution boundary.
