## Execution And Data Flow

Last updated: 2026-08-20

## Current Layering

The current application is a layered monolith with an explicit composition root. The names below describe ownership, not a claim that every package is framework-independent.

- **Interface:** `app/server/api/*` validates HTTP input, calls an application service, validates the response, and translates selected exceptions to HTTP status codes.
- **Contracts:** `app/server/contracts/*` contains Pydantic request/response contracts and validated settings dataclasses/models shared between interface and application code.
- **Application services:** `app/server/services/*` coordinates dataset import, checkpoints, training lifecycle, inference sessions, startup checks, and in-process job/session state.
- **Learning execution:** `app/server/learning/*` contains roulette betting rules, neural models, training algorithms, and inference players. It receives prepared data and explicit runtime inputs from application services.
- **Persistence adapters:** `app/server/repositories/*` owns SQLAlchemy schema, engines, transaction scopes, dataset/inference repositories, training queries, and checkpoint/model serialization.
- **Configuration:** `app/server/bootstrap.py` explicitly loads `.env`, resolves mutable paths, and configures logging before the composition root imports Keras-backed modules; `app/server/configurations/*` then resolves `.env` and JSON settings.
- **Shared primitives:** `app/server/common/*` contains paths, constants, logging, normalization, error mapping, and the shared roulette feature transformation.

## Current Module Dependency Diagram

```mermaid
flowchart TD
    Root[app.py\ncomposition root]
    Bootstrap[bootstrap.py\nexplicit runtime bootstrap]
    API[api]
    Contracts[contracts]
    Config[configurations]
    Services[services]
    Learning[learning]
    Repos[repositories]
    Common[common]
    DB[database adapters + schemas]
    Files[checkpoint/log/data files]
    ThirdParty[FastAPI, Pydantic, SQLAlchemy, Keras, Torch, pandas]

    Root --> API
    Root --> Bootstrap
    Root --> Config
    Root --> Services
    Root --> Repos
    API --> Contracts
    API --> Config
    API --> Services
    API --> Common
    Services --> Contracts
    Services --> Config
    Services --> Learning
    Services --> Repos
    Services --> Common
    Learning --> Common
    Repos --> Config
    Repos --> DB
    Repos --> Learning
    Repos --> Common
    DB --> ThirdParty
    API --> ThirdParty
    Learning --> ThirdParty
    Services --> Files
    Repos --> Files
```

The remaining cross-layer edge is `Repos --> Learning`, which is currently used to register custom Keras layers when loading checkpoints; it is not a database relationship. `Learning --> Repos` has been removed: the application worker and inference service supply persistence-derived inputs.

## Pragmatic Target Dependency Diagram

The target keeps the single-process application and existing packages. It moves orchestration and adapter construction toward application composition without introducing generic ports or speculative layers.

```mermaid
flowchart TD
    Root[Composition root]
    API[HTTP interface]
    Contracts[Boundary contracts]
    Services[Application services]
    LearningCore[Learning core\nmodels, betting, environment]
    Worker[Application-owned training worker]
    Persistence[Persistence and checkpoint adapters]
    Config[Explicit runtime configuration]
    External[Frameworks and external systems]

    Root --> API
    Root --> Services
    Root --> Persistence
    Root --> Config
    API --> Contracts
    API --> Services
    Services --> Contracts
    Services --> LearningCore
    Services --> Persistence
    Services --> Config
    Worker --> LearningCore
    Worker --> Persistence
    Worker --> Config
    LearningCore --> Contracts
    Persistence --> External
    Config --> External
```

`Worker` represents the implemented `server.services.training_worker` process orchestration module. It owns process channels and coordinates learning execution with explicit data/configuration and checkpoint storage collaborators.

## Startup Flow

`app/server/app.py` constructs the FastAPI object and routes before lifespan startup. The lifespan then:

