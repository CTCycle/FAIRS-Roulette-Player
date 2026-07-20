## Deployment

Last updated: 2026-07-20

## Supported Distribution

FAIRS is run locally from its repository through `start_on_windows.ps1`. The repository does not maintain an installer or bundled application release path.

## Local Build Chain

- portable Python, uv, and Node.js are prepared under `runtimes/`
- backend dependencies are synchronized into `app/server/.venv`
- frontend dependencies are installed in `app/client/node_modules`
- `npm run build` produces the frontend used by `npm run preview`

## Constraints

- Windows is the supported launcher platform.
- No container deployment path is documented or supported in this repository.
- Training workloads remain compute-heavy and depend on the existing worker-process model.

## Related Files

- Read `startup.md` for the command entry points.
- Read `../coding/windows_automation.md` for implementation constraints around launcher scripts.
