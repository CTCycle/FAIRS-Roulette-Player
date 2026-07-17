## Windows Automation

Last updated: 2026-07-11

## Scope

This file covers repository-specific conventions for the PowerShell launcher and Windows automation.

## PowerShell Rules

- Preserve Windows-first behavior in PowerShell automation.
- Keep startup and maintenance flows consolidated in `start_on_windows.ps1`.
- Inline all launcher logic in `start_on_windows.ps1`.
- Do not introduce parallel bootstrap paths unless the task explicitly requires them.

## Runtime Layout Expectations

- Python, uv, and Node runtime preparation is coordinated by the Windows launcher.
- Local launch relies on a prepared virtual environment and a built frontend.
- Any changes to runtime staging should be reflected in both the scripts and the runtime documentation.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/deployment.md` for the local build chain and supported distribution boundary.