1. Resolves server settings.
2. Runs startup validations and creates required storage directories.
3. Runs the shared Alembic create/upgrade runner for SQLite or PostgreSQL, including revision, lock, legacy-adoption, and strict metadata checks.
4. Constructs `FAIRSDatabase`, then constructs dataset/inference repositories and the `DataStore` persistence facade. The application engine is disposed during lifespan cleanup.
5. Constructs `JobManager`, `CheckpointService`, `DatasetService`, `TrainingService`, and `InferenceService`.
6. Stores those runtime objects on `application.state` for FastAPI dependency providers.

The `server` package itself is import-safe. `server.app` calls `bootstrap_runtime()` before importing Keras-backed application modules; the bootstrap loads/creates `.env`, resolves `FAIRS_DATA_DIR`, and configures logging from `FAIRS_LOG_DIR`. Direct imports of common path/logger modules do not create files or configure the global logging tree.

## Training Flow

```mermaid
sequenceDiagram
    participant Browser
    participant Client as React client
    participant API as FastAPI training router
    participant Service as TrainingService
    participant Jobs as JobManager
    participant Worker as TrainingWorker
    participant ML as DQNTraining
    participant Data as TrainingDataService
    participant DB as SQLite/PostgreSQL
    participant Files as Checkpoint files

    Browser->>Client: Configure training
    Client->>API: POST /api/training/start
    API->>Service: start_training(TrainingConfig)
    Service->>Jobs: start_job(run_training_job)
    Jobs-->>Service: job_id
    Service-->>API: 202 JobStartResponse
    API-->>Client: job_id and poll interval
    Service->>Worker: start training process
    Worker->>ML: run configured training
    Worker->>Data: load dataset or generate series
    Data->>DB: Read training outcomes when dataset-backed
    DB-->>Data: rows and roulette features
    loop While job is active
        Client->>API: GET /api/training/status
        API->>Service: get_status()
        Service->>Jobs: read progress/result
        Service-->>API: status and history
        API-->>Client: TrainingStatusResponse
        Worker-->>Service: progress messages
    end
    ML->>Files: Save model/configuration/history
    Worker-->>Service: result or error
```

Training is not an event-queue system: a `JobManager` thread monitors a separate worker process, and the browser polls status endpoints. No WebSocket or durable job table exists.

## Inference Flow

```mermaid
sequenceDiagram
    participant Client as React client
    participant API as FastAPI inference router
    participant Service as InferenceService
    participant Checkpoint as CheckpointService
    participant Model as CheckpointStorage
    participant Data as DataStore
    participant Dataset as DatasetRepository
    participant Player as RoulettePlayer
    participant Repo as InferenceRepository
    participant DB as SQLite/PostgreSQL

    Client->>API: POST /api/inference/sessions/start
    API->>Service: start_session(InferenceStartRequest)
    Service->>Checkpoint: resolve and load checkpoint
    Checkpoint->>Model: load model/configuration
    Model-->>Checkpoint: model and configuration
    Service->>Data: load dataset metadata
    Data->>Dataset: get(dataset_id)
    Dataset->>DB: SELECT dataset
    DB-->>Dataset: dataset metadata
    Service->>Data: load_dataset_outcomes(dataset_id)
    Data->>Dataset: get outcome rows
    Dataset->>DB: SELECT outcomes
    DB-->>Dataset: outcome rows
    Data-->>Service: prepared dataframe context
    Service->>Player: construct player with model and prepared context
    Service->>Repo: persist session header and initial prediction
    Repo->>DB: upsert session and step
    Service-->>API: session and prediction
    API-->>Client: InferenceStartResponse
    Client->>API: POST next, step, bet, clear, or shutdown
    API->>Service: apply session command
    Service->>Player: predict or apply observed extraction
    Service->>Repo: persist resulting step/state
    Service-->>API: typed response
    API-->>Client: response
```

Active sessions are held in `InferenceState` with a bounded in-memory session count. Database rows provide history, not a rehydration mechanism for the live `RoulettePlayer` object.

