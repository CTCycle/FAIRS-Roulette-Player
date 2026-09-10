## Backend API

Last updated: 2026-09-10

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

`POST /api/training/validate` validates the same `TrainingConfig` contract used by training start. The frontend does not maintain an independent copy of semantic training validation rules.

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

Prediction preference is exposed as `relative_preference`. This is the softmax-normalized relative preference of the DQN action scores, not a calibrated probability of success. The superseded `confidence` name is not accepted or returned.

## System Endpoints

- `GET /api/health` returns `HealthResponse` with `status`, `application`, and `version`.

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
