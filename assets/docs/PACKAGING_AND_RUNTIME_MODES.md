# FAIRS Packaging and Runtime Modes

## 1. Strategy

FAIRS uses one active runtime file:

- `FAIRS/settings/.env`

Runtime switching is configuration-only:

- Local mode: host execution through `FAIRS\start_on_windows.bat`.
- Desktop packaged mode: Tauri shell + local packaged backend.
- Switch modes by copying the relevant profile into `FAIRS/settings/.env`.

## 2. Runtime profiles

- `FAIRS/settings/.env.local.example`: local defaults.
- `FAIRS/settings/.env.local.tauri.example`: packaged desktop defaults.
- `FAIRS/settings/.env`: active values for launcher, tests, and desktop packaging.
- `FAIRS/settings/configurations.json`: non-runtime defaults.

## 3. Required environment keys

| Key | Purpose |
|---|---|
| `FASTAPI_HOST`, `FASTAPI_PORT` | Backend bind host and port. Packaged desktop mode should use loopback. |
| `UI_HOST`, `UI_PORT` | Local frontend preview host and port. |
| `VITE_API_BASE_URL` | Frontend API base path. Desktop mode uses `/api`. |
| `ENABLE_API_DOCS` | Enables FastAPI docs/OpenAPI endpoints. |
| `FAIRS_ALLOW_DIRECT_API_ROUTES` | When `false`, backend domain routes are exposed only under `/api/*` for consistent frontend routing. |
| `RELOAD` | Enables Uvicorn reload in local mode when `true`. |
| `OPTIONAL_DEPENDENCIES` | Adds optional backend extras during `uv sync`. |
| `DB_EMBEDDED` | `true` = embedded SQLite, `false` = external DB config required. |
| `DB_ENGINE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | External DB connection settings. |
| `DB_SSL`, `DB_SSL_CA` | DB TLS settings for external DB mode. |
| `DB_CONNECT_TIMEOUT`, `DB_INSERT_BATCH_SIZE` | DB runtime tuning values. |
| `MPLBACKEND`, `KERAS_BACKEND` | Runtime plotting and ML backend selection. |

## 4. Local mode

1. Activate local profile:

```cmd
copy /Y FAIRS\settings\.env.local.example FAIRS\settings\.env
```

2. Start app:

```cmd
FAIRS\start_on_windows.bat
```

3. Optional test run:

```cmd
tests\run_tests.bat
```

## 5. Desktop packaged mode

### 5.1 Maintainer prerequisites

- Rust/Cargo installed on the maintainer machine, with a default toolchain configured (`rustup default stable`).
- WebView2 installed on the maintainer machine.
- Portable runtimes provisioned under `runtimes`.

Provision the portable runtimes with:

```cmd
FAIRS\start_on_windows.bat
```

That script prepares:

- `runtimes/python/python.exe`
- `runtimes/uv/uv.exe`
- `runtimes/nodejs/node.exe`
- `runtimes/nodejs/npm.cmd`
- `runtimes/.venv`
- `runtimes/uv.lock`

It also normalizes the extracted Node layout so `node.exe` lives directly under `runtimes/nodejs`.

### 5.2 Shared desktop icon source

The canonical desktop icon source is:

- `FAIRS/client/public/favicon.png`

It is also referenced by the plain web app. Regenerate the Tauri desktop icons with:

```cmd
cd FAIRS\client
npm run tauri:icon
```

That command:

- runs `tauri icon public/favicon.png`;
- refreshes `FAIRS/client/src-tauri/icons`;
- removes generated `android` and `ios` icon folders so the repo stays desktop-only.

### 5.3 Packaging entrypoint

1. Activate the packaged desktop profile:

```cmd
copy /Y FAIRS\settings\.env.local.tauri.example FAIRS\settings\.env
```

2. Build desktop artifacts through the repo entrypoint:

```cmd
release\tauri\build_with_tauri.bat
```

Do not treat raw `tauri build` as the primary path, because the repo helper also validates runtimes, stages resources, and exports public artifacts.

### 5.4 What the packaging helper does

`release/tauri/build_with_tauri.bat`:

- validates the bundled runtime files before build;
- fails early with actionable Rust setup guidance when Cargo is present but no default Rust toolchain is configured;
- stages a short bundle source tree at `FAIRS/client/src-tauri/r`;
- copies `pyproject.toml` and `runtimes/uv.lock` into that staging tree as packaged `uv.lock` (and `runtimes/uv.lock`);
- junctions the runtime directories required by the packaged app;
- prepends the portable Node runtime to `PATH` for frontend build steps;
- installs frontend dependencies with the portable Node runtime;
- runs `npm run tauri:build:release` inside `FAIRS/client`;
- removes the transient staging tree on both success and failure;
- exports distribution artifacts to `release/windows`.

### 5.5 Resource map and runtime tree

The packaged runtime reconstructs this workspace shape:

```text
<runtime root>/
  pyproject.toml
  uv.lock
  FAIRS/
    server/
    scripts/
    settings/
    client/dist/
    resources/
      checkpoints/
      database.db
      logs/
  runtimes/
    uv.lock
    .venv/
    .uv-cache/
    nodejs/
    python/
    uv/
