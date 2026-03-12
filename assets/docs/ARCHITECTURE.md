# FAIRS Architecture

FAIRS is a FastAPI + React/Vite web application for roulette model training and inference workflows.

## 1. Repository layout

- `FAIRS/server`: FastAPI backend, training/inference logic, database access.
- `FAIRS/client`: React + TypeScript frontend built with Vite.
- `FAIRS/settings`: Runtime configuration (`.env`, profile examples, `configurations.json`).
- `FAIRS/resources`: Runtime data (`checkpoints`, `database`, `logs`).
- `runtimes`: Portable Python/uv/Node.js runtimes provisioned by Windows scripts.
- `release/tauri`: Desktop packaging scripts and output staging helpers.
- `tests`: Python unit and E2E tests (pytest + pytest-playwright).

## 2. Runtime topology

### Local mode (default webapp)

- Start with `FAIRS\start_on_windows.bat`.
- Backend runs Uvicorn (`FAIRS.server.app:app`) on `FASTAPI_HOST:FASTAPI_PORT`.
- Frontend runs Vite preview on `UI_HOST:UI_PORT`.
- Frontend talks to backend through `/api` proxying.

### Desktop packaged mode (Tauri)

- Desktop artifacts are produced via `release\tauri\build_with_tauri.bat`.
- Tauri launches a local backend from a packaged runtime root and then opens `http://127.0.0.1:<FASTAPI_PORT>/`.
- FastAPI serves the packaged SPA and exposes API routes under `/api`.

## 3. Backend architecture

### Entry point

- `FAIRS/server/app.py` creates the FastAPI app and mounts routers:
  - `/data` (`routes/upload.py`)
  - `/training` (`routes/training.py`)
  - `/database` (`routes/database.py`)
  - `/inference` (`routes/inference.py`)

### Layers

1. Routes (`FAIRS/server/routes`): request validation, HTTP status mapping.
2. Services (`FAIRS/server/services`): upload parsing/import and job orchestration.
3. Learning (`FAIRS/server/learning`): DQN training, inference player, betting logic.
4. Repositories (`FAIRS/server/repositories`): DB backends, queries, serialization helpers.
5. Configurations (`FAIRS/server/configurations`): env + JSON settings resolution.

### API surface (current)

- Data upload:
  - `POST /data/upload?table=roulette_series|inference_context`
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

## 4. Frontend architecture

- Router setup in `FAIRS/client/src/App.tsx` with the shared shell rendered from `components/Layout/MainLayout.tsx`.
- Main pages currently mounted:
  - `/training` -> training dashboard, dataset upload/preview, checkpoint management.
  - `/inference` -> interactive inference session and session history controls.
- Shared app state lives in `FAIRS/client/src/context/AppStateContext.tsx`.
- API access is fetch-based and routed through `/api/*`.

## 5. Persistence model

Primary tables:

- `datasets`
- `dataset_outcomes`
- `inference_sessions`
- `inference_session_steps`
- `roulette_outcomes`

`DataSerializer` handles dataset normalization, import, listing, deletion, and inference session persistence.

## 6. Extension points

- New API domain: add route in `FAIRS/server/routes`, service in `FAIRS/server/services`, and serializer/query support in `FAIRS/server/repositories` as needed.
- New training/inference behavior: extend `FAIRS/server/learning/*` and expose controls in frontend page components.
- New UI page: register route in `FAIRS/client/src/App.tsx` and add navigation in `components/Layout/TopNavigation.tsx`.
