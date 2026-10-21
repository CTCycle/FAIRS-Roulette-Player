## Configuration

Last updated: 2026-10-21

## Configuration Ownership

FAIRS uses three distinct configuration surfaces:

1. `settings/.env` contains process and deployment values such as host and port, data directory, API docs, reload behavior, and ML backend selection. It contains no database connection settings.
2. `<data-root>/database-config.json` contains only the selected database backend and its connection parameters. It is independent of the database so startup can locate the database before opening it.
3. The active database's singleton `application_settings` row contains the Settings UI preferences: job polling, global JIT/compiler behavior, and roulette pool and display preferences. A missing row is seeded with current defaults; old settings files are ignored.

`TrainingConfig` in `app/server/contracts/training.py` owns per-training defaults, semantic constraints, dataset choices, model parameters, device selection, and mixed precision. No setting is independently defaulted in more than one canonical surface.

## Environment Variables

The runtime consumes these environment keys:

- `FASTAPI_HOST`, `FASTAPI_PORT`, `UI_HOST`, and `UI_PORT`
- `ENABLE_API_DOCS`, `RELOAD`, and `FAIRS_DATA_DIR`
- `MPLBACKEND` and `KERAS_BACKEND`
- `WEB_CONCURRENCY`, `UVICORN_WORKERS`, and `FAIRS_WORKERS`

`settings/.env.example` is the canonical template. The Windows launcher copies it only when `.env` does not exist. It does not overlay defaults on an existing file. The launcher requires `FASTAPI_HOST`, `FASTAPI_PORT`, `UI_HOST`, `UI_PORT`, and `RELOAD`; database selection is read from `database-config.json`, not `.env`.

`FAIRS_DATA_DIR` may be empty, which selects the normal `data` directory. A configured path selects the persistent data root and must not overlap `runtimes/cache`.

The launcher sets execution-scoped cache paths below `runtimes/cache`, including `FAIRS_CACHE_DIR`, `UV_CACHE_DIR`, `NPM_CONFIG_CACHE`, `PIP_CACHE_DIR`, `PYTHONPYCACHEPREFIX`, `PYTEST_CACHE_DIR`, `PYTEST_BASETEMP_DIR`, `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `COVERAGE_FILE`, `PLAYWRIGHT_BROWSERS_PATH`, `KERAS_HOME`, `TORCH_HOME`, `TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR`, `MPLCONFIGDIR`, `XDG_CACHE_HOME`, and `CUDA_CACHE_PATH`.

## Database Configuration File

The connection configuration is `<FAIRS_DATA_DIR>/database-config.json`, or `data/database-config.json` when `FAIRS_DATA_DIR` is empty. Its versioned, strict schema stores only:

- SQLite: the database file path and insert batch size.
- PostgreSQL: the `postgresql+psycopg` driver, host, port, database name, username, password credential, SSL and optional CA path, connection timeout, and insert batch size.

The file is written through a same-directory temporary file, flushed and synchronized, then atomically replaced. Unknown fields, unsupported versions, malformed JSON, or undecryptable credentials enter recovery mode; startup does not fall back to environment values or silently choose SQLite. PostgreSQL passwords are protected with Windows DPAPI for the current user and are never returned by the API or written to logs. A blank password retains the saved credential; the explicit clear action removes it. Moving the file to another Windows account or machine requires entering the password again.

The Database section in Settings supports SQLite and PostgreSQL. `GET /api/settings/database` returns redacted status, `POST /api/settings/database/test` checks a candidate without activating it, and `PUT /api/settings/database` validates and applies it. The default SQLite path is `<data-root>/database.db`.

If `database-config.json` is absent, startup writes the current default SQLite configuration. Database values in `settings/.env` and inherited process environment variables are not read. Obsolete database keys and secrets are removed from `settings/.env` while unrelated entries are preserved. A present but invalid `database-config.json` fails closed and remains available for correction.

## Database-Backed Application Settings

The active database owns all Settings UI values in `application_settings` (singleton id `1`), with validated `jobs`, `device`, and `roulette` objects. Alembic baseline `0001_current_schema` creates this table. Empty databases receive backend defaults. A database without a row receives current defaults; switching to another database never copies settings or application data.

`GET /api/settings`, `PATCH /api/settings`, and `POST /api/settings/reset` read and write only the active database. The Settings page automatically sends each valid change, debouncing numeric and text inputs. The minimum, maximum, and zero-inclusion controls are validated as one range; while that draft is invalid, its pending range patch is removed and no range request is sent. Partial updates merge with the current validated row and are applied to live services after persistence succeeds. A failed write or live propagation keeps the edited value visible with an error; a failed live propagation restores the previous row and service values.

Live switching is supported when training and inference are idle. Database edits remain a local draft until the user confirms **Apply and switch**. The connection test does not activate or save the candidate. FAIRS initializes or validates the target schema through Alembic, loads and validates that database's settings, drains in-flight API database operations, then activates the new connection and stores its configuration file. Failures roll back to the previous backend and keep its configuration. Each database remains an independent data store. Changes to `FAIRS_DATA_DIR`, listener addresses or ports, and other process-startup settings still require a restart.

When the saved database cannot be parsed, decrypted, connected, or initialized, the frontend and Database settings API remain available in recovery mode. Health reports `recovery`; database-backed APIs return `503` until a valid backend is applied.

## Settings UI Values

The application-settings row owns:

- `jobs.polling_interval`
- `device.jit_compile` and `device.jit_backend`
- `roulette.minimum_number`, default `0`
- `roulette.maximum_number`, default `36`
- `roulette.exclude_zero`, default `false`
- `roulette.invert_colors`, default `false`
- `roulette.show_number_labels`, default `true`

Roulette limits are inclusive and bounded to `0..36`. The minimum cannot exceed the maximum, and excluding zero cannot leave an empty number pool. Number-pool settings affect newly prepared training data and live inference validation. Color inversion and number labels are visual settings only.

Global mixed precision is not present. `use_mixed_precision`, `use_device_gpu`, and `device_id` are per-training values owned by `TrainingConfig`.

Enabling `device.jit_compile` runs a runtime capability preflight. The supported Windows runtime accepts the setting when the installed PyTorch exposes `torch.compile`; on Windows, use `eager` because `inductor` requires Triton. No silent compiler fallback is used.

## Lifecycle and Worker Contract

- FastAPI construction is import-safe. Environment loading, configuration recovery, and database initialization occur during lifespan startup.
- `WEB_CONCURRENCY`, `UVICORN_WORKERS`, and `FAIRS_WORKERS` must be unset or exactly `1` because jobs and inference models are process-local.
- `RELOAD=true` is development-only and discards process-local training and inference state on reload.
- The backend creates timestamped `FAIRS_*.log` files below the active data root.
- Polling changes affect future parent polling immediately. A worker receives the current polling, JIT, and roulette settings when it starts; an active worker keeps its captured settings. Live inference uses current roulette number-pool settings for subsequent observations.

## Related Files

- Read `startup.md` for launcher behavior.
- Read `../architecture/backend_api.md` for the Settings and database endpoints.
- Read `../architecture/persistence.md` for schema and migration behavior.
