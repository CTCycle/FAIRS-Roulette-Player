## Troubleshooting

Last updated: 2026-08-02

## Startup Problems

- If local startup fails, run option 2 in `start_on_windows.ps1` and choose `Standard` to resync runtimes and application dependencies.
- If test or browser tooling is missing, run option 2 and choose `Development` so the server's `test` extra is installed.
- If ports are already occupied, resolve the conflicting listeners before relaunching.
- If the backend starts without the frontend, verify that `app/client/node_modules` contains Vite and that `app/client/dist` exists; use option 2 with `ALWAYS_REBUILD=true` to rebuild.
- If the launcher reports a backend readiness failure, open `http://<FASTAPI_HOST>:<FASTAPI_PORT>/api/health` and inspect the generated `FAIRS_*.log` file.

## API Docs Problems

- If `/docs` is unavailable, check `ENABLE_API_DOCS`.
- If the backend root does not show docs when no frontend build exists, verify docs were not explicitly disabled.

## Test Problems

- If browser-dependent tests fail to start correctly, choose `Development` in the launcher's install/update option and rerun the test setup flow.
- Prefer starting with the smallest failing test slice before rerunning the full test suite.

## Configuration Problems

- If database startup fails, confirm the embedded-vs-external database settings are internally consistent.
- If PostgreSQL mode is enabled, verify the configured engine and connection details match the supported backend expectations; startup must be able to reach the server and create or ensure the target database/schema.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for supported local distribution constraints.
