## Deployment

Last updated: 2026-09-03

## Supported Distribution

FAIRS is distributed as source and run locally from its repository through `start_on_windows.ps1`. The repository does not maintain an installer, bundled executable, container image, or packaged desktop release path.

## Local Build Chain

- portable Python `3.14.2`, uv, and Node.js `22.13.0` are prepared under `runtimes/`
- backend dependencies are synchronized into `app/server/.venv`
- frontend dependencies are installed in `app/client/node_modules`
- `npm run build` produces the frontend used by `npm run preview`; the launcher invokes this after dependency installation in option 2, directly through option 3, and during option 1 recovery when the environment or build is unusable
- the backend is launched as one Uvicorn worker and the frontend as a separate Vite preview process
- the launcher reports startup complete only after the backend health endpoint and frontend HTTP endpoint both succeed

## Constraints

- Windows is the supported launcher platform.
- No container deployment path is documented or supported in this repository.
- Training workloads remain compute-heavy and depend on the existing worker-process model.
- The launcher is the supported operational boundary for preparing runtimes, starting services, testing, and removing generated dependencies/build output while preserving source and user data.
- The launcher starts the backend in a dedicated visible PowerShell application terminal by default; closing that terminal is the local stop action. Keep the configured backend and UI ports dedicated to FAIRS.
- `RELOAD=true` is development-only because reload replaces the process-local training and inference state. Multiple Uvicorn workers are unsupported and rejected.
- Closing the browser does not stop the backend or active inference sessions. Sessions end on capacity eviction or backend shutdown; closing the application terminal is the local shutdown boundary, and a backend restart intentionally expires live model state.

## Source Release Boundary

- The current source release is `v3.1.0`.
- Releases use annotated `vX.Y.Z` tags from the synchronized `main` branch; GitHub supplies the repository source archives for the tag.
- This repository has no Tauri, MSI, portable executable, installer, or release-artifact workflow. Do not describe a packaged desktop artifact as part of the supported distribution.

## Related Files

- Read `startup.md` for the command entry points.
- Read `../coding/windows_automation.md` for implementation constraints around launcher scripts.
