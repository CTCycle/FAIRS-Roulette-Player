# ARCHITECTURE

Last updated: 2026-04-27

## System Summary

FAIRS is a multi-runtime application with:
- FastAPI backend in `FAIRS/server`
- React + TypeScript frontend in `FAIRS/client/src`
- Optional Windows desktop wrapper (Tauri + Rust) in `FAIRS/client/src-tauri`

The backend is the system of record for API, training orchestration, inference sessions, and persistence.

## Directory and File Structure

The structure below is source-focused and excludes dependency/vendor/build-cache folders such as `node_modules`, `dist`, `target`, and `__pycache__`.

```text
.
├─ pyproject.toml
├─ uv.lock
├─ README.md
├─ FAIRS/
│  ├─ start_on_windows.bat
│  ├─ setup_and_maintenance.bat
│  ├─ scripts/
│  │  └─ initialize_database.py
│  ├─ settings/
│  │  ├─ .env
│  │  ├─ .env.example
│  │  └─ configurations.json
│  ├─ resources/
│  │  ├─ database.db
│  │  ├─ checkpoints/
│  │  └─ logs/
│  ├─ server/
│  │  ├─ __init__.py
│  │  ├─ app.py
│  │  ├─ api/
│  │  │  ├─ __init__.py
│  │  │  ├─ upload.py
│  │  │  ├─ training.py
│  │  │  ├─ database.py
│  │  │  └─ inference.py
│  │  ├─ common/
│  │  │  ├─ api_errors.py
│  │  │  ├─ checkpoints.py
│  │  │  ├─ constants.py
│  │  │  └─ utils/
│  │  │     ├─ __init__.py
│  │  │     ├─ logger.py
│  │  │     ├─ trainingstats.py
│  │  │     └─ types.py
│  │  ├─ configurations/
│  │  │  ├─ __init__.py
│  │  │  ├─ dependencies.py
│  │  │  ├─ environment.py
│  │  │  ├─ management.py
│  │  │  └─ startup.py
│  │  ├─ domain/
│  │  │  ├─ __init__.py
│  │  │  ├─ configuration.py
│  │  │  ├─ database.py
│  │  │  ├─ inference.py
│  │  │  ├─ jobs.py
│  │  │  ├─ training.py
│  │  │  └─ upload.py
│  │  ├─ learning/
│  │  │  ├─ __init__.py
│  │  │  ├─ betting/
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ hold.py
│  │  │  │  ├─ sizer.py
│  │  │  │  └─ types.py
│  │  │  ├─ inference/
│  │  │  │  ├─ __init__.py
│  │  │  │  └─ player.py
│  │  │  ├─ models/
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ embeddings.py
│  │  │  │  ├─ logits.py
│  │  │  │  ├─ qnet.py
│  │  │  │  └─ strategy.py
│  │  │  └─ training/
│  │  │     ├─ __init__.py
│  │  │     ├─ agents.py
│  │  │     ├─ device.py
│  │  │     ├─ environment.py
│  │  │     ├─ fitting.py
│  │  │     ├─ generator.py
│  │  │     ├─ serializer.py
│  │  │     └─ worker.py
│  │  ├─ repositories/
│  │  │  ├─ __init__.py
│  │  │  ├─ database/
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ backend.py
│  │  │  │  ├─ initializer.py
│  │  │  │  ├─ postgres.py
│  │  │  │  ├─ sqlite.py
│  │  │  │  └─ utils.py
│  │  │  ├─ queries/
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ data.py
│  │  │  │  └─ training.py
│  │  │  ├─ schemas/
│  │  │  │  ├─ __init__.py
│  │  │  │  └─ models.py
│  │  │  └─ serialization/
│  │  │     ├─ __init__.py
│  │  │     ├─ data.py
│  │  │     ├─ model.py
│  │  │     └─ training.py
│  │  └─ services/
│  │     ├─ __init__.py
│  │     ├─ checkpoints.py
│  │     ├─ datasets.py
│  │     ├─ importer.py
│  │     ├─ inference.py
│  │     ├─ jobs.py
│  │     ├─ loader.py
│  │     ├─ process.py
│  │     └─ training.py
│  ├─ client/
│  │  ├─ package.json
│  │  ├─ vite.config.ts
│  │  ├─ index.html
│  │  ├─ public/
│  │  │  ├─ favicon.png
│  │  │  └─ roulette_wheel.png
│  │  ├─ src/
│  │  │  ├─ main.tsx
│  │  │  ├─ App.tsx
│  │  │  ├─ assets/react.svg
│  │  │  ├─ styles/global.css
│  │  │  ├─ context/
│  │  │  │  ├─ AppStateContext.tsx
│  │  │  │  └─ AppStateStore.ts
│  │  │  ├─ hooks/
│  │  │  │  ├─ useAppState.ts
│  │  │  │  ├─ useCheckpointOptions.ts
│  │  │  │  ├─ useDatasetFileUpload.ts
│  │  │  │  ├─ useDatasetUploadState.ts
│  │  │  │  ├─ useInferenceSetupOptions.ts
│  │  │  │  ├─ useKeyboardActivation.ts
│  │  │  │  └─ useWizardStep.ts
│  │  │  ├─ components/
│  │  │  │  ├─ Layout/
│  │  │  │  │  ├─ HeaderBar.tsx
│  │  │  │  │  ├─ MainLayout.tsx
│  │  │  │  │  ├─ MainLayout.css
│  │  │  │  │  └─ TopNavigation.tsx
│  │  │  │  ├─ datasetUpload/
│  │  │  │  │  ├─ DatasetFileDropzone.tsx
│  │  │  │  │  └─ UploadStatusMessage.tsx
│  │  │  │  ├─ inference/
│  │  │  │  │  ├─ GameSession.tsx
│  │  │  │  │  └─ GameSession.module.css
│  │  │  │  └─ wizard/WizardSummaryRows.tsx
│  │  │  ├─ pages/
│  │  │  │  ├─ Inference/
│  │  │  │  │  ├─ InferencePage.tsx
│  │  │  │  │  └─ InferencePage.css
│  │  │  │  └─ Training/
│  │  │  │     ├─ TrainingPage.tsx
│  │  │  │     ├─ Training.css
│  │  │  │     └─ components/
│  │  │  │        ├─ CheckpointPreview.tsx
│  │  │  │        ├─ DatasetPreview.tsx
│  │  │  │        ├─ DatasetUpload.tsx
│  │  │  │        ├─ TrainingDashboard.tsx
│  │  │  │        ├─ TrainingLossChart.tsx
│  │  │  │        ├─ TrainingMetricCard.tsx
│  │  │  │        ├─ TrainingMetricsChart.tsx
│  │  │  │        ├─ trainingPayload.ts
│  │  │  │        └─ WizardActions.tsx
│  │  │  ├─ types/
│  │  │  │  ├─ datasetUpload.ts
│  │  │  │  ├─ frontendApi.ts
│  │  │  │  └─ inference.ts
│  │  │  └─ utils/
│  │  │     ├─ apiParsers.ts
│  │  │     ├─ datasetUpload.ts
│  │  │     └─ frontendApiParsers.ts
│  │  └─ src-tauri/
│  │     ├─ Cargo.toml
│  │     ├─ build.rs
│  │     ├─ tauri.conf.json
│  │     ├─ capabilities/default.json
│  │     ├─ icons/...
│  │     └─ src/main.rs
├─ release/
│  └─ tauri/
│     ├─ build_with_tauri.bat
│     └─ scripts/
└─ tests/
   ├─ conftest.py
   ├─ run_tests.bat
   ├─ test_config.json
   ├─ unit/
   └─ e2e/
```

