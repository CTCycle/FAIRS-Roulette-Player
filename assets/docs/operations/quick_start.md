## Quick Start

Last updated: 2026-08-02

## Fastest Path

1. From repository root in PowerShell, run:

```powershell
.\start_on_windows.ps1
```

2. On first use, allow the launcher to prepare its portable runtimes and install Standard dependencies. Later starts reuse the environment when its readiness checks pass.
3. Open the UI at the configured frontend URL from `UI_HOST:UI_PORT`.
4. Use the top navigation to switch between:
   - `Training`
   - `Inference`

The launcher reports the backend and frontend URLs after both services pass their readiness checks.

## Primary Commands

Start the app:

```powershell
.\start_on_windows.ps1
```

Choose option 2 and then `Development` when browser/test dependencies are required; choose `Standard` for the normal application environment.

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