## Important Class Relationships

```mermaid
classDiagram
    class TrainingService {
        +start_training(config)
        +resume_training(config)
        +get_status()
        +stop()
    }
    class TrainingState {
        +latest_stats
        +history_points
        +current_job_id
    }
    class JobManager {
        +start_job()
        +get_job_status()
        +cancel_job()
    }
    class JobState {
        +job_id
        +status
        +progress
        +result
    }
    class ProcessWorker {
        +start()
        +poll()
        +stop()
        +terminate()
    }
    class DQNTraining {
        +train()
    }
    class TrainingDataService {
        +get_training_series(config)
    }
    class TrainingSeriesLoader {
        +load_training_series()
    }
    class TrainingRepositoryQueries {
        +load_training_dataset()
    }
    class InferenceService {
        +start_session(payload)
        +next_prediction(session_id)
        +step_session(session_id, payload)
    }
    class InferenceState {
        +sessions
        +max_sessions
    }
    class InferenceSession {
        +predict()
        +step(extraction)
        +update_bet(amount)
    }
    class RoulettePlayer {
        +dataset_context
        +predict_next()
        +update_with_true_extraction()
    }
    class CheckpointService
    class CheckpointStorage
    class DataStore
    class DatasetRepository
    class InferenceRepository
    class FAIRSDatabase

    TrainingService *-- TrainingState
    TrainingService --> JobManager
    TrainingService --> ProcessWorker
    JobManager *-- JobState
    ProcessWorker --> DQNTraining
    ProcessWorker --> TrainingDataService
    TrainingDataService --> TrainingSeriesLoader
    TrainingSeriesLoader --> TrainingRepositoryQueries
    TrainingRepositoryQueries --> FAIRSDatabase
    InferenceService *-- InferenceState
    InferenceState *-- InferenceSession
    InferenceSession *-- RoulettePlayer
    InferenceService --> CheckpointService
    InferenceService --> DataStore
    InferenceService --> InferenceRepository
    InferenceService --> RoulettePlayer : injects prepared context
    CheckpointService --> CheckpointStorage
    DataStore --> DatasetRepository
    DataStore --> InferenceRepository
    DatasetRepository --> FAIRSDatabase
    InferenceRepository --> FAIRSDatabase
```

## Responsibility and Duplication Notes

- Validation at the API boundary, service boundary, and database constraint boundary is intentional defense in depth; it is not automatically accidental duplication.
- Roulette feature derivation is now one shared transformation in `server.common.roulette`.
- `DataStore` is a narrow coordinator over dataset and inference repositories; its role-specific name avoids calling repository coordination “serialization.”
- `TrainingDataService` owns stored/synthetic training-series selection and passes concrete database settings/path into a worker-local `TrainingSeriesLoader`.
- `CheckpointStorage` owns checkpoint filesystem I/O. The checkpoint service scans its JSON metadata before allowing dataset deletion.
- `TrainingService` and `InferenceService` are broad because they own lifecycle state and orchestration; split them only when a concrete change isolates a cohesive responsibility.
- Frontend feature components currently combine network calls, parsing, local state, and rendering. Extract feature API hooks incrementally when those areas change; a wholesale rewrite is not justified by the current local runtime.

## Concurrency and Observability

- Most handlers are synchronous `def` handlers; file upload is asynchronous for file reads.
- Training runs outside the request thread in a worker process monitored by a job thread.
- Inference is synchronous and stateful per active process.
- Logs are timestamped `FAIRS_*.log` files under the configured data/log root; logging is configured by the explicit bootstrap boundary.
- `GET /api/health` is a lightweight readiness check exposing version and runtime mode.

## Related Files

- Read `backend_api.md` for the endpoint inventory and transport contract.
- Read `persistence.md` for relational tables and filesystem storage.
- Read `findings_and_remediation.md` for evidence, priorities, and migration steps.
