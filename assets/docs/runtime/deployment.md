## Deployment

Last updated: 2026-10-22

## Supported Distribution

FAIRS is distributed as source and run locally from its repository through `start_on_windows.ps1`. The repository does not maintain an installer, bundled executable, container image, or packaged desktop release path.

## Local Build Chain

- portable Python `3.14.7`, uv, and Node.js `22.13.0` are prepared under `runtimes/`
- backend dependencies are synchronized into `app/server/.venv`
- frontend dependencies are installed in `app/client/node_modules`
- `npm run build` produces the static frontend bundle; the launcher builds it after dependency installation in option 2, directly through option 3, and during option 1 recovery when the environment or build is stale
- FastAPI serves the built frontend files and API from one origin; production does not run Vite preview
- the launcher supervises one Uvicorn worker, waits up to 60 seconds for `/api/health` to return `ok` or `recovery`, then opens the FastAPI root URL

## Constraints

- Windows is the supported launcher platform.
- No container deployment path is documented or supported in this repository.
- Training workloads remain compute-heavy and depend on the existing worker-process model.
- The launcher is the supported operational boundary for preparing runtimes, starting services, testing, and removing generated dependencies/build output while preserving source and user data.
- The launcher console remains the lifecycle owner. Ctrl+C requests normal Uvicorn/FastAPI shutdown; if graceful shutdown fails, the launcher waits a bounded time and stops only the process tree it started. Keep the configured backend port dedicated to FAIRS.
- `UI_HOST` and `UI_PORT` are development-server settings for manual `npm run dev`; the Vite server proxies `/api` to FastAPI.
- `RELOAD=true` is development-only because reload replaces the process-local training and inference state. Multiple Uvicorn workers are unsupported and rejected.
- Closing the browser does not stop the backend or active inference sessions. Sessions end on capacity eviction or backend shutdown; Ctrl+C in the launcher console is the normal shutdown boundary, and a backend restart intentionally expires live model state.

## Source Release Boundary

- The current source release is `v3.6.1`.
- Releases use annotated `vX.Y.Z` tags from the synchronized `main` branch; GitHub supplies the repository source archives for the tag.
- This repository has no Tauri, MSI, portable executable, installer, or release-artifact workflow. Do not describe a packaged desktop artifact as part of the supported distribution.

## Related Files

- Read `startup.md` for the command entry points.
- Read `../coding/windows_automation.md` for implementation constraints around launcher scripts.
