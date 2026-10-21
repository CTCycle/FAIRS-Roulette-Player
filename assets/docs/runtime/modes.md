## Runtime Modes

Last updated: 2026-10-21

## Supported Modes

### Local Web Runtime

- Backend:
  - FastAPI via `uvicorn`
- Frontend:
  - built React/Vite SPA served by FastAPI from `app/client/dist`
- Startup orchestrator:
  - `start_on_windows.ps1`
- Intended use:
  - local production-style use and experimentation
- API docs and OpenAPI routes are enabled by default through `ENABLE_API_DOCS=true`.
- The production runtime is one backend worker. Frontend files and `/api` share the FastAPI origin, so the browser needs no separate production frontend server.
- Browser lifetime is independent of service lifetime. Closing a tab leaves the backend and live session state running until an explicit API stop, capacity eviction, or backend shutdown.

### Frontend Development

- Run Vite with `npm run dev` for hot reload; `UI_HOST` and `UI_PORT` apply to that workflow.
- Vite proxies `/api` to `API_BASE_URL` or the configured FastAPI host and port.
- `npm run preview` is reserved for frontend preview and test workflows, not production serving.

### Unsupported Packaging Modes

- Container deployment is not implemented; the repository has no Dockerfile or supported container startup pipeline.
- Tauri, desktop installers, containers, and other packaged distribution modes are not implemented or supported by this checkout.

## Cross-Mode Differences

- Production launcher mode opens the configured FastAPI URL after `/api/health` reports `ok` or `recovery`; a wildcard bind opens through loopback.
- `start_on_windows.ps1 -Launch` stays open as lifecycle supervisor. Ctrl+C in that console requests normal Uvicorn/FastAPI shutdown; closing the browser does not stop the app.
- SQLite and PostgreSQL are selected in Settings and saved in `<data-root>/database-config.json`; database selection is not environment configuration. Live switching is supported when training and inference are idle.
- A built frontend is served by the backend when available in `app/client/dist`; otherwise the backend root redirects to API docs when docs are enabled. Unknown `/api/*` routes remain API 404 responses instead of falling through to the SPA.
- `RELOAD=true` may be used for development only; reloads discard process-local jobs and live sessions. Multi-worker Uvicorn execution is unsupported.

## Related Files

- Read `startup.md` for the command paths into each mode.
- Read `configuration.md` for environment and database configuration ownership.
