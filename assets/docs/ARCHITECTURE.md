# FAIRS Architecture

Last updated: 2026-04-13

FAIRS is a FastAPI + React/Vite application for roulette training and inference workflows, with optional Windows desktop packaging through Tauri.

## 1. Repository Layout

- `FAIRS/server`: backend APIs, job orchestration, training/inference domain logic, persistence.
- `FAIRS/client`: React + TypeScript frontend (Vite).
- `FAIRS/settings`: runtime/process config (`.env`, `.env.example`) and backend JSON config (`configurations.json`).
- `FAIRS/resources`: runtime data (`checkpoints`, `database`, `logs`).
- `runtimes`: portable Python/uv/Node runtimes and project virtualenv (`runtimes/.venv`).
- `release/tauri`: desktop build/export scripts.
- `tests`: Python unit and E2E/API suites.

## 2. Runtime Topology

### Local web mode

- Entry point: `FAIRS/start_on_windows.bat`.
- Backend: `uvicorn FAIRS.server.app:app` on `FASTAPI_HOST:FASTAPI_PORT`.
- Frontend: Vite preview on `UI_HOST:UI_PORT`.
- Frontend communicates with backend through `/api/*`.

### Desktop packaged mode (Tauri)

- Build helper: `release/tauri/build_with_tauri.bat`.
- Tauri resolves packaged workspace/runtime, ensures `runtimes/.venv`, then starts local Uvicorn.
- Tauri injects `FAIRS_TAURI_MODE=true` for packaged behavior.
- Window opens `http://127.0.0.1:<FASTAPI_PORT>/` after backend readiness.

## 3. Backend Architecture

### Entry point and route mounting

- `FAIRS/server/app.py` creates the FastAPI app.
- Routers mounted from:
  - `FAIRS/server/api/upload.py`
  - `FAIRS/server/api/training.py`
  - `FAIRS/server/api/database.py`
  - `FAIRS/server/api/inference.py`

Routes are always exposed under `/api/*`.
When `FAIRS_ALLOW_DIRECT_API_ROUTES=true`, the same routes are also exposed without `/api`.

### Main layers

1. API layer: `FAIRS/server/api` (HTTP mapping and responses).
2. Services layer: `FAIRS/server/services` (job manager and service orchestration).
3. Domain layer: `FAIRS/server/domain` (request/response and shared domain state).
4. Learning layer: `FAIRS/server/learning` (training/inference execution and artifacts).
5. Persistence layer: `FAIRS/server/repositories` (DB initialization, schemas, serializers, queries).
6. Configuration layer: `FAIRS/server/configurations` (`environment.py`, `management.py`, `startup.py`).

### Configuration system

- Environment bootstrap happens at package import (`FAIRS/server/__init__.py`) through `load_environment()`.
- JSON technical settings are loaded and validated by `ConfigurationManager` in `FAIRS/server/configurations/management.py`.
- Startup access is provided through cached helpers in `FAIRS/server/configurations/startup.py` (`get_configuration_manager`, `get_server_settings`).
- Runtime/process keys are read from environment (`FASTAPI_*`, `UI_*`, docs/runtime toggles, ML backend vars).
- Technical backend keys are read only from `FAIRS/settings/configurations.json` (`database`, `jobs`, `device`).

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

- Root composition: `FAIRS/client/src/App.tsx`.
- Shared app state provider: `FAIRS/client/src/context/AppStateContext.tsx`.
- Main shell layout: `FAIRS/client/src/components/Layout/MainLayout.tsx`.
- Routes:
  - `/training` -> `pages/Training/TrainingPage.tsx`
  - `/inference` -> `pages/Inference/InferencePage.tsx`

## 5. Persistence Model

Primary tables:

- `datasets`
- `dataset_outcomes`
- `inference_sessions`
- `inference_session_steps`
- `roulette_outcomes`

Main ORM models are in `FAIRS/server/repositories/schemas/models.py`.
Dataset/session persistence orchestration is primarily in `FAIRS/server/repositories/serialization/data.py`.

## 6. Packaged SPA Behavior

When `FAIRS_TAURI_MODE=true` and `FAIRS/client/dist` exists:

- FastAPI serves SPA root at `/`.
- `/assets` is served from `FAIRS/client/dist/assets`.
- Unknown frontend paths fall back to `index.html`.
- If packaged SPA is unavailable, `/` falls back to docs redirect (when docs are enabled) or an `{\"status\":\"ok\"}` response.

## 7. Extension Points

- New API domain: add module under `FAIRS/server/api`, wire it in `FAIRS/server/app.py`, then add service/repository support.
- New background workflow: integrate with `FAIRS/server/services/jobs.py` and keep behavior aligned with `BACKGROUND_JOBS.md`.
- New frontend page: add route in `FAIRS/client/src/App.tsx` and update navigation/layout.
- Runtime or packaging behavior changes: update this file, `PACKAGING_AND_RUNTIME_MODES.md`, and `README.md` in the same change.