```

`FAIRS/client/src-tauri/tauri.conf.json` keeps that layout explicit through the Tauri resource whitelist.

### 5.6 Packaged startup behavior

- Tauri starts at `about:blank` and renders an in-window splash screen immediately.
- Rust resolves a packaged workspace by looking for `pyproject.toml` plus `FAIRS/server/app.py`.
- If multiple valid roots are found, it prefers one that already contains `runtimes\.venv\Scripts\python.exe`.
- Rust picks a writable runtime root: the workspace root when reusable, otherwise `%LOCALAPPDATA%\com.fairs.desktop\runtime`.
- If `runtimes\.venv\Scripts\python.exe` is missing in that runtime root, Rust runs `uv sync --python <bundled-python> --frozen` first, then falls back to `uv sync --frozen`.
- Sync runs with `UV_PROJECT_ENVIRONMENT=<runtime-root>\runtimes\.venv` and `UV_CACHE_DIR=<runtime-root>\runtimes\.uv-cache`.
- After sync, Rust launches `python -m uvicorn FAIRS.server.app:app --host <host> --port <port>` from the resolved `runtimes\.venv`.
- The window redirects to `http://127.0.0.1:<FASTAPI_PORT>/` after backend readiness is inferred from TCP connectivity.
- On exit, the app kills the backend process tree with `taskkill /PID <pid> /T /F`.

### 5.7 Packaged HTTP behavior

When `FAIRS_TAURI_MODE=true` and `FAIRS/client/dist` exists:

- FastAPI serves `index.html` at `/`.
- `/assets` is mounted from `FAIRS/client/dist/assets`.
- API routers remain available at their original paths and again under `/api`.
- Unknown SPA routes fall back to `index.html`.
- If the packaged frontend is unavailable, `/` redirects to `/docs` when docs are enabled.

### 5.8 Distribution output

The user-facing output is exported to:

- `release/windows/installers`
- `release/windows/portable`

The portable folder contains the desktop `.exe` plus the runtime payload entries required by the packaged launcher (`FAIRS`, `runtimes`, `pyproject.toml`, `uv.lock`, and `_up_` when present).

`release/tauri/scripts/export-windows-artifacts.ps1` also verifies that `portable/runtimes/uv/uv.exe`, `portable/runtimes/python/python.exe`, `portable/runtimes/nodejs/node.exe`, and `portable/runtimes/nodejs/npm.cmd` are present in the exported payload.

## 6. Desktop cleanup

Clean desktop build residue with:

```cmd
cd FAIRS\client
npm run tauri:clean
```

Or through the maintenance menu:

```cmd
FAIRS\setup_and_maintenance.bat
```

Then choose `Clean desktop build artifacts`.
