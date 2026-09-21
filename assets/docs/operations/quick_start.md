## Quick Start

Last updated: 2026-09-21

## Fastest Path

1. From repository root in PowerShell, run:

```powershell
.\start_on_windows.ps1
```

2. On first use, allow the launcher to prepare its portable runtimes, install Standard dependencies, and run the idempotent database create/upgrade step. Later starts check the configured backend and frontend ports first, reuse current dependency state independently, and rebuild only when the content-based frontend build state is missing, invalid, or stale. FastAPI still validates the database through Alembic during lifespan.
3. Open the UI at the configured frontend URL from `UI_HOST:UI_PORT`.
4. Use the top navigation to switch between:
   - `Training`
   - `Inference`

The launcher always keeps the backend in a visible PowerShell terminal, starts the frontend preview without waiting for backend health, and reports the configured URLs once the frontend is available. If option 1 finds a listener on either configured port, it shows the exact process records and asks whether to terminate them; answering `No` leaves every process running and returns to the menu. The browser shows FAIRS startup progress until the backend is healthy. If Windows cannot open the browser automatically, open the printed frontend URL manually.

## Primary Commands

Start the app:

```powershell
.\start_on_windows.ps1
```

Choose option 2 and then `Development` when browser/test dependencies are required; choose `Standard` for the normal application environment.

Use option 4 to run the database create/upgrade workflow directly. Option 2 explicitly synchronizes both dependency layers and rebuilds the frontend; option 3 explicitly rebuilds the frontend without automatic dependency synchronization. Close the application terminal to stop the local application before maintenance or cleanup.

Use option 7 to pull application changes from `main`. Use option 6 to check the locally known `origin/main` status without fetching or applying updates. Options 8 through 12 are destructive cleanup actions and require an affirmative response at a `[y/N]` prompt; option 10 removes checkpoints separately, while option 11 removes local database and log data while preserving checkpoints.

Use option 13, `Stop all app processes`, when the application terminal is unavailable. It requires confirmation and stops the repository-owned backend, frontend, and child processes without closing the browser.

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
