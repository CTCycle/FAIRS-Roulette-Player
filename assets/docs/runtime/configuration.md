## Configuration

Last updated: 2026-09-03

## Environment Variables

The runtime scripts and backend consume these environment keys:

- `FASTAPI_HOST`
- `FASTAPI_PORT`
- `UI_HOST`
- `UI_PORT`
- `BACKEND_LOGS_VISIBLE`
- `ENABLE_API_DOCS`
- `RELOAD`
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

## Internal Runtime Settings

- `UV_PROJECT_ENVIRONMENT`
  - set by the launcher to target the runtime virtual environment
- `UV_CACHE_DIR`, `NPM_CONFIG_CACHE`, `PIP_CACHE_DIR`, and `PYTHONPYCACHEPREFIX`
  - set by the launcher below `runtimes/cache`
- `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `COVERAGE_FILE`, and `PLAYWRIGHT_BROWSERS_PATH`
  - set by the launcher below `app/tests/cache`
- `FAIRS_DATA_DIR`
  - overrides the mutable database, logs, and checkpoints directory

For external PostgreSQL mode, `DATABASE_ENGINE` must be `postgresql+psycopg`. Legacy aliases such as `postgres`, `postgresql`, and `postgresql+psycopg2` are rejected during startup validation.

The backend creates timestamped `FAIRS_*.log` files under the active data root's `logs` directory.

The FastAPI lifespan calls `server.bootstrap.bootstrap_runtime()` before importing Keras-backed application modules. Direct construction/import of `server.app`, `server`, common path helpers, and logging helpers does not load `.env`, resolve mutable paths from the environment, create directories, or configure the global logging tree.

### Lifecycle And Worker Contract

- FastAPI application construction is import-safe; runtime bootstrap, database initialization, service construction, and logging setup occur inside the lifespan.
- Lifespan state transitions are `starting`, `ready`, `stopping`, and `stopped`. Startup rolls back acquired resources on failure, and shutdown attempts every owned cleanup operation even when one cleanup fails.
- `WEB_CONCURRENCY`, `UVICORN_WORKERS`, and `FAIRS_WORKERS` must be unset or exactly `1`. The launcher also passes `--workers 1` explicitly. This application does not provide a shared store for process-local training jobs or live inference models.
- `RELOAD=true` is development-only. A reload replaces the in-memory process and expires active training and inference state.
- `FAIRS_DATA_DIR` controls persistent database/checkpoint/log ownership; it does not make in-memory jobs or live models durable.

## Structured Settings

`settings/configurations.json` contains non-env technical settings such as:

- `jobs.polling_interval`
- device-related options such as JIT and mixed-precision defaults

`settings/configurations.json` must not contain a `database` block. Database configuration is accepted only from `settings/.env`, and startup rejects JSON database settings to avoid ambiguous sources of truth.

## Behavior Differences Driven By Configuration

### API Docs

- `ENABLE_API_DOCS` controls whether `/docs`, `/redoc`, and OpenAPI routes are mounted.

### Database Mode

- `EMBEDDED_DATABASE=true`
  - uses SQLite and runs the Alembic create/upgrade runner against the configured data-root database
  - uses an immediate migration lock and strict metadata validation; it never resets or repairs drift automatically
- `EMBEDDED_DATABASE=false`
  - uses PostgreSQL and requires explicit connection settings
  - first tries the configured database and creates it only after SQLSTATE `3D000`, under an admin advisory lock
  - requires `CREATEDB` for automatic database creation; migrations then run under a target transaction advisory lock

The application and launcher use the same idempotent runner. Empty databases upgrade to `head`; non-empty unversioned databases are rejected unchanged and must be migrated explicitly. Partial/drifted/unknown/ahead states fail before service construction.

### Backend Log Visibility

- `BACKEND_LOGS_VISIBLE=false` starts the backend detached and hidden.
- `BACKEND_LOGS_VISIBLE=true` opens a dedicated backend terminal so logs remain visible; closing that terminal is the local application stop action.
- When `BACKEND_LOGS_VISIBLE` is absent, the launcher defaults to `true`.

### Dependency Installation And Frontend Build

- The launcher checks runtime readiness before installing dependencies.
- The checked-in `settings/.env.example` template defaults to API port `8890` and UI port `8051`; override them in `settings/.env` when needed.
- Launcher option 2 selects `Standard` or `Development` installation, installs dependencies, rebuilds the frontend, and runs database create/upgrade; `Development` adds the backend's test extra.
- Normal application startup skips installation and rebuilding when the environment and frontend build are ready. If either is missing or unusable, option 1 recovers dependencies and rebuilds the frontend; option 2 remains the explicit install/update and rebuild path.

When `FAIRS_DATA_DIR` is absent, the application uses `app/resources`.

## Related Files

- Read `modes.md` for the runtime surfaces these settings affect.
- Read `../architecture/persistence.md` for the storage consequences of database configuration.
