## Deployment

Last updated: 2026-06-23

## Desktop Packaging Outputs

`release/tauri/build_with_tauri.bat` exports Windows artifacts under:

- `release/windows/installers`
- `release/windows/portable`

The versioned Tauri project lives under `app/src-tauri` and is limited to source code, configuration, icons, capabilities, and required build metadata.

Generated packaging outputs under `app/src-tauri/target`, `app/src-tauri/bundle`, `app/src-tauri/gen`, and `release/windows` are local or release artifacts and must not be committed to Git. Desktop binaries are published as release artifacts instead of repository content.

## Build Chain

- Frontend build:
  - `npm run build` in `app/client`
- Tauri build:
  - `npm run tauri:build`
- Windows export:
  - `npm run tauri:export:windows`
- End-to-end helper:
  - `npm run tauri:build:release`
  - typically invoked through `release/tauri/build_with_tauri.bat`

## Bundled Runtime Expectations

- The packaged desktop runtime bundles the frontend build, backend source, settings, resources, and required runtime payloads as configured by Tauri packaging.
- Export scripts expect the Tauri release bundle and portable payload entries to exist before artifact export completes.

## Constraints

- Desktop packaging is Windows-focused.
- Linux and macOS desktop packaging are not maintained as first-class workflows here.
- No container deployment path is documented or supported in this repository.
- Training workloads remain compute-heavy and depend on the existing worker-process model.

## Related Files

- Read `startup.md` for the command entry points.
- Read `../coding/windows_automation.md` for implementation constraints around scripts and Tauri behavior.
