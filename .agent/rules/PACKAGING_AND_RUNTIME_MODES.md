# FAIRS Packaging and Runtime Modes

## 1. Strategy

FAIRS uses a single active runtime file:

- `FAIRS/settings/.env`

Runtime switching is configuration-only:

- Local mode: host execution without Docker.
- Cloud mode: Docker Compose (`backend` + `frontend`).
- Switch modes by changing `FAIRS/settings/.env` values (or copying a profile example).

## 2. Runtime profiles

- `FAIRS/settings/.env.local.example`: local defaults.
- `FAIRS/settings/.env.cloud.example`: cloud defaults.
- `FAIRS/settings/.env`: active values for launcher, tests, and docker compose.
- `FAIRS/settings/configurations.json`: non-runtime defaults (jobs/device tuning).

## 3. Required environment keys

| Key | Purpose |
|---|---|
| `FASTAPI_HOST`, `FASTAPI_PORT` | Backend host/port. |
| `UI_HOST`, `UI_PORT` | Frontend host/port. |
| `VITE_API_BASE_URL` | Frontend API base path (`/api` expected for same-origin proxying). |
| `ENABLE_API_DOCS` | Enables FastAPI docs/OpenAPI endpoints (`true` for local, `false` recommended in cloud). |
| `RELOAD` | Enables Uvicorn reload in local mode when `true`. |
| `OPTIONAL_DEPENDENCIES` | Enables optional extras (tests/playwright) during local setup. |
| `DB_EMBEDDED` | `true` = embedded SQLite, `false` = external DB config required. |
| `DB_ENGINE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | External DB connection settings. |
| `DB_SSL`, `DB_SSL_CA` | DB TLS settings for external DB mode. |
| `DB_CONNECT_TIMEOUT`, `DB_INSERT_BATCH_SIZE` | DB runtime tuning values. |
| `MPLBACKEND`, `KERAS_BACKEND` | Runtime plotting/ML backend selection. |

## 4. Local mode (default)

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

## 5. Cloud mode (Docker)

1. Activate cloud profile:

```cmd
copy /Y FAIRS\settings\.env.cloud.example FAIRS\settings\.env
```

2. Build images:

```bash
docker compose --env-file FAIRS/settings/.env build --no-cache
```

3. Start services:

```bash
docker compose --env-file FAIRS/settings/.env up -d
```

4. Stop services:

```bash
docker compose --env-file FAIRS/settings/.env down
```

Cloud topology:

- `backend`: FastAPI/Uvicorn on internal `8000` (not published to host by docker compose).
- `frontend`: Nginx serving built SPA.
- `/api/*` is proxied from frontend to backend.

## 6. Deterministic build notes

- Backend lockfile: `uv.lock`.
- Backend install path in Docker: `uv sync --frozen`.
- Frontend lockfile: `FAIRS/client/package-lock.json`.
- Frontend install path in Docker: `npm ci`.
- Base images are pinned by tag in:
  - `docker/backend.Dockerfile`
  - `docker/frontend.Dockerfile`

## 7. Data persistence in cloud mode

Docker volume:

- `fairs_resources` is mounted to `/app/FAIRS/resources`.

This preserves checkpoints, embedded database files, and logs across container restarts.
