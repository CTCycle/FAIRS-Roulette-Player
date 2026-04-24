# RUNTIME_MODES

Last updated: 2026-04-24

This document reflects only runtime modes and execution paths currently implemented in the repository.

## Supported Modes

### 1. Local Web Runtime (default)

- Backend: FastAPI via `uvicorn`.
- Frontend: Vite preview server.
- Startup orchestrator: `FAIRS/start_on_windows.bat`.
- Intended use: day-to-day development and experimentation.

### 2. Desktop Runtime (Tauri, Windows)

- Shell: Tauri app (`FAIRS/client/src-tauri`).
- Backend: local `uvicorn` process spawned by `src-tauri/src/main.rs`.
- Build/packaging orchestrator: `release/tauri/build_with_tauri.bat`.
- Intended use: packaged distribution for Windows desktop.

### 3. Maintenance Runtime (operations menu)

- Script: `FAIRS/setup_and_maintenance.bat`.
- Supports database initialization, log cleanup, desktop build cleanup, and runtime uninstall.

### 4. Containerized Runtime

- Not currently implemented.
- No Dockerfile or container startup pipeline is defined in the current repository.

## Startup Procedures

### Local Web Runtime

From repository root (CMD):

```cmd
FAIRS\start_on_windows.bat
```

From repository root (PowerShell):

```powershell
cmd /c FAIRS\start_on_windows.bat
```

What the launcher does:
- Installs/validates portable Python, uv, and Node in `runtimes/`.
- Syncs Python dependencies via `uv sync`.
- Installs frontend dependencies and builds frontend if missing.
- Starts backend (`uvicorn FAIRS.server.app:app`) and frontend (`vite preview`).

### Desktop Runtime Build

From repository root (CMD):

```cmd
release\tauri\build_with_tauri.bat
```

From repository root (PowerShell):

```powershell
cmd /c release\tauri\build_with_tauri.bat
```

Prerequisites:
- Rust/Cargo installed and usable.
- Portable runtimes already prepared (run `FAIRS\start_on_windows.bat` at least once).

### Maintenance Runtime

From repository root:

```cmd
FAIRS\setup_and_maintenance.bat
```

Menu options:
- Initialize database
- Remove logs
- Clean desktop build artifacts
- Uninstall runtime-local artifacts

## Environment Variables and Configuration

### `.env` keys used by runtime scripts and app

- `FASTAPI_HOST`
- `FASTAPI_PORT`
- `UI_HOST`
- `UI_PORT`
- `ENABLE_API_DOCS`
- `RELOAD`
- `OPTIONAL_DEPENDENCIES`
- `MPLBACKEND`
- `KERAS_BACKEND`

### Internal/runtime flags

- `FAIRS_TAURI_MODE=true` is injected by the desktop runtime backend launcher.
- `UV_PROJECT_ENVIRONMENT` is set by launch/build scripts to target runtime `.venv` locations.

### Technical backend settings

`FAIRS/settings/configurations.json` controls:
- `database` (embedded SQLite vs PostgreSQL settings)
- `jobs.polling_interval`
- `device` options (JIT/mixed precision defaults)

## Configuration Differences

### Local vs desktop

- Local script launches frontend preview and opens browser URL from `UI_HOST:UI_PORT`.
- Desktop runtime launches only the Tauri window and routes it to backend root (`http://<FASTAPI_HOST>:<FASTAPI_PORT>/`) once ready.
- Desktop runtime may place writable runtime state in a per-user app data directory when workspace root is not writable.

### API docs exposure

- Controlled by `ENABLE_API_DOCS`.
- If disabled, `/docs`, `/redoc`, and OpenAPI routes are not mounted.

### Database behavior

- If `embedded_database=true`, SQLite auto-initializes on startup only when `FAIRS/resources/database.db` is missing.
- If `embedded_database=false`, PostgreSQL initialization is manual via maintenance script (`Initialize database`).

## Interoperability

- Frontend always communicates with backend through `/api/*`.
- Vite dev/preview proxies `/api` to backend host/port from `.env`.
- In desktop mode, FastAPI can serve packaged SPA assets from `FAIRS/client/dist` when `FAIRS_TAURI_MODE=true`.
- Training and inference share persisted datasets/checkpoints through shared backend services and repositories.

## Limitations and Constraints

- Desktop packaged runtime is Windows-focused in current implementation.
- No Linux/macOS desktop packaging workflow is maintained here.
- No container runtime path is defined.
- Training is compute-heavy and uses a worker process; it is not suitable for request-thread execution.
- Backend concurrency model is primarily synchronous API handlers plus job threads/processes (not async DB).

## Deployment Notes

### Desktop packaging outputs

`release/tauri/build_with_tauri.bat` exports Windows artifacts under:
- `release/windows/installers`
- `release/windows/portable`

### Build chain

- Frontend build: `npm run build` (inside `FAIRS/client`).
- Tauri release build/export: `npm run tauri:build:release` via packaging helper script.
- Runtime payloads bundled include backend source, frontend dist, settings, resources, and portable runtimes as configured in `tauri.conf.json`.
