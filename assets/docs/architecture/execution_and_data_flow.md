## Execution And Data Flow

Last updated: 2026-06-02

## Backend Layers

- API layer:
  - `app/server/api/*`
  - validates payloads, maps exceptions, and delegates orchestration
- Service layer:
  - `app/server/services/*`
  - coordinates jobs, training, inference, dataset import, and checkpoint lifecycle
- Domain layer:
  - `app/server/domain/*`
  - defines request, response, and configuration contracts
- Repository layer:
  - `app/server/repositories/queries/*`
  - `app/server/repositories/serialization/*`
  - handles persistence access and data transformation
- Database backend layer:
  - `app/server/repositories/database/*`
  - abstracts SQLite and PostgreSQL behavior
- ML execution layer:
  - `app/server/learning/*`
  - executes training and inference logic

## Application Startup Flow

`app/server/app.py` builds the app in this order:

1. Resolve server settings.
2. Initialize the configured database backend.
3. Run startup validations.
4. Construct shared services and attach them to `application.state`.
5. Mount API routers.
6. Configure SPA serving or docs redirect behavior.

## Typical Orchestration Chains

- Dataset upload:
  - `api/upload.py`
  - `DatasetService`
  - `DatasetImportService`
  - `DataSerializer`
  - `DataRepositoryQueries`
  - `FAIRSDatabase`
- Training start or resume:
  - `api/training.py`
  - `TrainingService`
  - `JobManager`
  - `ProcessWorker`
  - learning training modules
  - checkpoint serializer
- Inference session:
  - `api/inference.py`
  - `InferenceService`
  - `RoulettePlayer`
  - `CheckpointService`
  - `DataSerializer`
- Dataset list or delete:
  - `api/datasets.py`
  - `DatasetService`
  - `DataSerializer`
  - repository queries and backend

## Core Module Responsibilities

- `app/server/app.py`
  - FastAPI construction, dependency wiring, router mounting, and SPA serving
- `app/server/common/api_errors.py`
  - shared HTTP exception mapping helpers
- `app/server/common/constants.py`
  - shared constants including roulette wheel maps (position, color, color code)
- `app/server/common/session.py`
  - session identifier normalization and validation
- `app/server/configurations/startup.py`
  - cached settings and configuration access
- `app/server/services/jobs.py`
  - in-process job registry, `JobState` dataclass, progress tracking, and cancellation
- `app/server/services/training.py`
  - training lifecycle, worker management, and resume behavior
- `app/server/services/inference.py`
  - session state machine and session-step persistence
- `app/server/services/checkpoints.py`
  - checkpoint resolution, metadata, listing, deletion, model loading, and strategy model loading
- `app/server/services/startup_validation.py`
  - runtime pre-flight checks, storage directory creation, and Tauri-mode validation
- `app/server/repositories/schemas/models.py`
  - SQLAlchemy schema definitions and constraints
- `app/server/repositories/database/initializer.py`
  - database initialization and embedded-vs-external setup rules
- `app/server/repositories/database/utils.py`
  - database utility functions: engine normalization, datetime coercion, Postgres connect-arg builder

## Concurrency Model

- Most FastAPI handlers are synchronous `def` handlers.
- File upload is asynchronous only where non-blocking file reads matter.
- Long-running training is isolated from request handling:
  - `JobManager` tracks jobs in background threads
  - heavy training work runs in a separate process managed by `TrainingService`
- Inference is synchronous and stateful per active session.
- No async database driver or event-loop-based persistence model is used.

## Frontend Interaction Pattern

- The frontend talks to the backend through `/api/*`.
- Route composition lives in `app/client/src/App.tsx`.
- Shared app state is context-driven through `AppStateContext`.
- Feature-local hooks and components own most request and view orchestration.

## Related Files

- Read `backend_api.md` for the endpoint inventory.
- Read `persistence.md` for storage surfaces used by these flows.
