## Configuration

Last updated: 2026-09-18

## Configuration Ownership

FAIRS uses three distinct configuration surfaces with non-overlapping responsibilities:

1. `settings/.env` for deployment/runtime environment values such as hosts, ports, storage location, database connection, backend visibility, API docs, reload behavior, and ML backend selection.
2. `<data-root>/runtime-settings.json` for the application-wide settings exposed by the Settings UI/API. It owns job polling, global JIT/compiler behavior, roulette outcome-pool rules, and roulette rendering preferences.
3. `TrainingConfig` in `app/server/contracts/training.py` for all per-training defaults, semantic constraints, dataset choices, model parameters, device selection, and mixed precision.

No setting should be independently defaulted in more than one of these surfaces.

## Environment Variables

The runtime consumes these environment keys:

- `FASTAPI_HOST`
- `FASTAPI_PORT`
- `UI_HOST`
- `UI_PORT`
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

For launcher operations, the following values must be explicitly present and non-empty in `.env`: `FASTAPI_HOST`, `FASTAPI_PORT`, `UI_HOST`, `UI_PORT`, `RELOAD`, and `EMBEDDED_DATABASE`. An existing stale `.env` that omits them fails with an actionable message instead of silently inheriting compatibility defaults.

`FAIRS_DATA_DIR` may be empty. An empty value means the normal `app/resources` data root.

## Internal Runtime Settings

The launcher sets only execution-scoped tool variables:

- `UV_PROJECT_ENVIRONMENT` targets `app/server/.venv`.
- `FAIRS_CACHE_DIR`, `UV_CACHE_DIR`, `NPM_CONFIG_CACHE`, `PIP_CACHE_DIR`, `PYTHONPYCACHEPREFIX`, `PYTEST_CACHE_DIR`, `PYTEST_BASETEMP_DIR`, `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `COVERAGE_FILE`, and `PLAYWRIGHT_BROWSERS_PATH` are rooted below `runtimes/cache`.
- `KERAS_HOME`, `TORCH_HOME`, `TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR`, `MPLCONFIGDIR`, `XDG_CACHE_HOME`, and `CUDA_CACHE_PATH` are also rooted below `runtimes/cache` so normal application execution does not fall back to user-profile or system temporary cache locations.

This cache root is canonical. The launcher does not scan the repository for historical or alternate cache locations. `FAIRS_DATA_DIR` is rejected when it overlaps `runtimes/cache`.

## Runtime Settings File

The runtime settings file is `<FAIRS_DATA_DIR>/runtime-settings.json` when `FAIRS_DATA_DIR` is configured; otherwise it is `app/resources/runtime-settings.json`. It is created on startup when absent and is ignored by source control because it is local user state.

Startup resolution is strict and deterministic:

- An existing runtime file is parsed and validated. Malformed or invalid content fails startup.
- When the runtime file is absent, the validated defaults are written to the runtime path.
- Existing runtime files that predate the `roulette` block remain valid. Missing roulette fields resolve to the current backend defaults and are persisted on the next settings write.

Writes use a same-directory temporary file, flush and `fsync`, then `os.replace` so readers see either the previous complete document or the new complete document. The Settings API merges strict partial updates, validates the complete merged document, persists the runtime file, and applies live technical settings to the running application. It does not read or write `.env`, the database, or `TrainingConfig`.

Enabling `device.jit_compile` also runs a runtime capability preflight. The bundled Python 3.14 runtime supports the setting when the installed PyTorch exposes `torch.compile`; on Windows, use the `eager` backend because `inductor` requires Triton and is rejected before persistence. Training start and the worker boundary repeat the guard for older or manually edited runtime files; no silent compiler fallback is used.

## Database Configuration

Database configuration is accepted only from the environment model so connection ownership is unambiguous.

For external PostgreSQL mode, `DATABASE_ENGINE` must be `postgresql+psycopg`. Legacy aliases such as `postgres`, `postgresql`, and `postgresql+psycopg2` are rejected rather than normalized.

- `EMBEDDED_DATABASE=true` selects SQLite.
- `EMBEDDED_DATABASE=false` selects PostgreSQL and requires valid connection settings.

Both modes use the same SQLAlchemy repositories and Alembic schema.

## Structured Settings

The runtime settings document owns:

- `jobs.polling_interval`
- `device.jit_compile`
- `device.jit_backend`
- `roulette.minimum_number`, default `0`
- `roulette.maximum_number`, default `36`
- `roulette.exclude_zero`, default `false`
- `roulette.invert_colors`, default `false`
- `roulette.show_number_labels`, default `true`

Roulette range values are inclusive and must stay between `0` and `36`. The minimum cannot exceed the maximum, and excluding zero cannot leave an empty number pool.

`minimum_number`, `maximum_number`, and `exclude_zero` affect the actual outcome pool used by newly generated synthetic training data. Stored training outcomes outside the configured pool are filtered before a new training run starts. Live inference observations are rejected at the API boundary when they fall outside the current pool. The canonical model action space remains unchanged, so existing checkpoints keep their expected output dimensions and betting semantics.

`invert_colors` is visual only. It swaps red and black slice rendering while leaving zero green and does not alter canonical roulette color features, reward rules, or red/black betting semantics. `show_number_labels` controls whether numeric labels are drawn on newly rendered roulette wheel frames.

Global mixed precision is intentionally not present. `use_mixed_precision`, `use_device_gpu`, and `device_id` are per-training values owned by `TrainingConfig`.

## Training Configuration

`TrainingConfig` is the canonical owner of training defaults and cross-field semantic validation. The frontend obtains generated default values from `app/client/src/generated/api.ts`, which is derived from the Pydantic model by `app/scripts/generate_frontend_contracts.py`.

The training wizard may provide presentation-level input constraints, but it does not maintain a second implementation of semantic rules. Submission validation goes through `POST /api/training/validate`, using the same Pydantic contract that starts the training run.

## Lifecycle and Worker Contract

- FastAPI construction remains import-safe. Runtime bootstrap and mutable environment loading occur in lifespan startup.
- `WEB_CONCURRENCY`, `UVICORN_WORKERS`, and `FAIRS_WORKERS` must be unset or exactly `1` because live jobs and inference models are process-local.
- `RELOAD=true` is development-only and expires process-local training/inference state when the process reloads.
- The backend creates timestamped `FAIRS_*.log` files under the active data root.
- Settings changes update future parent polling immediately. A newly started worker reads the current roulette settings and receives the current polling and JIT launch snapshot; an active worker keeps the values captured when it started. Resuming a checkpoint uses the current runtime settings while preserving the checkpoint's model configuration.
- Live inference step validation reads the current roulette number-pool settings, so changing the range or zero exclusion affects subsequent observations in the same application session without a restart.

## Related Files

- Read `startup.md` for launcher behavior.
- Read `../architecture/backend_api.md` for the Settings endpoints.
- Read `../architecture/persistence.md` for database and checkpoint consequences.
- Read `../architecture/backend_api.md` for generated transport contracts.
