## Runtime Modes

Last updated: 2026-07-20

## Supported Modes

### Local Web Runtime

- Backend:
  - FastAPI via `uvicorn`
- Frontend:
  - Vite preview server for the built frontend
- Startup orchestrator:
  - `start_on_windows.ps1`
- Intended use:
  - day-to-day development and experimentation

### Container Runtime

- Not implemented in the current repository.
- No Dockerfile or supported container startup pipeline is part of the documented runtime surface.

## Cross-Mode Differences

- Local mode launches browser-based access on the configured UI host and port.
- Embedded and external database behavior differ by environment configuration.

## Related Files

- Read `startup.md` for the command paths into each mode.
- Read `configuration.md` for the environment variables that switch behavior.
