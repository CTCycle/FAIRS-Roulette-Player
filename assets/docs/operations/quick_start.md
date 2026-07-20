## Quick Start

Last updated: 2026-07-20

## Fastest Path

1. From repository root, run:

```powershell
.\start_on_windows.ps1
```

2. Open the UI at the configured frontend URL from `UI_HOST:UI_PORT`.
3. Use the top navigation to switch between:
   - `Training`
   - `Inference`

The launcher reports the backend and frontend URLs after both services pass their readiness checks.

## Primary Commands

Start the app:

```powershell
.\start_on_windows.ps1
```

Run the automated test entry point:

```cmd
app\tests\run_tests.bat
```

Open maintenance tools:

```powershell
.\start_on_windows.ps1
```

## Orientation

- Use local web mode for normal development and experimentation.
- Keep `settings` and environment configuration aligned with the local runtime.

## Related Files

- Read `workflows.md` for end-user task sequences.
- Read `../runtime/startup.md` for PowerShell and CMD launch details.
