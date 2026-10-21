## Backend API

Last updated: 2026-10-21

## Mounting Model

- `app/server/app.py` mounts all routers with the shared `/api` prefix.
- Routers are defined in `app/server/api` and delegate application work to services.
- Request and response schemas are Pydantic models in `app/server/contracts`.
- FastAPI/Pydantic is the canonical HTTP contract authority. There is no checked-in OpenAPI snapshot acting as a second stored contract.
- No WebSocket routes are implemented. Long-running training is polled through job/status endpoints.

## Upload Endpoints

Router prefix: `/data`

- `POST /api/data/upload`

## Training Endpoints

Router prefix: `/training`

- `POST /api/training/validate`
- `POST /api/training/start`
- `POST /api/training/resume`
- `GET /api/training/status`
- `POST /api/training/stop`
- `GET /api/training/checkpoints`
- `GET /api/training/checkpoints/{checkpoint}/metadata`
- `DELETE /api/training/checkpoints/{checkpoint}`
- `GET /api/training/jobs/{job_id}`
- `DELETE /api/training/jobs/{job_id}`

`POST /api/training/validate` validates the same `TrainingConfig` contract used by training start, checks runtime capability, verifies that a selected stored dataset still exists as a training dataset, and rejects an already-used output checkpoint name. `/api/training/start` repeats the resource preflight before registering a job. Missing datasets return `404`, occupied checkpoint names return `409`, and invalid configuration fields return `422`. Validation is read-only. The frontend does not maintain an independent copy of semantic training validation rules.

## Dataset Endpoints

Router prefix: `/datasets`

- `GET /api/datasets/training`
- `GET /api/datasets/training/summary`
- `DELETE /api/datasets/training/{dataset_id}`

## Inference Endpoints

Router prefix: `/inference`

- `POST /api/inference/sessions/start`
- `GET /api/inference/sessions/{session_id}`
- `POST /api/inference/sessions/{session_id}/next`
- `POST /api/inference/sessions/{session_id}/step`
- `POST /api/inference/sessions/{session_id}/shutdown`
- `POST /api/inference/sessions/{session_id}/bet`
- `POST /api/inference/sessions/{session_id}/rows/clear`
- `POST /api/inference/context/clear`

`GET /api/inference/sessions/{session_id}` returns the authoritative live-session snapshot plus persisted step history. A `404` after a backend restart means the in-memory player is gone. Persisted history is not treated as a rehydratable live model session.

`POST /api/inference/sessions/{session_id}/step` validates the submitted extraction against the current roulette runtime number pool before it reaches the live player. Changes to the configured minimum, maximum, or zero exclusion therefore apply to subsequent observations in an existing application session.

Prediction preference is exposed as `relative_preference`. This is the softmax-normalized relative preference of the DQN action scores, not a calibrated probability of success. The superseded `confidence` name is not accepted or returned.

## Settings Endpoints

Router prefix: `/settings`

- `GET /api/settings` returns the current validated user preferences.
- `PATCH /api/settings` accepts a strict partial update for `jobs`, `device`, and `roulette` settings. The Settings UI sends valid changes automatically; its continuous numeric and text inputs are debounced.
- `POST /api/settings/reset` restores the validated backend defaults.

The roulette settings contract exposes `minimum_number`, `maximum_number`, `exclude_zero`, `invert_colors`, and `show_number_labels`. Number limits are inclusive, bounded to `0..36`, and validated after partial patches are merged with the existing document. The combination `minimum_number=0`, `maximum_number=0`, and `exclude_zero=true` is rejected because it would create an empty outcome pool.

The Settings endpoints persist to the `application_settings` row in the active database through `SettingsService`. Each accepted partial update is committed before it is propagated to live services; a propagation failure restores the previous row and service values. Nested unknown fields, invalid roulette ranges, out-of-range polling values, empty JIT backend values, API targets, listener ports, CORS origins, database configuration, environment values, and per-training `TrainingConfig` fields are rejected. API target, listener hosts and ports, and CORS origins are supplied through `settings/.env`; the application API route paths remain fixed at `/api`. Enabling JIT also requires runtime capability support; the supported Python 3.14 launcher runtime accepts it when `torch.compile` is available, while Windows rejects the `inductor` backend because Triton is unavailable. Job and device changes are propagated to the live `TrainingService`; roulette rules are read from the same persisted row when new training data is prepared and when live inference steps are validated.

## Database Configuration Endpoints

Router prefix: `/settings/database`

- `GET /api/settings/database` returns the saved connection configuration with the password redacted, active backend, lifecycle status, and a recovery message when applicable.
- `POST /api/settings/database/test` tests a candidate connection without activating it or saving its settings.
- `PUT /api/settings/database` validates connectivity and schema, drains in-flight database operations, loads the target database's Settings row, then activates the connection. It returns `409` while training or inference is active and `400` when the candidate cannot be initialized or activated. Failed activation restores the previous backend.

Supported backends are SQLite and PostgreSQL through `postgresql+psycopg`. Blank PostgreSQL passwords retain the saved credential; the explicit clear flag removes it. Password values are never returned by API responses. Switching does not copy settings or application data between databases.

## System Endpoints

- `GET /api/health` returns `HealthResponse` with `status`, `application`, and `version`. `status` is `recovery` when database startup failed but the configuration recovery surface is available.
- During recovery, database-backed API requests return `503` until a working database is applied; database configuration and health routes remain available.

## Non-API Routes

- When `app/client/dist/index.html` exists, the backend serves the built SPA from `/`.
- Without a built frontend, `/` redirects to `/docs` when API docs are enabled.
- Without a built frontend and with API docs disabled, `/` returns `{ "status": "ok" }` through `RootStatusResponse`.
- Static SPA assets are mounted from `/assets` when the frontend build exists.

## API Design Notes

- Resource identifiers such as `job_id` and `session_id` are explicit.
- `POST /api/inference/sessions/start` accepts `checkpoint`, numeric `dataset_id`, `game_capital`, and `game_bet`. Strategy behavior comes from the checkpoint configuration.
- `X-Preserve-Inference-Session` is retained only for transactional client-side session replacement during replay. The existing session remains authoritative until replacement succeeds.
- Training start and resume return `202 Accepted` because work is tracked as a background job.
- Dataset deletion returns `409 Conflict` when checkpoint metadata references the dataset or cannot be safely inspected.
- Inference context clearing returns `409 Conflict` while a live inference session exists.
- API modules do not access SQLAlchemy, checkpoint files, or learning models directly.
- API docs exposure is controlled by `ENABLE_API_DOCS`.

## Derived Frontend Contract

`app/client/src/generated/api.ts` is a generated transport artifact, not an independent contract source. `app/scripts/generate_frontend_contracts.py` derives it from the live FastAPI/Pydantic schema and also exports frontend defaults from the corresponding Pydantic request models.

Regenerate it from repository root with:

```powershell
$env:PYTHONPATH='app'
uv --project app/server run python app/scripts/generate_frontend_contracts.py
```

CI verifies that the checked-in generated TypeScript matches the runtime backend contract:

```powershell
$env:PYTHONPATH='app'
uv --project app/server run python app/scripts/generate_frontend_contracts.py --check
```

OpenAPI itself remains runtime-derived. `app/scripts/export_openapi.py` prints it to stdout or writes it to an explicitly supplied `--output` path when an external artifact is required.

## Related Files

- Read `execution_and_data_flow.md` for endpoint-to-service chains.
- Read `persistence.md` for database and checkpoint persistence.
- Read `../runtime/configuration.md` for flags that change runtime behavior.
