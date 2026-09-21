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
- If database startup fails, confirm the embedded-vs-external database settings are internally consistent.
- If PostgreSQL mode is enabled, select option 4 in `start_on_windows.ps1` to create or upgrade the configured database. FastAPI startup runs the same idempotent runner. A missing target is created only for SQLSTATE `3D000`, and the configured role needs `CREATEDB`.
- If startup reports an unsupported database engine, set external PostgreSQL configuration to `DATABASE_ENGINE=postgresql+psycopg`; legacy aliases are not accepted.
- If startup reports schema drift, a partial legacy schema, or an unknown/ahead revision, do not delete or reset the database. Review the Alembic revision and database state, make an explicit reviewed migration or restore the matching revision scripts, then retry. Automatic repair is disabled.
- For migration lock timeouts, stop the competing initializer/session and retry. SQLite uses `BEGIN IMMEDIATE`; PostgreSQL reports a bounded advisory-lock timeout.
- If training dataset deletion reports a checkpoint conflict, inspect the listed checkpoint metadata and either retain the dataset or remove/update the referencing checkpoint through the normal checkpoint workflow. Unreadable checkpoint metadata is treated as a conflict for safety.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for supported local distribution constraints.
