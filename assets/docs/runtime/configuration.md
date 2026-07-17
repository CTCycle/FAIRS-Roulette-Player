## Configuration

Last updated: 2026-07-11

## Environment Variables

The runtime scripts and backend consume these environment keys:

- `FASTAPI_HOST`
- `FASTAPI_PORT`
- `UI_HOST`
- `UI_PORT`
- `BACKEND_LOGS_VISIBLE`
- `ENABLE_API_DOCS`
- `RELOAD`
- `OPTIONAL_DEPENDENCIES`
- `ALWAYS_REBUILD`
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
- `FAIRS_USER_DATA_DIR`
  - overrides the mutable database, logs, and checkpoints directory
- `FAIRS_LOG_DIR`
  - overrides the log directory; primarily useful for isolated test runs

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
  - uses SQLite and can auto-initialize the embedded database file
- `EMBEDDED_DATABASE=false`
  - uses PostgreSQL and requires explicit configuration plus manual initialization

### Backend Log Visibility

- `BACKEND_LOGS_VISIBLE=false` starts the backend detached and hidden.
- `BACKEND_LOGS_VISIBLE=true` opens a dedicated backend terminal so logs remain visible.
- When `BACKEND_LOGS_VISIBLE` is absent, the launcher defaults to `true`.

### Frontend Build

- `ALWAYS_REBUILD=true` rebuilds the frontend whenever the application starts.
- `ALWAYS_REBUILD=false` skips the frontend build at application startup.

When `FAIRS_USER_DATA_DIR` is absent, the application uses `app/resources`.

## Related Files

- Read `modes.md` for the runtime surfaces these settings affect.
- Read `../architecture/persistence.md` for the storage consequences of database configuration.
