## Startup

Last updated: 2026-10-22

## Local Application Startup

From repository root in PowerShell:

```powershell
.\start_on_windows.ps1
```

`start_on_windows.ps1` is the single interactive Windows entry point for launching, dependency setup, frontend rebuilds, database create/upgrade, testing, maintenance, source updates, and uninstall operations.

## Environment Initialization

- If `settings/.env` does not exist, the launcher copies `settings/.env.example` once.
- An existing `.env` is never supplemented with a hidden compatibility/default map.
- Launcher-critical values must be explicitly present in `.env`: `FASTAPI_HOST`, `FASTAPI_PORT`, and `RELOAD`. `UI_HOST` and `UI_PORT` configure the manual Vite development server. Database selection and connection details come from `<data-root>/database-config.json`.
- If one of those values is absent or blank, the launcher fails with an instruction to update `.env` from the current template.

## Runtime Preparation

The launcher prepares or validates:

- portable Python `3.14.7`
- portable `uv`
- Node.js `22.13.0`
- `app/server/.venv`
- frontend dependencies and built `app/client/dist`

`UV_PROJECT_ENVIRONMENT` targets the single server virtual environment. Backend dependency installation uses `uv sync --locked` so a stale lockfile fails instead of being rewritten during startup. A failed `uv sync` is reported as a failure; the launcher no longer assumes that failure means a legacy environment path and does not delete/recreate the environment as an automatic compatibility retry.

Production launch checks `FASTAPI_PORT` before runtime, dependency, or build work. If it is occupied, the launcher lists each PID, process name, port, and executable path when Windows provides it, then asks once whether those exact processes may be terminated. Declining returns to the menu; `-Launch` fails closed without terminating unconfirmed processes. After confirmation, the port is re-queried for a bounded period, and any remaining or replacement listener aborts startup. `UI_HOST` and `UI_PORT` are used by the manual development server; maintenance actions still check both configured ports when present.

The launcher validates each prepared portable runtime once per startup. Backend and frontend dependency readiness are independent: backend state is recorded at `app/server/.venv/.fairs-install-state.json` after a successful `uv sync`, while frontend state is recorded at `app/client/node_modules/.fairs-install-state.json` after a successful `npm ci`. Each state fingerprint covers its lock/project files and the launcher runtime baseline; a lightweight FastAPI/Uvicorn import remains the backend integrity check.

Frontend freshness is content-based rather than timestamp-based. The launcher hashes the exact production build inputs (`index.html`, package manifests, TypeScript configuration, `vite.config.ts`, and regular files under `src` and `public`) with SHA-256, together with the build-state schema and Node.js baseline. A successful build publishes `app/client/dist/.fairs-build-state.json`; missing or malformed state, changed content, a changed Node baseline, or incomplete output triggers a rebuild. The build state is never published after a failed build. README, lint configuration, and arbitrary file timestamps do not invalidate the production bundle under the current Vite configuration.

## Cache Ownership

`runtimes/cache` is the only canonical cache root. Fixed child directories contain runtime, dependency, application, frontend, and test/tool caches. The cache action empties this root by removing all child files and folders while preserving only its `.gitkeep` marker, and removes source-tree `__pycache__` directories under `app/server`; later runtime/setup operations recreate cache paths when needed. It does not scan the managed `app/server/.venv` runtime or discover historical project-local cache names. Obsolete cache directories, if manually left in an old checkout, are outside current ownership and should be removed during repository cleanup.

## Application Lifecycle

