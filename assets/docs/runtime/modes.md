## Runtime Modes

Last updated: 2026-06-02

## Supported Modes

### Local Web Runtime

- Backend:
  - FastAPI via `uvicorn`
- Frontend:
  - Vite development server
- Startup orchestrator:
  - `start_on_windows.ps1`
- Intended use:
  - day-to-day development and experimentation

### Desktop Runtime

- Shell:
  - Tauri app in `app/src-tauri`
- Backend:
  - local `uvicorn` process spawned by `src-tauri/src/main.rs`
- Build and packaging orchestrator:
  - `release/tauri/build_with_tauri.bat`
- Intended use:
  - packaged Windows desktop distribution

### Container Runtime

- Not implemented in the current repository.
- No Dockerfile or supported container startup pipeline is part of the documented runtime surface.

## Cross-Mode Differences

- Local mode launches browser-based access on the configured UI host and port.
- Desktop mode launches only the Tauri window and targets the backend root URL once ready.
- Desktop mode fails fast if Tauri is enabled but the built frontend is missing.
- Embedded and external database behavior differ by environment configuration, not by UI surface.

## Related Files

- Read `startup.md` for the command paths into each mode.
- Read `configuration.md` for the environment variables that switch behavior.
