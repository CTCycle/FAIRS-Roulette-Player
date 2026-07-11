## Quick Start

Last updated: 2026-06-02

## Fastest Path

1. From repository root, run:

```cmd
start_on_windows.ps1
```

2. Open the UI at the configured frontend URL from `UI_HOST:UI_PORT`.
3. Use the top navigation to switch between:
   - `Training`
   - `Inference`

## Primary Commands

Start the app:

```cmd
start_on_windows.ps1
```

Run the automated test entry point:

```cmd
app\tests\run_tests.bat
```

Build the desktop package:

```cmd
release\tauri\build_with_tauri.bat
```

Open maintenance tools:

```cmd
start_on_windows.ps1 init-db
```

## Orientation

- Use local web mode for normal development and experimentation.
- Use desktop packaging only when preparing distributable Windows builds.
- Keep `settings` and environment configuration aligned with the runtime mode you intend to use.

## Related Files

- Read `workflows.md` for end-user task sequences.
- Read `../runtime/startup.md` for PowerShell and CMD launch details.
