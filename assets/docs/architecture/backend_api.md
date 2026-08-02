## Backend API

Last updated: 2026-08-02

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
  - returns `status`, `application`, `version`, and `mode`.
  - reports `development` by default and `desktop` only when `FAIRS_TAURI_MODE=true`; no packaged desktop runtime is shipped by this repository.

## Non-API Routes

- When `app/client/dist/index.html` exists, the backend serves the built SPA from `/`.
- When no built frontend is available, `/` redirects to `/docs` if API docs are enabled.
- Static SPA assets are mounted from `/assets` when the frontend build exists.

## API Design Notes

- Endpoints use explicit domain identifiers such as `job_id` and `session_id`.
- Training start and resume requests return `202 Accepted` because work is tracked as a background job.
- Upload, dataset, checkpoint, inference, and job-management operations return `200 OK` on success unless a documented validation or conflict error applies.
- HTTP handlers validate and marshal payloads at the API boundary, then delegate orchestration to services.
- API docs exposure is controlled by `ENABLE_API_DOCS`.

## Related Files

- Read `execution_and_data_flow.md` for endpoint-to-service chains.
- Read `../../runtime/configuration.md` for the flags that change API visibility and backend behavior.
