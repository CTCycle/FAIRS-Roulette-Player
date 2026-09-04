## Windows Automation

Last updated: 2026-09-03

## Scope

This file covers repository-specific conventions for the PowerShell launcher and Windows automation.

## PowerShell Rules

- Preserve Windows-first behavior in PowerShell automation.
- Keep startup and maintenance flows consolidated in `start_on_windows.ps1`.
- Inline all launcher logic in `start_on_windows.ps1`.
- Do not introduce parallel bootstrap paths unless the task explicitly requires them.
- Keep installation mode explicit: `Standard` syncs runtime dependencies, while `Development` adds the server's `test` extra.

## Runtime Layout Expectations

- Python, uv, and Node runtime preparation is coordinated by the Windows launcher.
- The current launcher baseline is portable Python `3.14.2`, Node.js `22.13.0`, and a portable `uv` executable.
- Local launch relies on a prepared virtual environment and a built frontend.
- Startup checks the runtime executables, the backend environment, the Vite runner, and the built frontend before deciding whether dependency installation or rebuild is needed.
- The launcher requires the application terminal to be closed before maintenance, database, testing, update, uninstall, or data-removal actions. Keep the configured backend and UI ports dedicated to this application.
- There is no separate application stop action. Closing the application terminal is the local stop signal; closing the browser is not.
- Startup is complete only after backend health and frontend HTTP checks succeed. If either service fails readiness, close the application terminal before retrying.
- Uvicorn is always launched with one worker. `RELOAD=true` is development-only because reloads discard process-local state.
- Cache and data cleanup is best-effort and reproducible: it inventories each target recursively, excludes required sentinels, deletes individual entries deepest-first in stable normalized-path order, and reports locked or protected paths as skipped. Required roots are recreated after cleanup.
- Any changes to runtime staging should be reflected in both the scripts and the runtime documentation.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/deployment.md` for the local build chain and supported distribution boundary.
