## Troubleshooting

Last updated: 2026-09-21

## Startup Problems

- If local startup fails, run option 2 in `start_on_windows.ps1` and choose `Standard` to resync runtimes and application dependencies.
- If test or browser tooling is missing, run option 2 and choose `Development` so the server's `test` extra is installed.
- If option 1 reports a listener on a configured port, review the displayed PID, process name, port, and executable path. Answer `Yes` only when you intend to terminate every listed PID; the launcher deduplicates a PID that owns both ports, waits for both ports to clear, and never kills a replacement listener automatically. Answer `No` to leave all processes untouched and return to the menu. Noninteractive launches fail closed when a conflict exists. Option 13 remains the separate FAIRS-owned process cleanup action.
- If the backend starts without the frontend, verify that `app/client/node_modules` contains Vite and that `app/client/dist/index.html` and its generated assets exist; close the application terminal before retrying option 1, run option 3 for a frontend-only rebuild, or run option 2 when frontend dependencies also need updating.
- If option 1 resynchronizes only backend dependencies after a `pyproject.toml` or `uv.lock` change, that is expected; backend recovery does not rebuild the frontend. A missing or corrupt `app/server/.venv/.fairs-install-state.json`, `app/client/node_modules/.fairs-install-state.json`, or `app/client/dist/.fairs-build-state.json` causes the relevant layer to recover on the next launch.
- Frontend rebuild decisions use content fingerprints, not file timestamps. Changes to React/TypeScript/CSS source, public assets, package manifests, TypeScript configuration, or `vite.config.ts` rebuild the frontend; README and lint-only configuration changes do not.
- Maintenance actions require the application terminal to be closed first. If npm reports `EPERM` for `esbuild.exe`, stop any external Vite or Node process using `app/client/node_modules` through its own owner and retry.
- If the browser remains on the FAIRS startup screen, keep the visible backend terminal open and inspect its startup output. The screen retries transient connection failures and changes to a compact retry state after its bounded startup window; use `Retry connection` after correcting the backend issue.
- If startup reports an unsupported worker count, unset `WEB_CONCURRENCY`, `UVICORN_WORKERS`, and `FAIRS_WORKERS`, or set each to `1`. Do not use multiple workers for this process-local runtime.
- If the frontend preview itself does not become ready, close the application terminal before retrying. Check whether the configured UI port is owned by an unrelated process and verify that `app/client/dist` is complete. If the preview starts but no browser opens, use the frontend URL printed by the launcher.

## API Docs Problems

- If `/docs` is unavailable, check `ENABLE_API_DOCS`.
- If the backend root does not show docs when no frontend build exists, verify docs were not explicitly disabled.

## Test Problems

- If browser-dependent tests fail to start correctly, choose `Development` in the launcher's install/update option and rerun the test setup flow.
- Prefer starting with the smallest failing test slice before rerunning the full test suite.

## Configuration Problems

- If saving JIT settings reports that `torch.compile` is unavailable, reinstall the launcher-managed Python 3.14 runtime so the locked PyTorch build is present, or disable JIT. On Windows, select the `eager` backend because `inductor` requires Triton. The application intentionally fails closed instead of silently using a different execution mode.
- If saving JIT settings reports that the `inductor` backend requires Triton, select `eager` on Windows. The Windows-supported runtime does not silently substitute a different compiler backend.
- If database startup enters recovery, open Settings → Database, review the redacted configuration/status message, test a corrected target, then apply it. Health reports `recovery` and database-backed APIs return `503` until a target is active.
- If PostgreSQL connection testing fails, check the host, port, database name, username, password, SSL requirement, and optional CA certificate path in Settings → Database. Only the `postgresql+psycopg` driver is supported.
- Applying a PostgreSQL target runs the normal Alembic initializer. A missing database is created only for SQLSTATE `3D000`, and the configured role needs `CREATEDB`; otherwise create the database through your normal PostgreSQL administration workflow.
- Each configured database owns separate settings and application data. Switching does not copy either. Switching is rejected during active training or inference; stop training and close inference sessions before retrying.
- Connection configuration is stored in `<data-root>/database-config.json`. On Windows, saved PostgreSQL passwords are protected for the current user with DPAPI; if the file was moved to another account or machine, enter the password again.
- If `database-config.json` is absent, startup selects the current default SQLite database; database values in `.env` are ignored and scrubbed. If a present config file is invalid, repair it through the Database section.
- If startup reports schema drift, a non-empty unversioned schema, or an unknown/previous revision, startup fails without modifying the database. Recreate the database to use the current schema, or restore a separate backup for any data that must be retained. Automatic repair is disabled.
- For migration lock timeouts, stop the competing initializer/session and retry. SQLite uses `BEGIN IMMEDIATE`; PostgreSQL reports a bounded advisory-lock timeout.
- If training dataset deletion reports a checkpoint conflict, inspect the listed checkpoint metadata and either retain the dataset or remove/update the referencing checkpoint through the normal checkpoint workflow. Unreadable checkpoint metadata is treated as a conflict for safety.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for supported local distribution constraints.
