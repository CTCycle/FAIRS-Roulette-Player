## Troubleshooting

Last updated: 2026-08-20

## Startup Problems

- If local startup fails, run option 2 in `start_on_windows.ps1` and choose `Standard` to resync runtimes and application dependencies.
- If test or browser tooling is missing, run option 2 and choose `Development` so the server's `test` extra is installed.
- If ports are already occupied, resolve the conflicting listeners before relaunching.
- If the backend starts without the frontend, verify that `app/client/node_modules` contains Vite and that `app/client/dist/index.html` and its generated assets exist; retry option 1 for automatic recovery, run option 3 for a frontend-only rebuild, or run option 2 when frontend dependencies also need updating.
- Option 2 stops a process listening on the configured `UI_PORT` before `npm ci` replaces frontend dependencies. If npm still reports `EPERM` for `esbuild.exe`, stop any external Vite or Node process using `app/client/node_modules` and retry.
- If the launcher reports a backend readiness failure, open `http://<FASTAPI_HOST>:<FASTAPI_PORT>/api/health` and inspect the generated `FAIRS_*.log` file.

## API Docs Problems

- If `/docs` is unavailable, check `ENABLE_API_DOCS`.
- If the backend root does not show docs when no frontend build exists, verify docs were not explicitly disabled.

## Test Problems

- If browser-dependent tests fail to start correctly, choose `Development` in the launcher's install/update option and rerun the test setup flow.
- Prefer starting with the smallest failing test slice before rerunning the full test suite.

## Configuration Problems

- If database startup fails, confirm the embedded-vs-external database settings are internally consistent.
- If PostgreSQL mode is enabled, select option 4 in `start_on_windows.ps1` to create or upgrade the configured database. FastAPI startup runs the same idempotent runner. A missing target is created only for SQLSTATE `3D000`, and the configured role needs `CREATEDB`.
- If startup reports an unsupported database engine, set external PostgreSQL configuration to `DATABASE_ENGINE=postgresql+psycopg`; legacy aliases are not accepted.
- If startup reports schema drift, a partial legacy schema, or an unknown/ahead revision, do not delete or reset the database. Review the Alembic revision and database state, make an explicit reviewed migration or restore the matching revision scripts, then retry. Automatic repair is disabled.
- For migration lock timeouts, stop the competing initializer/session and retry. SQLite uses `BEGIN IMMEDIATE`; PostgreSQL reports a bounded advisory-lock timeout.
- If training dataset deletion reports a checkpoint conflict, inspect the listed checkpoint metadata and either retain the dataset or remove/update the referencing checkpoint through the normal checkpoint workflow. Unreadable checkpoint metadata is treated as a conflict for safety.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for supported local distribution constraints.
