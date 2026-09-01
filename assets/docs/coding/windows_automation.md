## Windows Automation

Last updated: 2026-09-01

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
- The launcher requires the application to be stopped before maintenance, database, testing, update, uninstall, or data-removal actions. It discovers configured-port listeners and refuses to kill a process unless it was started by the launcher or its command line demonstrably belongs to this repository.
- Option 2 is the explicit application stop action. Closing the browser is not a stop signal.
- Startup is complete only after backend health and frontend HTTP checks succeed. If either service fails readiness, all processes started by that launch attempt are cleaned up.
- Uvicorn is always launched with one worker. `RELOAD=true` is development-only because reloads discard process-local state.
- Cache cleanup is best-effort and reproducible: it attempts one recursive bulk removal per target, then uses a single deepest-first, normalized-path snapshot for item-level recovery only when the bulk operation fails. Locked or protected paths are reported and skipped.
- Any changes to runtime staging should be reflected in both the scripts and the runtime documentation.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/deployment.md` for the local build chain and supported distribution boundary.
