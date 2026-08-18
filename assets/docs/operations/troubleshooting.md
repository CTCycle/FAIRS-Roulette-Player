## Troubleshooting

Last updated: 2026-08-19

## Startup Problems

- If local startup fails, run option 2 in `start_on_windows.ps1` and choose `Standard` to resync runtimes and application dependencies.
- If test or browser tooling is missing, run option 2 and choose `Development` so the server's `test` extra is installed.
- If ports are already occupied, resolve the conflicting listeners before relaunching.
- If the backend starts without the frontend, verify that `app/client/node_modules` contains Vite and that `app/client/dist/index.html` and its generated assets exist; retry option 1 for automatic recovery or run option 2 for an explicit rebuild.
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
- If PostgreSQL mode is enabled, select option 3 in `start_on_windows.ps1` once to create or initialize the configured database and schema. Normal startup only probes the existing database; it never creates or resets it. Invalid or unavailable connection settings therefore stop startup and must be corrected before relaunching.
- If startup reports an unsupported database engine, set external PostgreSQL configuration to `DATABASE_ENGINE=postgresql+psycopg`; legacy aliases are not accepted.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for supported local distribution constraints.
