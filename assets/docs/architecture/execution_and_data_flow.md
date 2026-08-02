## Execution And Data Flow

Last updated: 2026-08-02

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

`app/server/app.py` constructs the app with routers and client routes, then its lifespan performs runtime startup in this order:

1. Resolve server settings.
2. Initialize the configured database backend.
3. Run startup validations.
4. Construct the database handle.
5. Validate the database schema.
6. Construct the serializers, job manager, checkpoint service, and domain services, then attach them and the database to `application.state`.

Router mounting and SPA/docs route configuration happen during app construction before the lifespan runs.

## Typical Orchestration Chains

- Dataset upload:
  - `api/upload.py`
  - `DatasetService`
  - `DatasetImportService`
  - `DataSerializer`
  - `DatasetRepository`
  - `FAIRSDatabase`
- Synthetic training data:
  - `DataSerializerExtension`
  - `RouletteSyntheticGenerator` emits canonical `outcome` values in the range `0..36`
  - `RouletteSeriesEncoder` adds wheel and color features
  - the training serializer normalizes the encoded outcome column to `extraction`, matching the training environment contract
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
  - `DatasetRepository`

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
  - runtime pre-flight checks and storage directory creation
- `app/server/repositories/schemas/models.py`
  - SQLAlchemy schema definitions and constraints
- `app/server/repositories/database/initializer.py`
  - database initialization and embedded-vs-external setup rules
- `app/server/repositories/database/utils.py`
  - database utility functions: engine normalization, datetime coercion, Postgres connect-arg builder
- `app/server/repositories/datasets.py`
  - atomic dataset replacement, summaries, reads, and cascade deletion
- `app/server/repositories/inference.py`
  - inference session and step persistence
- `app/server/repositories/queries/training.py`
  - training-oriented database queries and checkpoint-adjacent persistence operations
- `app/server/repositories/serialization/model.py`
  - model and checkpoint serialization helpers
- `app/server/repositories/serialization/training.py`
  - training configuration and result serialization helpers
- `app/server/learning/training/generator.py`
  - deterministic synthetic roulette-series generation from the training configuration
- `app/server/learning/training/serializer.py`
  - synthetic/data-backed series selection and canonical training-column normalization

## Concurrency Model

- Most FastAPI handlers are synchronous `def` handlers.
- File upload is asynchronous only where non-blocking file reads matter.
- Long-running training is isolated from request handling:
  - `JobManager` tracks jobs in background threads
  - heavy training work runs in a separate process managed by `TrainingService`
- Inference is synchronous and stateful per active session.
- No async database driver or event-loop-based persistence model is used.

## Runtime Observability

- The backend writes timestamped `FAIRS_*.log` files under the configured log directory.
- `FAIRS_LOG_DIR` can isolate logs for tests or diagnostics.
- `GET /api/health` exposes a lightweight readiness check with application version and mode.

## Frontend Interaction Pattern

- The frontend talks to the backend through `/api/*`.
- Route composition lives in `app/client/src/App.tsx`.
- Shared app state is context-driven through `AppStateContext`.
- Feature-local hooks and components own most request and view orchestration.

## Related Files

- Read `backend_api.md` for the endpoint inventory.
- Read `persistence.md` for storage surfaces used by these flows.
