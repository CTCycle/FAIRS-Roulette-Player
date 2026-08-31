## Quick Start

Last updated: 2026-08-21

## Fastest Path

1. From repository root in PowerShell, run:

```powershell
.\start_on_windows.ps1
```

2. On first use, allow the launcher to prepare its portable runtimes, install Standard dependencies, and run the idempotent database create/upgrade step. Later starts reuse the environment when its readiness checks pass and still validate the database through Alembic during FastAPI lifespan.
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

Choose option 4 and then `Development` when browser/test dependencies are required; choose `Standard` for the normal application environment.

Use option 6 to run the database create/upgrade workflow directly. Use option 5 only when the frontend needs rebuilding and dependencies/database state should not be touched.

Use option 2 to pull application changes from `main`. Use option 3 to check the locally known `origin/main` status without fetching or applying updates. Options 8 through 12 are destructive cleanup actions and require an affirmative response at a `[y/N]` prompt; option 10 removes checkpoints separately, while option 11 removes local database and log data while preserving checkpoints.

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
