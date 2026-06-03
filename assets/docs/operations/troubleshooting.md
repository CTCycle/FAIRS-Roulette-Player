## Troubleshooting

Last updated: 2026-06-02

## Startup Problems

- If local startup fails, rerun `start_on_windows.bat` to resync runtimes and dependencies.
- If ports are already occupied, resolve the conflicting listeners before relaunching.
- If the backend starts without the frontend, verify the frontend dependency and build steps completed successfully.

## API Docs Problems

- If `/docs` is unavailable, check `ENABLE_API_DOCS`.
- If the backend root does not show docs when no frontend build exists, verify docs were not explicitly disabled.

## Test Problems

- If browser-dependent tests fail to start correctly, confirm optional dependencies are enabled where required and rerun the launcher or test setup flow.
- Prefer starting with the smallest failing test slice before rerunning the full test suite.

## Desktop Packaging Problems

- If the packaged app fails to start, verify the Rust toolchain and rerun `release\tauri\build_with_tauri.bat`.
- If Tauri mode fails immediately, confirm `app/client/dist/index.html` exists before packaging or desktop launch.
- If export scripts fail, inspect whether the expected release bundle or portable payload entries were generated.

## Configuration Problems

- If database startup fails, confirm the embedded-vs-external database settings are internally consistent.
- If PostgreSQL mode is enabled, verify the configured engine and connection details match the supported backend expectations.

## Related Files

- Read `../runtime/configuration.md` for the active settings surface.
- Read `../runtime/deployment.md` for packaging-specific constraints.
