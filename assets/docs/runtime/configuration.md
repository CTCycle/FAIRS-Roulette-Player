## Configuration

Last updated: 2026-08-18

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
  - does not cross-validate an existing database during normal startup
- `EMBEDDED_DATABASE=false`
  - uses PostgreSQL and requires explicit connection settings
  - requires launcher option 3 to create or initialize the database and schema
  - normal startup only probes the existing database connection

### Backend Log Visibility

- `BACKEND_LOGS_VISIBLE=false` starts the backend detached and hidden.
- `BACKEND_LOGS_VISIBLE=true` opens a dedicated backend terminal so logs remain visible.
- When `BACKEND_LOGS_VISIBLE` is absent, the launcher defaults to `true`.

### Dependency Installation And Frontend Build

- The launcher checks runtime readiness before installing dependencies.
- Launcher option 2 selects `Standard` or `Development` installation, installs dependencies, and rebuilds the frontend; `Development` adds the backend's test extra.
- Normal application startup may install missing dependencies, but it does not rebuild the frontend. Run option 2 when a frontend build is required.

When `FAIRS_DATA_DIR` is absent, the application uses `app/resources`.

## Related Files

- Read `modes.md` for the runtime surfaces these settings affect.
- Read `../architecture/persistence.md` for the storage consequences of database configuration.
