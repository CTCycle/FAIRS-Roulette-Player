## Windows Automation

Last updated: 2026-06-23

## Scope

This file covers repository-specific conventions for Tauri, Rust, batch launchers, and PowerShell automation.

## Batch And PowerShell Rules

- Preserve Windows-first behavior in `.bat` and PowerShell automation.
- Keep startup and maintenance flows aligned with:
  - `start_on_windows.bat`
  - `setup_and_maintenance.bat`
  - `release/tauri/build_with_tauri.bat`
- Do not introduce parallel bootstrap paths unless the task explicitly requires them.

## Tauri And Rust Rules

- Keep desktop startup behavior aligned with the Tauri shell in `app/src-tauri`.
- Preserve the runtime expectations around local backend spawning, environment propagation, and built frontend availability.
- Treat `FAIRS_TAURI_MODE` as a real runtime contract, not a cosmetic flag.
- Keep packaging logic aligned with the current release helper scripts.
- Cleanup automation may remove generated Tauri outputs, but it must never delete the `app/src-tauri` source/config tree.

## Runtime Layout Expectations

- Python and Node runtime preparation is coordinated by the existing Windows launchers.
- Desktop launch logic relies on a prepared virtual environment and a built frontend when packaged.
- Any changes to runtime staging should be reflected in both the scripts and the runtime documentation.

## Related Files

- Read `../runtime/startup.md` for launcher usage.
- Read `../runtime/deployment.md` for packaging outputs and build chain notes.
