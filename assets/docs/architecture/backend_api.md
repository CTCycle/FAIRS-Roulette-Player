## Backend API

Last updated: 2026-08-20

## Mounting Model

- `app/server/app.py` mounts all routers with the shared `/api` prefix.
- Routers are defined in:
  - `app/server/api/upload.py`
  - `app/server/api/training.py`
  - `app/server/api/datasets.py`
  - `app/server/api/inference.py`
  - `app/server/api/system.py`
- No WebSocket routes are currently implemented in `app/server/api`; long-running training is polled through job/status endpoints.

## Upload Endpoints

Router prefix: `/data`

- `POST /api/data/upload`

## Training Endpoints

Router prefix: `/training`

- `POST /api/training/start`
- `POST /api/training/resume`
- `GET /api/training/status`
- `POST /api/training/stop`
- `GET /api/training/checkpoints`
- `GET /api/training/checkpoints/{checkpoint}/metadata`
- `DELETE /api/training/checkpoints/{checkpoint}`
- `GET /api/training/jobs/{job_id}`
- `DELETE /api/training/jobs/{job_id}`

## Dataset Endpoints

Router prefix: `/datasets`

- `GET /api/datasets/training`
- `GET /api/datasets/training/summary`
- `DELETE /api/datasets/training/{dataset_id}`

## Inference Endpoints

Router prefix: `/inference`

- `POST /api/inference/sessions/start`
- `POST /api/inference/sessions/{session_id}/next`
- `POST /api/inference/sessions/{session_id}/step`
- `POST /api/inference/sessions/{session_id}/shutdown`
- `POST /api/inference/sessions/{session_id}/bet`
- `POST /api/inference/sessions/{session_id}/rows/clear`
- `POST /api/inference/context/clear`

## System Endpoints

- `GET /api/health`
  - returns a typed `HealthResponse` with `status`, `application`, `version`, and `mode`.
  - reports `development` by default and `desktop` only when `FAIRS_TAURI_MODE=true`; no packaged desktop runtime is shipped by this repository.

## Non-API Routes

- When `app/client/dist/index.html` exists, the backend serves the built SPA from `/`.
- When no built frontend is available, `/` redirects to `/docs` if API docs are enabled.
- When no built frontend is available and API docs are disabled, `/` returns the typed `RootStatusResponse` payload `{ "status": "ok" }`.
- Static SPA assets are mounted from `/assets` when the frontend build exists.

## API Design Notes

- Endpoints use explicit resource identifiers such as `job_id` and `session_id`.
- Training start and resume requests return `202 Accepted` because work is tracked as a background job.
- Upload, dataset, checkpoint, inference, and job-management operations return `200 OK` on success unless a documented validation or conflict error applies.
- `DELETE /api/datasets/training/{dataset_id}` returns `409 Conflict` when checkpoint metadata still references the dataset; the successful response contract and route are unchanged.
- HTTP handlers validate and marshal payloads using `app/server/contracts/*` at the API boundary, then delegate orchestration to services.
- API modules do not access SQLAlchemy, checkpoint files, or learning models directly; those concerns remain behind services and their collaborators.
- API docs exposure is controlled by `ENABLE_API_DOCS`.

## Shared Contract

- The checked-in runtime contract is `app/shared/openapi.json`.
- Regenerate it from the FastAPI application in PowerShell with `$env:PYTHONPATH='app'; & '.\\app\\server\\.venv\\Scripts\\python.exe' '.\\app\\scripts\\export_openapi.py'`.
- CI runs the same exporter in check mode and fails when the snapshot differs from `app.openapi()`.

## Related Files

- Read `execution_and_data_flow.md` for endpoint-to-service chains.
- Read `../../runtime/configuration.md` for the flags that change API visibility and backend behavior.
- Read `findings_and_remediation.md` for the API boundary assessment and incremental remediation priorities.
