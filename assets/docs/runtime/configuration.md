## Configuration

Last updated: 2026-06-02

## Environment Variables

The runtime scripts and backend consume these environment keys:

- `FASTAPI_HOST`
- `FASTAPI_PORT`
- `UI_HOST`
- `UI_PORT`
- `ENABLE_API_DOCS`
- `RELOAD`
- `OPTIONAL_DEPENDENCIES`
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

## Internal Runtime Flags

- `FAIRS_TAURI_MODE=true`
  - injected by the desktop runtime when spawning the backend
- `UV_PROJECT_ENVIRONMENT`
  - set by startup and build scripts to target the runtime virtual environment

## Structured Settings

`settings/configurations.json` contains non-env technical settings such as:

- `jobs.polling_interval`
- device-related options such as JIT and mixed-precision defaults

## Behavior Differences Driven By Configuration

### API Docs

- `ENABLE_API_DOCS` controls whether `/docs`, `/redoc`, and OpenAPI routes are mounted.

### Database Mode

- `EMBEDDED_DATABASE=true`
  - uses SQLite and can auto-initialize the embedded database file
- `EMBEDDED_DATABASE=false`
  - uses PostgreSQL and requires explicit configuration plus manual initialization

### Desktop Runtime

- `FAIRS_TAURI_MODE=true` requires a built frontend at `app/client/dist/index.html`.
- Desktop startup injects backend process environment values such as `MPLBACKEND` and `KERAS_BACKEND`.

## Related Files

- Read `modes.md` for the runtime surfaces these settings affect.
- Read `../architecture/persistence.md` for the storage consequences of database configuration.
