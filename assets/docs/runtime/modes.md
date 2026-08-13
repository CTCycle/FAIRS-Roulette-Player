## Runtime Modes

Last updated: 2026-08-13

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
- API docs and OpenAPI routes are enabled by default through `ENABLE_API_DOCS=true`.

### Unsupported Packaging Modes

- Container deployment is not implemented; the repository has no Dockerfile or supported container startup pipeline.
- The backend recognizes `FAIRS_TAURI_MODE` for a desktop-mode health label and a built-frontend guard, but this checkout contains no Tauri packaging or supported desktop distribution.

## Cross-Mode Differences

- Local mode launches browser-based access on the configured UI host and port.
- Embedded and external database behavior differ by environment configuration.
- A built frontend is served by the backend when available in `app/client/dist`; otherwise the backend root redirects to API docs when docs are enabled.

## Related Files

- Read `startup.md` for the command paths into each mode.
- Read `configuration.md` for the environment variables that switch behavior.