## Application Entry Points

- Backend app entry: `FAIRS/server/app.py` (`app = FastAPI(...)`).
- Backend process launch (local): `FAIRS/start_on_windows.bat` (`python -m uvicorn FAIRS.server.app:app`).
- Backend process launch (desktop runtime): `FAIRS/client/src-tauri/src/main.rs` spawns `uvicorn` using runtime `.venv`.
- Frontend entry: `FAIRS/client/src/main.tsx`.
- Frontend route composition: `FAIRS/client/src/App.tsx`.
- Desktop shell entry: `FAIRS/client/src-tauri/src/main.rs`.

## API Endpoints

All backend routers are mounted with prefix `/api`.

### Upload
- `POST /api/data/upload`

### Training
- `POST /api/training/start`
- `POST /api/training/resume`
- `GET /api/training/status`
- `POST /api/training/stop`
- `GET /api/training/checkpoints`
- `GET /api/training/checkpoints/{checkpoint}/metadata`
- `DELETE /api/training/checkpoints/{checkpoint}`
- `GET /api/training/jobs/{job_id}`
- `DELETE /api/training/jobs/{job_id}`

### Database
- `GET /api/database/roulette-series/datasets`
- `GET /api/database/roulette-series/datasets/summary`
- `DELETE /api/database/roulette-series/datasets/{dataset_id}`

