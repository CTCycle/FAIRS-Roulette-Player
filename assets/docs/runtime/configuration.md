## Configuration

Last updated: 2026-09-16

## Configuration Ownership

FAIRS uses three distinct configuration surfaces with non-overlapping responsibilities:

1. `settings/.env` for deployment/runtime environment values such as hosts, ports, storage location, database connection, backend visibility, API docs, reload behavior, and ML backend selection.
2. `<data-root>/runtime-settings.json` for the application-wide technical settings exposed by the Settings UI/API. It owns job polling and global JIT/compiler behavior.
3. `TrainingConfig` in `app/server/contracts/training.py` for all per-training defaults, semantic constraints, dataset choices, model parameters, device selection, and mixed precision.

No setting should be independently defaulted in more than one of these surfaces.

## Environment Variables

The runtime consumes these environment keys:

- `FASTAPI_HOST`
- `FASTAPI_PORT`
- `UI_HOST`
- `UI_PORT`
- `BACKEND_LOGS_VISIBLE`
- `ENABLE_API_DOCS`
- `RELOAD`
- `FAIRS_DATA_DIR`
- `EMBEDDED_DATABASE`
- `DATABASE_ENGINE`
- `DATABASE_HOST`
- `DATABASE_PORT`
- `DATABASE_NAME`
- `DATABASE_USERNAME`
- `DATABASE_PASSWORD`
- `DATABASE_SSL`
- `DATABASE_SSL_CA`
- `DATABASE_CONNECT_TIMEOUT`
- `DATABASE_INSERT_BATCH_SIZE`
- `MPLBACKEND`
- `KERAS_BACKEND`
- `WEB_CONCURRENCY`, `UVICORN_WORKERS`, `FAIRS_WORKERS`

`settings/.env.example` is the canonical environment template. The Windows launcher copies it to `settings/.env` only when `.env` does not yet exist. It never overlays a hardcoded default map on an existing `.env`.

For launcher operations, the following values must be explicitly present and non-empty in `.env`: `FASTAPI_HOST`, `FASTAPI_PORT`, `UI_HOST`, `UI_PORT`, `RELOAD`, `BACKEND_LOGS_VISIBLE`, and `EMBEDDED_DATABASE`. An existing stale `.env` that omits them fails with an actionable message instead of silently inheriting compatibility defaults.

`FAIRS_DATA_DIR` may be empty. An empty value means the normal `app/resources` data root.

## Internal Runtime Settings

The launcher sets only execution-scoped tool variables:

- `UV_PROJECT_ENVIRONMENT` targets `app/server/.venv`.
- `UV_CACHE_DIR`, `NPM_CONFIG_CACHE`, `PIP_CACHE_DIR`, and `PYTHONPYCACHEPREFIX` are rooted below `runtimes/cache`.
- `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `COVERAGE_FILE`, and `PLAYWRIGHT_BROWSERS_PATH` are rooted below `app/tests/cache`.

These cache roots are canonical. The launcher does not scan the repository for historical `.uv-cache`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, Vite cache, or other legacy locations.

## Runtime Settings File

The runtime settings file is `<FAIRS_DATA_DIR>/runtime-settings.json` when `FAIRS_DATA_DIR` is configured; otherwise it is `app/resources/runtime-settings.json`. It is created on startup when absent and is ignored by source control because it is local user state.

Startup resolution is strict and deterministic:

- An existing runtime file is parsed and validated. Malformed or invalid content fails startup.
- When the runtime file is absent, the validated defaults are written to the runtime path.

Writes use a same-directory temporary file, flush and `fsync`, then `os.replace` so readers see either the previous complete document or the new complete document. The Settings API merges strict partial updates, persists the runtime file, and applies the accepted snapshot to the live `TrainingService`; it does not read or write `.env`, the database, or `TrainingConfig`.

## Database Configuration

Database configuration is accepted only from the environment model so connection ownership is unambiguous.

For external PostgreSQL mode, `DATABASE_ENGINE` must be `postgresql+psycopg`. Legacy aliases such as `postgres`, `postgresql`, and `postgresql+psycopg2` are rejected rather than normalized.

- `EMBEDDED_DATABASE=true` selects SQLite.
- `EMBEDDED_DATABASE=false` selects PostgreSQL and requires valid connection settings.

Both modes use the same SQLAlchemy repositories and Alembic schema.

## Structured Settings

The runtime settings document currently owns:

- `jobs.polling_interval`
- `device.jit_compile`
- `device.jit_backend`

Global mixed precision is intentionally not present. `use_mixed_precision`, `use_device_gpu`, and `device_id` are per-training values owned by `TrainingConfig`.

## Training Configuration

`TrainingConfig` is the canonical owner of training defaults and cross-field semantic validation. The frontend obtains generated default values from `app/client/src/generated/api.ts`, which is derived from the Pydantic model by `app/scripts/generate_frontend_contracts.py`.

The training wizard may provide presentation-level input constraints, but it does not maintain a second implementation of semantic rules. Submission validation goes through `POST /api/training/validate`, using the same Pydantic contract that starts the training run.

## Lifecycle and Worker Contract

- FastAPI construction remains import-safe. Runtime bootstrap and mutable environment loading occur in lifespan startup.
- `WEB_CONCURRENCY`, `UVICORN_WORKERS`, and `FAIRS_WORKERS` must be unset or exactly `1` because live jobs and inference models are process-local.
- `RELOAD=true` is development-only and expires process-local training/inference state when the process reloads.
- `BACKEND_LOGS_VISIBLE` is an explicit launcher configuration value, not an implicit launcher default.
- The backend creates timestamped `FAIRS_*.log` files under the active data root.
- Settings changes update future parent polling immediately. A newly started worker receives a launch snapshot of polling and JIT values; an active worker keeps its existing snapshot. Resuming a checkpoint uses the current polling interval while preserving the checkpoint's model configuration.

## Related Files

- Read `startup.md` for launcher behavior.
- Read `../architecture/backend_api.md` for the Settings endpoints.
- Read `../architecture/persistence.md` for database and checkpoint consequences.
- Read `../architecture/backend_api.md` for generated transport contracts.
