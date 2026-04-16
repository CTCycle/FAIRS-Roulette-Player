# FAIRS Packaging and Runtime Modes

Last updated: 2026-04-13

## 1. Runtime Strategy

FAIRS uses a single active runtime profile file:

- `FAIRS/settings/.env`

Mode switching is configuration-driven:

- Local mode: launch with `FAIRS/start_on_windows.bat`.
- Desktop packaged mode: build/run through Tauri packaging helpers.

## 2. Runtime Configuration Files

- `FAIRS/settings/.env.example`: runtime template.
- `FAIRS/settings/.env`: active runtime values used by launcher/tests/frontend/Tauri startup.
- `FAIRS/settings/configurations.json`: backend technical defaults (`database`, `jobs`, `device`).

Initialize runtime file (Windows):

```cmd
copy /Y FAIRS\settings\.env.example FAIRS\settings\.env
```

## 3. Runtime Keys

| Key | Purpose |
|---|---|
| `FASTAPI_HOST`, `FASTAPI_PORT` | Backend bind host/port. |
| `UI_HOST`, `UI_PORT` | Local frontend preview host/port. |
| `ENABLE_API_DOCS` | Enables `/docs`, `/redoc`, OpenAPI routes. |
| `RELOAD` | Enables Uvicorn reload in local mode. |
| `OPTIONAL_DEPENDENCIES` | Installs optional extras (tests/playwright). |
| `MPLBACKEND`, `KERAS_BACKEND` | Plotting/ML backend runtime settings. |

Note: `FAIRS_TAURI_MODE` is set by Tauri runtime at launch time and is not expected in `.env`.

Technical value resolution order:
1. `FAIRS/settings/configurations.json` (source of truth for `database`, `jobs`, `device`)
2. explicit runtime reload through configuration manager APIs during tests/internal tooling

Runtime/process env values are still loaded from `.env` and accessed as standard environment variables.

## 4. Local Mode

1. Activate local profile.
2. Launch:

```cmd
FAIRS\start_on_windows.bat
```

3. Optional full test run:

```cmd
tests\run_tests.bat
```

`start_on_windows.bat` provisions portable runtimes under `runtimes/`, syncs dependencies with `uv`, ensures frontend dependencies/build, then starts backend + frontend.

## 5. Desktop Packaged Mode (Tauri)

### 5.1 Maintainer prerequisites

- Rust/Cargo installed and usable.
- Default Rust toolchain configured (`rustup default stable`).
- Portable runtimes provisioned under `runtimes` (run `FAIRS/start_on_windows.bat` first).

### 5.2 Packaging entrypoint

1. Ensure `FAIRS/settings/.env` has the desired runtime host/port/backends.
2. Build through repository helper:

```cmd
release\tauri\build_with_tauri.bat
```

Do not treat raw `tauri build` as the main path; the helper validates runtime payload and exports distribution artifacts.

### 5.3 Icon workflow

Canonical icon source:

- `FAIRS/client/public/favicon.png`

Regenerate desktop icons:

```cmd
cd FAIRS\client
npm run tauri:icon
```

### 5.4 What the helper stages

`release/tauri/build_with_tauri.bat` validates and stages:

- runtime binaries (`python.exe`, `uv.exe`, `node.exe`, `npm.cmd`)
- runtime lockfile (`runtimes/uv.lock`)
- bundle source tree in `FAIRS/client/src-tauri/r`
- required workspace/runtime junctions for bundled execution

Then it runs `npm run tauri:build:release` and exports Windows artifacts.

### 5.5 Packaged startup behavior

- Tauri shows startup screen and resolves workspace/runtime root.
- If needed, it runs `uv sync --frozen` into runtime-managed `runtimes/.venv`.
- Backend process is started as `python -m uvicorn FAIRS.server.app:app`.
- `FAIRS_TAURI_MODE=true` is injected for packaged backend behavior.
- Window redirects to `http://127.0.0.1:<FASTAPI_PORT>/` when backend is ready.
- On exit, backend process tree is terminated.

### 5.6 Packaged HTTP behavior

When packaged SPA assets exist:

- FastAPI serves SPA at `/`.
- `/assets` is served from `FAIRS/client/dist/assets`.
- API routes remain available under `/api` (and optionally direct).
- Unknown SPA routes fallback to `index.html`.

## 6. Distribution Output

User-facing artifacts are exported to:

- `release/windows/installers`
- `release/windows/portable`

Portable payload includes app executable and required runtime entries (`FAIRS`, `runtimes`, `pyproject.toml`, `uv.lock`, optional `_up_`).

## 7. Desktop Cleanup

From `FAIRS/client`:

```cmd
npm run tauri:clean
```

Or via:

```cmd
FAIRS\setup_and_maintenance.bat
```

Choose `Clean desktop build artifacts`.
