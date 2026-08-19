## Deployment

Last updated: 2026-08-19

## Supported Distribution

FAIRS is distributed as source and run locally from its repository through `start_on_windows.ps1`. The repository does not maintain an installer, bundled executable, container image, or packaged desktop release path.

## Local Build Chain

- portable Python `3.14.2`, uv, and Node.js `22.13.0` are prepared under `runtimes/`
- backend dependencies are synchronized into `app/server/.venv`
- frontend dependencies are installed in `app/client/node_modules`
- `npm run build` produces the frontend used by `npm run preview`; the launcher invokes this after dependency installation in option 2, directly through option 3, and during option 1 recovery when the environment or build is unusable

## Constraints

- Windows is the supported launcher platform.
- No container deployment path is documented or supported in this repository.
- Training workloads remain compute-heavy and depend on the existing worker-process model.
- The launcher is the supported operational boundary for preparing runtimes, starting services, testing, and removing generated dependencies/build output while preserving source and user data.

## Source Release Boundary

- The current source release is `v2.8.0`.
- Releases use annotated `vX.Y.Z` tags from the synchronized `main` branch; GitHub supplies the repository source archives for the tag.
- This repository has no Tauri, MSI, portable executable, installer, or release-artifact workflow. Do not describe a packaged desktop artifact as part of the supported distribution.

## Related Files

- Read `startup.md` for the command entry points.
- Read `../coding/windows_automation.md` for implementation constraints around launcher scripts.
