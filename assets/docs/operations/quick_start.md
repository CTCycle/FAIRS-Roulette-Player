## Quick Start

Last updated: 2026-10-21

## Fastest Path

1. From repository root in PowerShell, run:

```powershell
.\start_on_windows.ps1
```

2. On first use, allow the launcher to prepare its portable runtimes, install Standard dependencies, and build the frontend. Later starts check the backend port, reuse current dependency state independently, and rebuild only when the content-based frontend build state is missing, invalid, or stale. FastAPI validates and upgrades the database through Alembic during lifespan.
3. The launcher waits for `/api/health` to report `ok` or `recovery`, then opens the FastAPI URL at `http://FASTAPI_HOST:FASTAPI_PORT/` (wildcard binds open through loopback).
4. Use the top navigation to switch between:
   - `Training`
   - `Inference`

FastAPI serves the built frontend and `/api` from the same origin; production does not use Vite preview. The launcher console remains open and supervises the backend after the browser opens. Closing the browser leaves the app running. Press Ctrl+C in the launcher console to stop through FastAPI's normal shutdown path. If automatic browser opening fails, use the printed application URL.

## Primary Commands

Start the app:

```powershell
.\start_on_windows.ps1
```

Choose option 2 and then `Development` when browser/test dependencies are required; choose `Standard` for the normal application environment. To launch without the menu, run `.\start_on_windows.ps1 -Launch`; that console exits after the backend stops.

Use option 4 to run the database create/upgrade workflow directly. Option 2 explicitly synchronizes both dependency layers and rebuilds the frontend; option 3 explicitly rebuilds the frontend without automatic dependency synchronization. Stop the app with Ctrl+C in its launcher console before maintenance or cleanup.

Use option 7 to pull application changes from `main`. Use option 6 to check the locally known `origin/main` status without fetching or applying updates. Options 8 through 12 are destructive cleanup actions and require an affirmative response at a `[y/N]` prompt; option 10 removes checkpoints separately, while option 11 removes local database and log data while preserving checkpoints and configuration. Option 12 offers standard uninstall or complete removal; complete removal displays its exact targets and asks for a separate `REMOVE` confirmation before deleting persistent local data.

For read-only cleanup previews from any working directory, run `start_on_windows.ps1 -Action Cache -WhatIf`, `-Action Uninstall -WhatIf`, or `start_on_windows.ps1 -Action Uninstall -CompleteRemoval -WhatIf`.

Use option 13, `Stop all app processes`, when the launcher console is unavailable. It requires confirmation and stops detected FAIRS backend or older Vite preview process trees without closing the browser.

Run the automated test entry point:

```cmd
app\tests\run_tests.bat
```

Open maintenance tools:

```powershell
.\start_on_windows.ps1
```

## Orientation

- Use the launcher for local production-style serving. Start Vite with `npm run dev` for frontend hot reload; `UI_HOST` and `UI_PORT` apply to Vite, which proxies `/api` to FastAPI.
- Keep `settings` and environment configuration aligned with the local runtime.

## Related Files

- Read `workflows.md` for end-user task sequences.
- Read `../runtime/startup.md` for PowerShell and CMD launch details.
