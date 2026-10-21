## Runtime Modes

Last updated: 2026-10-21

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
- The supported runtime is a single backend worker plus one frontend preview process. Training jobs and live inference models are intentionally process-local.
- Browser lifetime is independent of service lifetime. Closing a tab leaves the backend and live session state running until an explicit API stop, capacity eviction, or backend shutdown.

### Unsupported Packaging Modes

- Container deployment is not implemented; the repository has no Dockerfile or supported container startup pipeline.
- Tauri, desktop installers, containers, and other packaged distribution modes are not implemented or supported by this checkout.

## Cross-Mode Differences

- Local mode launches browser-based access on the configured UI host and port.
- SQLite and PostgreSQL are selected in Settings and saved in `<data-root>/database-config.json`; database selection is not environment configuration. Live switching is supported when training and inference are idle.
- A built frontend is served by the backend when available in `app/client/dist`; otherwise the backend root redirects to API docs when docs are enabled.
- `RELOAD=true` may be used for development only; reloads discard process-local jobs and live sessions. Multi-worker Uvicorn execution is unsupported.

## Related Files

- Read `startup.md` for the command paths into each mode.
- Read `configuration.md` for environment and database configuration ownership.
