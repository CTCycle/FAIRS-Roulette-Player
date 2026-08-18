## Windows Automation

Last updated: 2026-08-19

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
- The launcher clears its configured FastAPI and UI ports before starting services and clears the configured UI port before replacing frontend dependencies.
- Any changes to runtime staging should be reflected in both the scripts and the runtime documentation.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/deployment.md` for the local build chain and supported distribution boundary.
