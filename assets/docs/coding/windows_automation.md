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

`runtimes/cache` is the only cache root owned by current automation. Fixed child directories hold uv, npm, pip, Python bytecode, pytest, pytest basetemp, Ruff, mypy, coverage, Playwright, Vite, TypeScript, Keras, Torch, Triton, Matplotlib, XDG, and CUDA cache data. Clear Cache removes all child files and folders under this root, preserves only its `.gitkeep` marker, and also removes source-tree `__pycache__` directories under `app/server`, while leaving the managed `app/server/.venv` runtime untouched. Do not recursively discover or create other cache directories elsewhere in the repository.

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

Uninstall removes current runtime, dependency, cache, and build targets only. It does not retain permanent cleanup knowledge for superseded root virtual environments, Angular build directories, or old cache conventions.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/configuration.md` for configuration ownership.
- Read `../runtime/deployment.md` for the supported local distribution boundary.