### Inference
- `POST /api/inference/sessions/start`
- `POST /api/inference/sessions/{session_id}/next`
- `POST /api/inference/sessions/{session_id}/step`
- `POST /api/inference/sessions/{session_id}/shutdown`
- `POST /api/inference/sessions/{session_id}/bet`
- `POST /api/inference/sessions/{session_id}/rows/clear`
- `POST /api/inference/context/clear`

No WebSocket routes are currently implemented in `FAIRS/server/api`.

## Layered Architecture and Responsibilities

### Backend flow
- Endpoint layer: `FAIRS/server/api/*` validates/marshals HTTP payloads and maps exceptions to status codes.
- Service layer: `FAIRS/server/services/*` orchestrates jobs, training/inference workflows, dataset import, and checkpoint lifecycle.
- Domain layer: `FAIRS/server/domain/*` defines Pydantic/domain contracts for requests/responses/settings.
- Repository query/serialization layer: `FAIRS/server/repositories/queries/*` and `FAIRS/server/repositories/serialization/*` provide persistence operations and dataframe-to-table transforms.
- Database backend layer: `FAIRS/server/repositories/database/*` abstracts SQLite/PostgreSQL engines and CRUD operations.
- ML execution layer: `FAIRS/server/learning/*` executes training and inference model logic.

### Typical endpoint-to-repository chains
- Dataset upload: `api/upload.py` -> `DatasetService` -> `DatasetImportService` -> `DataSerializer` -> `DataRepositoryQueries` -> `FAIRSDatabase` backend.
- Training start/resume: `api/training.py` -> `TrainingService` -> `JobManager` + `ProcessWorker` -> learning training modules + checkpoint serializer.
- Inference session: `api/inference.py` -> `InferenceService` -> `RoulettePlayer` + `CheckpointService` + `DataSerializer` persistence.
- Dataset list/delete: `api/database.py` -> `DatasetService` -> `DataSerializer` -> repository queries/backend.

### Key module responsibilities
- `FAIRS/server/app.py`: FastAPI app factory and entry point, dependency graph initialization in lifespan, router mounting, packaged SPA serving behavior.
- `FAIRS/server/common/api_errors.py`: shared HTTP exception mapping helpers used by endpoint modules.
- `FAIRS/server/configurations/startup.py`: cached settings/config manager access.
- `FAIRS/server/services/jobs.py`: in-process job registry and cancellation/progress management.
- `FAIRS/server/services/training.py`: training state, worker lifecycle, progress projection, resume behavior.
- `FAIRS/server/services/inference.py`: session state machine and session-step persistence.
- `FAIRS/server/services/checkpoints.py`: checkpoint path normalization, metadata, list/delete/resolve.
- `FAIRS/server/repositories/schemas/models.py`: SQLAlchemy schema definitions and constraints.
- `FAIRS/server/repositories/database/initializer.py`: SQLite auto-init and PostgreSQL initialization/seed logic.

## Data Persistence

### Backends
- SQLite when `database.embedded_database = true` in `FAIRS/settings/configurations.json`.
- PostgreSQL when `embedded_database = false` (engine/host/credentials from `configurations.json`).

### Core tables
- `roulette_outcomes`
- `datasets`
- `dataset_outcomes`
- `inference_sessions`
- `inference_session_steps`

### Data storage surfaces
- Relational data: `FAIRS/resources/database.db` (SQLite mode) or PostgreSQL database.
- Model checkpoints: `FAIRS/resources/checkpoints/<checkpoint_id>/...`.
- Runtime logs: `FAIRS/resources/logs/*.log`.

## Async vs Sync Behavior and Constraints

- Most FastAPI handlers are synchronous (`def`) and execute quick orchestration.
- File upload handler is asynchronous (`async def upload`) only for non-blocking `UploadFile.read()`.
- Long-running training does not run in request threads:
  - `JobManager` uses a background thread per job.
  - heavy training runs in a separate process (`ProcessWorker`) managed by `TrainingService`.
- Inference operations are synchronous and stateful in-memory per session (`InferenceState`).
- No async database driver/event loop concurrency model is currently used; persistence uses SQLAlchemy with synchronous engines.

## Frontend Architecture

- Global state: reducer-based context in `AppStateContext.tsx`.
- Route shell: `MainLayout` with two primary routes:
  - `/training`
  - `/inference`
- API calls are feature-local in hooks/components and target `/api/*`.
- Styling model is token-driven (`src/styles/global.css`) with page/component CSS modules and stylesheets.
