## Troubleshooting

Last updated: 2026-07-20

## Startup Problems

- If local startup fails, rerun `start_on_windows.ps1` to resync runtimes and dependencies.
- If ports are already occupied, resolve the conflicting listeners before relaunching.
- If the backend starts without the frontend, verify the frontend dependency and build steps completed successfully.
- If the launcher reports a backend readiness failure, open `http://<FASTAPI_HOST>:<FASTAPI_PORT>/api/health` and inspect the generated `FAIRS_*.log` file.

## API Docs Problems

- If `/docs` is unavailable, check `ENABLE_API_DOCS`.
- If the backend root does not show docs when no frontend build exists, verify docs were not explicitly disabled.

## Test Problems

- If browser-dependent tests fail to start correctly, choose `Development` in the launcher's install/update option and rerun the test setup flow.
- Prefer starting with the smallest failing test slice before rerunning the full test suite.

## Configuration Problems

- If database startup fails, confirm the embedded-vs-external database settings are internally consistent.
- If PostgreSQL mode is enabled, verify the configured engine and connection details match the supported backend expectations; startup must be able to reach the server and ensure the target database/schema.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for supported local distribution constraints.
