## Startup

Last updated: 2026-09-21

## Local Application Startup

From repository root in PowerShell:

```powershell
.\start_on_windows.ps1
```

`start_on_windows.ps1` is the single interactive Windows entry point for launching, dependency setup, frontend rebuilds, database create/upgrade, testing, maintenance, source updates, and uninstall operations.

## Environment Initialization

- If `settings/.env` does not exist, the launcher copies `settings/.env.example` once.
- An existing `.env` is never supplemented with a hidden compatibility/default map.
- Launcher-critical values must be explicitly present in `.env`: `FASTAPI_HOST`, `FASTAPI_PORT`, `UI_HOST`, `UI_PORT`, `RELOAD`, and `EMBEDDED_DATABASE`.
- If one of those values is absent or blank, the launcher fails with an instruction to update `.env` from the current template.

## Runtime Preparation

The launcher prepares or validates:

- portable Python `3.14.7`
- portable `uv`
- Node.js `22.13.0`
- `app/server/.venv`
- frontend dependencies and built `app/client/dist`

`UV_PROJECT_ENVIRONMENT` targets the single server virtual environment. A failed `uv sync` is reported as a failure; the launcher no longer assumes that failure means a legacy environment path and does not delete/recreate the environment as an automatic compatibility retry.

Normal launch resolves conflicts on `FASTAPI_PORT` and `UI_PORT` before runtime, dependency, or build work. When either port is occupied, option 1 lists each unique PID, process name, configured port, and executable path when Windows provides it, then asks once whether those exact processes may be terminated. Declining returns to the menu; a noninteractive launch fails closed without terminating anything. After confirmation, each original PID is targeted at most once, the two ports are re-queried for a bounded period, and any remaining or replacement listener aborts startup without being killed automatically. Maintenance actions retain the strict `Assert-ApplicationStopped` behavior.

The launcher validates each prepared portable runtime once per startup. Backend and frontend dependency readiness are independent: backend state is recorded at `app/server/.venv/.fairs-install-state.json` after a successful `uv sync`, while frontend state is recorded at `app/client/node_modules/.fairs-install-state.json` after a successful `npm ci`. Each state fingerprint covers its lock/project files and the launcher runtime baseline; a lightweight FastAPI/Uvicorn import remains the backend integrity check.

Frontend freshness is content-based rather than timestamp-based. The launcher hashes the exact production build inputs (`index.html`, package manifests, TypeScript configuration, `vite.config.ts`, and regular files under `src` and `public`) with SHA-256, together with the build-state schema and Node.js baseline. A successful build publishes `app/client/dist/.fairs-build-state.json`; missing or malformed state, changed content, a changed Node baseline, or incomplete output triggers a rebuild. The build state is never published after a failed build. README, lint configuration, and arbitrary file timestamps do not invalidate the production bundle under the current Vite configuration.

## Cache Ownership

`runtimes/cache` is the only canonical cache root. Fixed child directories contain runtime, dependency, application, frontend, and test/tool caches. The cache action removes this root and recreates it as needed. The launcher does not discover or clean historical project-local cache names. Obsolete cache directories, if manually left in an old checkout, are outside current ownership and should be removed during repository cleanup.

## Application Lifecycle

- Uvicorn is launched with exactly one worker.
- The built frontend is served through Vite preview in the local launcher flow.
- The launcher starts the backend and frontend preview independently. Startup succeeds for the launcher once the frontend HTTP response and listener are available; the browser then polls `/api/health` while the backend finishes its lifespan startup.
- The frontend shows a dedicated FAIRS loading screen during backend startup, transitions into the normal application after a healthy response, and offers a bounded retry state if the backend does not become ready.
- Opening the frontend in a browser is best-effort after the frontend readiness check. If Windows cannot hand the URL to a browser automatically, the launcher still reports the frontend URL for manual opening.
- Closing the browser does not stop the backend or live inference session.
- Closing the application terminal is the local application stop boundary.
- If the application terminal is unavailable, use launcher option 13, `Stop all app processes`, and confirm the `[y/N]` prompt to terminate the repository-owned backend/frontend process tree.
- `RELOAD=true` is development-only because a reload discards process-local training and inference state.

## Database Behavior

FastAPI lifespan, the CLI, and the launcher use the same Alembic initializer.

- Empty databases upgrade to `head`.
- Known older Alembic revisions upgrade in order.
- Current `head` performs strict metadata validation.
- Non-empty unversioned databases are rejected unchanged.
- Unknown/ahead revisions, multiple heads, and schema drift fail unchanged.
- PostgreSQL and SQLite use the same schema and repositories.

The current database head is `0002_rename_relative_preference`.

Checkpoint format migration is separate from database migration. Before using pre-v1 checkpoint configuration files, run the explicit one-time checkpoint migration preflight described in `../architecture/persistence.md`.

## Destructive Maintenance

Log removal, cache clearing, checkpoint deletion, local data removal, and uninstall require interactive confirmation.

Uninstall removes only current application-owned runtime/dependency/build locations:

- `runtimes`
- `app/server/.venv`
- `app/client/node_modules`
- `app/client/dist`

It does not carry permanent knowledge of obsolete root virtual environments, Angular artifacts, or historical cache paths.

## Source Updates

The update action requires a clean, non-detached `main` checkout and uses `git pull --ff-only origin main`. It does not switch branches, rewrite local changes, or silently merge.

The check-for-updates action compares against the locally known `origin/main` reference and does not fetch.

## Test Startup

From repository root in CMD:

```cmd
app\tests\run_tests.bat
```

From PowerShell:

```powershell
cmd /c app\tests\run_tests.bat
```

## Validation Campaign Baseline

The first campaign tier is recorded in the project status ledger as `VAL-00` and `VAL-01`.

- `VAL-00` records the exact revision, managed runtime, SQLite mode, health response, clean training/inference state, disposable dataset, short real CPU training job, and completed checkpoint identifiers. The checkpoint must be produced through the supported API/launcher path so later inference slices exercise real serialization and dataset lineage.
- `VAL-01` uses the official launcher to verify that the frontend is reachable while backend lifespan startup is still pending, that the browser transitions only after `/api/health` is healthy, and that explicit launcher stop removes only repository-owned backend/frontend processes and leaves ports `8890` and `8051` clear.

When capturing evidence, record browser-visible state, console/network failures, backend logs, process identity, and screenshots for failures. Do not treat a source inspection, a test definition, or a successful response from an unrelated revision as current startup evidence.

## Related Files

- Read `configuration.md` for configuration ownership.
- Read `../architecture/persistence.md` for database and checkpoint migration rules.
- Read `../coding/windows_automation.md` for launcher maintenance conventions.
