## Configuration

Last updated: 2026-08-20

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
- `DATABASE_URL`
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

## Internal Runtime Settings

- `UV_PROJECT_ENVIRONMENT`
  - set by the launcher to target the runtime virtual environment
- `FAIRS_DATA_DIR`
  - overrides the mutable database, logs, and checkpoints directory
- `FAIRS_LOG_DIR`
  - overrides the log directory; primarily useful for isolated test runs
- `FAIRS_TAURI_MODE`
  - marks the health response as `desktop` and requires a built frontend, but does not provide packaging

For external PostgreSQL mode, `DATABASE_ENGINE` must be `postgresql+psycopg`. Legacy aliases such as `postgres`, `postgresql`, and `postgresql+psycopg2` are rejected during startup validation.

The backend creates timestamped `FAIRS_*.log` files in `FAIRS_LOG_DIR` when set, or in the active data `logs` directory otherwise.

The application entry point calls `server.bootstrap.bootstrap_runtime()` explicitly before importing Keras-backed application modules. Direct imports of `server`, common path helpers, and logging helpers do not load `.env`, resolve mutable paths from the environment, create directories, or configure the global logging tree.

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
  - uses SQLite and creates the embedded database file only when it is missing
  - validates an existing database structurally during normal startup without resetting or migrating it
  - records SQLite schema version `1` during explicit schema creation; a newer unsupported version stops startup
- `EMBEDDED_DATABASE=false`
  - uses PostgreSQL and requires explicit connection settings
  - requires launcher option 4 to create or initialize the database and schema
  - normal startup probes the existing database connection and validates the required table/column structure

### Backend Log Visibility

- `BACKEND_LOGS_VISIBLE=false` starts the backend detached and hidden.
- `BACKEND_LOGS_VISIBLE=true` opens a dedicated backend terminal so logs remain visible.
- When `BACKEND_LOGS_VISIBLE` is absent, the launcher defaults to `true`.

### Dependency Installation And Frontend Build

- The launcher checks runtime readiness before installing dependencies.
- The checked-in `settings/.env.example` template defaults to API port `8890` and UI port `8051`; override them in `settings/.env` when needed.
- Launcher option 2 selects `Standard` or `Development` installation, installs dependencies, and rebuilds the frontend; `Development` adds the backend's test extra.
- Normal application startup skips installation and rebuilding when the environment and frontend build are ready. If either is missing or unusable, option 1 recovers dependencies and rebuilds the frontend; option 2 remains the explicit install/update and rebuild path.

When `FAIRS_DATA_DIR` is absent, the application uses `app/resources`.

## Related Files

- Read `modes.md` for the runtime surfaces these settings affect.
- Read `../architecture/persistence.md` for the storage consequences of database configuration.