- The launcher builds `app/client/dist` and starts one Uvicorn worker. FastAPI serves the built HTML, assets, and client-side routes on the same origin as `/api`; Vite preview is not used in production.
- The launcher waits up to 60 seconds for `/api/health` to return `application=FAIRS` with `status=ok` or `status=recovery`, then opens `http://<FASTAPI_HOST>:<FASTAPI_PORT>/`. Wildcard bind addresses open through loopback.
- During launch, `[TIME]` lines report the elapsed milliseconds for environment/port preflight, runtime and dependency setup, frontend build validation, backend startup, readiness, and total time to application readiness. The timings are informational.
- `.\start_on_windows.ps1 -Launch` starts the production app directly and keeps that console open as lifecycle supervisor until the backend stops. The menu's Launch action also waits in the launcher console, then returns to the menu.
- Press Ctrl+C in the launcher console to stop the app through Uvicorn and FastAPI lifespan shutdown. If startup or shutdown fails, the launcher reports the issue and only terminates the backend process tree it started after a bounded wait.
- Closing the browser does not stop the backend or live inference session. If the launcher console is unavailable, use the confirmed `Stop all app processes` maintenance action to clean up orphaned FAIRS backend processes and any older Vite preview process tree.
- `RELOAD=true` is development-only because a reload discards process-local training and inference state.

## Development Frontend

Start the backend and Vite development server manually when using hot reload:

```powershell
.\start_on_windows.ps1
# Choose Install/Check as needed, then in separate terminals:
.\runtimes\nodejs\npm.cmd --prefix app/client run dev
```

The Vite server uses `UI_HOST` and `UI_PORT` and proxies `/api` to the backend configured by `API_BASE_URL` or `FASTAPI_HOST` and `FASTAPI_PORT`.

## Database Behavior

FastAPI lifespan, the CLI, and the launcher use the same Alembic initializer.

- Empty databases upgrade to `head`.
- A fresh database is created at the current `0001_current_schema` baseline. Revisions removed from the migration history are rejected unchanged and require database recreation; known revisions in the current chain still upgrade in order.
- Current `head` performs strict metadata validation.
- Non-empty unversioned databases are rejected unchanged.
- Unknown/ahead revisions, multiple heads, and schema drift fail unchanged.
- PostgreSQL and SQLite use the same schema and repositories.

The current database head is `0001_current_schema`. The Database section in Settings can switch between validated SQLite and PostgreSQL targets while the application is running, provided training and inference are idle. It drains in-flight database requests, reloads Settings from the target database, and leaves each database's data independent. Connection, schema, or activation failures preserve the previous backend. Startup-only changes such as `FAIRS_DATA_DIR` and listener addresses still require a restart.

If the saved database configuration cannot be parsed, decrypted, connected, or initialized, the backend remains available in recovery mode. The frontend opens Database settings, `/api/health` reports `recovery`, and database-backed APIs return `503` until a valid target is applied.

Only current versioned checkpoint configuration files are supported. Unversioned or unsupported checkpoint data is rejected without modification.

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

The ledger records `VAL-00` and `VAL-01` as `PASSED` and `STARTUP-01` as `PASSED` for their recorded revisions. The 2026-10-15 GitHub-hosted Windows run ([run 38750350203](https://github.com/CTCycle/FAIRS-Roulette-Player/actions/runs/38750350203)) covered the official cold Standard installation, runtime/dependency/build artifacts, SQLite migration, prepared read-only `python314._pth` reuse, and launcher backend/frontend HTTP 200 responses. Those historical results do not validate the current database-config and recovery changes. The current `application.startup` component is `PARTIAL` until the updated launcher, recovery mode, readiness, and owned shutdown are exercised on the managed Windows runtime. The original machine's protected cache residue and ACLs remain a separate host-specific limitation.

When capturing evidence, record browser-visible state, console/network failures, backend logs, process identity, and screenshots for failures. Keep runner output transient and record the durable result, tested revision, limitation, and follow-up in the project status ledger. Do not treat a source inspection, a test definition, or a successful response from an unrelated revision as current startup evidence.

## Related Files

- Read `configuration.md` for configuration ownership.
- Read `../architecture/persistence.md` for database and checkpoint migration rules.
- Read `../coding/windows_automation.md` for launcher maintenance conventions.
