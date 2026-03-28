# FAIRS Architecture

FAIRS is a FastAPI + React/Vite application for roulette training and inference workflows, with optional Windows desktop packaging through Tauri.

## 1. Repository Layout

- `FAIRS/server`: backend APIs, domain logic, training/inference orchestration, persistence.
- `FAIRS/client`: React + TypeScript frontend (Vite).
- `FAIRS/settings`: runtime configuration (`.env`, profile examples, `configurations.json`).
- `FAIRS/resources`: runtime data (`checkpoints`, `database.db`, `logs`).
- `runtimes`: portable Python/uv/Node runtimes and project virtualenv.
- `release/tauri`: desktop build and export helpers.
- `tests`: Python unit and E2E test suites.

## 2. Runtime Topology

### Local webapp mode

- Entry point: `FAIRS/start_on_windows.bat`.
- Backend: `uvicorn FAIRS.server.app:app` on `FASTAPI_HOST:FASTAPI_PORT`.
- Frontend: Vite preview on `UI_HOST:UI_PORT`.
- Frontend calls backend through `/api/*`.

### Desktop packaged mode (Tauri)

- Build helper: `release/tauri/build_with_tauri.bat`.
- Tauri resolves/stages runtime workspace, ensures `runtimes/.venv`, then starts local Uvicorn.
- Tauri sets `FAIRS_TAURI_MODE=true` for packaged runtime behavior.
- Window opens `http://127.0.0.1:<FASTAPI_PORT>/` after backend readiness.

## 3. Backend Architecture

### Entry point

- `FAIRS/server/app.py` creates FastAPI app and mounts routers from:
  - `FAIRS/server/api/upload.py` (`/data`)
  - `FAIRS/server/api/training.py` (`/training`)
  - `FAIRS/server/api/database.py` (`/database`)
  - `FAIRS/server/api/inference.py` (`/inference`)

Routes are always exposed under `/api/*`. They are also exposed directly (without `/api`) when `FAIRS_ALLOW_DIRECT_API_ROUTES=true`.

### Layers

1. API layer: `FAIRS/server/api` (request mapping, responses, HTTP status handling).
2. Services layer: `FAIRS/server/services` (job manager, dataset import helpers).
3. Domain layer: `FAIRS/server/domain` (request/response models and job/domain state).
4. Learning layer: `FAIRS/server/learning` (training, inference, model artifacts).
5. Persistence layer: `FAIRS/server/repositories` (database initialization, queries, serializers, schema models).
6. Configuration layer: `FAIRS/server/configurations` (env + JSON settings resolution).

### API surface (current)

- Data upload:
  - `POST /data/upload`
- Training:
  - `POST /training/start`
  - `POST /training/resume`
  - `GET /training/status`
  - `POST /training/stop`
  - `GET /training/checkpoints`
  - `GET /training/checkpoints/{checkpoint}/metadata`
  - `DELETE /training/checkpoints/{checkpoint}`
  - `GET /training/jobs/{job_id}`
  - `DELETE /training/jobs/{job_id}`
- Database:
  - `GET /database/roulette-series/datasets`
  - `GET /database/roulette-series/datasets/summary`
  - `DELETE /database/roulette-series/datasets/{dataset_id}`
- Inference:
  - `POST /inference/sessions/start`
  - `POST /inference/sessions/{session_id}/next`
  - `POST /inference/sessions/{session_id}/step`
  - `POST /inference/sessions/{session_id}/bet`
  - `POST /inference/sessions/{session_id}/shutdown`
  - `POST /inference/sessions/{session_id}/rows/clear`
  - `POST /inference/context/clear`

## 4. Frontend Architecture

- Root composition in `FAIRS/client/src/App.tsx`.
- Global app state provider: `FAIRS/client/src/context/AppStateContext.tsx`.
- Main layout shell: `FAIRS/client/src/components/Layout/MainLayout.tsx`.
- Active pages:
  - `/training` -> `pages/Training/TrainingPage.tsx`
  - `/inference` -> `pages/Inference/InferencePage.tsx`

## 5. Persistence Model

Primary tables:

- `datasets`
- `dataset_outcomes`
- `inference_sessions`
- `inference_session_steps`
- `roulette_outcomes`

Main ORM definitions live in `FAIRS/server/repositories/schemas/models.py`.
`DataSerializer` in `FAIRS/server/repositories/serialization/data.py` owns most dataset/session persistence workflows.

## 6. Packaged SPA Behavior

When `FAIRS_TAURI_MODE=true` and `FAIRS/client/dist` exists:

- FastAPI serves SPA root at `/`.
- `/assets` is served from `FAIRS/client/dist/assets`.
- Unknown frontend paths fall back to `index.html`.
- If packaged SPA is unavailable, `/` falls back to docs redirect when docs are enabled.

## 7. Extension Points

- New API domain: add module in `FAIRS/server/api`, wire it in `FAIRS/server/app.py`, then add service/repository support as needed.
- New long-running workflow: integrate with `FAIRS/server/services/jobs.py` and follow `BACKGROUND_JOBS.md` patterns.
- New frontend page: register route in `FAIRS/client/src/App.tsx` and update layout navigation.
- New runtime mode/package behavior: update `PACKAGING_AND_RUNTIME_MODES.md` and README in the same change.
