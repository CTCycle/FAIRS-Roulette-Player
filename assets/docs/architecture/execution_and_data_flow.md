## Execution And Data Flow

Last updated: 2026-08-30

## Current Layering

FAIRS is a layered local monolith with an explicit composition root. The names below describe ownership, not a claim that every package is framework-independent.

- **Interface:** `app/server/api/*` validates HTTP input, calls an application service, validates the response, and translates selected exceptions to HTTP status codes.
- **Contracts:** `app/server/contracts/*` contains Pydantic request/response contracts and validated settings models shared between the interface and application code.
- **Application services:** `app/server/services/*` coordinates dataset import, checkpoint lifecycle, training runs, inference sessions, startup checks, and worker-process orchestration.
- **Learning execution:** `app/server/learning/*` contains roulette betting rules, neural models, training algorithms, and inference players. It receives prepared data and explicit runtime inputs from application services.
- **Persistence adapters:** `app/server/repositories/*` owns SQLAlchemy schema, engines, transactions, dataset/inference repositories, and checkpoint filesystem/configuration I/O.
- **Configuration:** `app/server/bootstrap.py` explicitly loads `.env`, resolves mutable paths, and configures logging before the composition root imports Keras-backed modules; `app/server/configurations/*` resolves JSON settings and typed environment database settings.
- **Shared primitives:** `app/server/common/*` contains paths, constants, logging, normalization, error mapping, version lookup, and the shared roulette feature transformation.

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
    Repos --> DB
    Repos --> Common
    Repos -.->|checkpoint custom-layer registration| Learning
    DB --> ThirdParty
    API --> ThirdParty
    Learning --> ThirdParty
    Services --> Files
    Repos --> Files
```

The dashed repository-to-learning edge is limited to custom Keras-layer registration required when loading checkpoints. Learning execution does not construct databases or import application repositories.

## Startup Flow

`app/server/app.py` constructs the FastAPI object and routes before lifespan startup. The lifespan then:

1. Resolves typed server settings from JSON and the explicit environment database fields.
2. Runs startup validations and creates the canonical data-root, `logs`, and `checkpoints` directories.
3. Runs the shared Alembic create/upgrade runner for SQLite or PostgreSQL. Empty databases upgrade to `head`; non-empty unversioned databases, drift, unknown/ahead revisions, and multiple heads are rejected without runtime adoption or stamping.
4. Constructs `FAIRSDatabase`, the `DatasetRepository`, and the `InferenceRepository`. The application engine is disposed during lifespan cleanup.
5. Constructs one `CheckpointService`, one `TrainingRunManager`, `DatasetService`, `TrainingService`, and `InferenceService` with those concrete collaborators.
6. Stores the runtime objects on `application.state` for FastAPI dependency providers.

The `server` package itself is import-safe. `server.app` calls `bootstrap_runtime()` before importing Keras-backed application modules; the bootstrap loads/creates `.env`, resolves `FAIRS_DATA_DIR`, and configures logging under the active data root. Direct imports of common path/logger modules do not create files or configure the global logging tree.

## Training Flow

```mermaid
sequenceDiagram
    participant Browser
    participant Client as React client
    participant API as FastAPI training router
    participant Service as TrainingService
    participant Runs as TrainingRunManager
    participant Worker as ProcessWorker
    participant ML as DQNTraining
    participant Data as TrainingDataService
    participant Dataset as DatasetRepository
    participant DB as SQLite/PostgreSQL
    participant Files as CheckpointRepository

    Browser->>Client: Configure training in local page state
    Client->>API: POST /api/training/start
    API->>Service: start_training(TrainingConfig)
    Service->>Runs: start_job(training runner)
    Runs-->>Service: job_id
    Service-->>API: 202 JobStartResponse
    API-->>Client: job_id and poll interval
    Runs->>Worker: start process
    Worker->>Data: load or generate training series
    Data->>Dataset: training_outcomes(dataset_id)
    Dataset->>DB: SELECT training outcomes
    DB-->>Dataset: rows
    Data-->>ML: encoded dataframe
    Worker->>ML: run configured training
    loop While run is active
        Client->>API: GET /api/training/status
        API->>Service: get_status()
        Service->>Runs: read run snapshot
        Runs-->>API: typed status/history projection
        API-->>Client: TrainingStatusResponse
        Worker-->>Runs: progress messages
    end
    ML->>Files: save model/configuration/history
    Worker-->>Runs: result or error
```

`TrainingRunManager` is the single in-process training-run state owner. It owns the authoritative `TrainingRun`, worker handle, progress, cancellation flag, latest statistics, and history projection. A run may use a child `ProcessWorker`, while the browser polls the status endpoint; there is no WebSocket or durable job table. `additional_episodes` is a resume operation input and is not added to the persisted checkpoint configuration.

## Inference Flow

```mermaid
sequenceDiagram
    participant Client as React client
    participant API as FastAPI inference router
    participant Service as InferenceService
    participant Checkpoint as CheckpointService
    participant Model as CheckpointRepository
    participant Dataset as DatasetRepository
    participant Player as RoulettePlayer
    participant Repo as InferenceRepository
    participant DB as SQLite/PostgreSQL

    Client->>API: POST /api/inference/sessions/start
    API->>Service: start_session(InferenceStartRequest)
    Note over API,Service: Request is checkpoint, numeric dataset_id, game_capital, game_bet
    Service->>Checkpoint: resolve and load checkpoint
    Checkpoint->>Model: load model/configuration
    Model-->>Checkpoint: model and checkpoint-owned strategy config
    Service->>Dataset: get(dataset_id)
    Dataset->>DB: SELECT dataset metadata
    DB-->>Dataset: dataset metadata
    Service->>Dataset: outcomes(dataset_id)
    Dataset->>DB: SELECT outcomes
    DB-->>Dataset: outcome rows
    Service->>Player: construct with model, config, and dataframe
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

The inference start contract does not accept dataset-source labels, session replacement identifiers, or strategy overrides. The checkpoint owns strategy behavior; the service only overlays the per-session capital and bet. Active sessions are held in `InferenceState` with a bounded in-memory session count. Database rows provide history, not a rehydration mechanism for the live `RoulettePlayer` object.

## Important Class Relationships

```mermaid
classDiagram
    class TrainingService {
        +start_training(config)
        +resume_training(config)
        +get_status()
        +stop()
    }
    class TrainingRunManager {
        +start_job()
        +training_status()
        +get_job_status()
        +cancel_job()
    }
    class TrainingRun {
        +job_id
        +status
        +progress
        +latest_stats
        +history_points
        +worker
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
        +context
        +predict_next()
        +update_with_true_extraction()
    }
    class CheckpointService
    class CheckpointRepository
    class DatasetRepository
    class InferenceRepository
    class FAIRSDatabase

    TrainingService --> TrainingRunManager
    TrainingRunManager *-- TrainingRun
    TrainingRun --> ProcessWorker
    ProcessWorker --> DQNTraining
    ProcessWorker --> TrainingDataService
    TrainingDataService --> DatasetRepository
    InferenceService *-- InferenceState
    InferenceState *-- InferenceSession
    InferenceSession *-- RoulettePlayer
    InferenceService --> CheckpointService
    InferenceService --> DatasetRepository
    InferenceService --> InferenceRepository
    CheckpointService --> CheckpointRepository
    DatasetRepository --> FAIRSDatabase
    InferenceRepository --> FAIRSDatabase
```

## Responsibility And Duplication Notes

- Validation at the API boundary, service boundary, and database constraint boundary is intentional defense in depth; it is not automatically accidental duplication.
- Roulette feature derivation is one shared transformation in `server.common.roulette`.
- `DatasetRepository` is the sole SQL authority for dataset metadata and outcome rows. `TrainingDataService` owns encoding and sampling after repository reads.
- `CheckpointRepository` owns checkpoint filesystem I/O and validates the current checkpoint configuration contract. `CheckpointService` owns lifecycle policy, including dataset-reference checks before deletion.
- `TrainingRunManager` owns the one authoritative in-process training-run model; `TrainingService` coordinates operations and worker execution around it.
- Training and inference pages own their workflow snapshots. `useTrainingStatus` is the single frontend training-status polling hook; API parsers reject malformed or legacy shapes instead of silently selecting compatibility defaults.

## Concurrency And Observability

- Most handlers are synchronous `def` handlers; file upload is asynchronous for file reads.
- Training runs outside the request thread in a worker process monitored by the `TrainingRunManager` thread.
- Inference is synchronous and stateful per active backend process.
- Logs are timestamped `FAIRS_*.log` files under the configured data-root `logs` directory.
- `GET /api/health` is a lightweight readiness check exposing application version from installed `fairs-server` package metadata; it has no desktop/runtime-mode field.

## Related Files

- Read `backend_api.md` for the endpoint inventory and transport contract.
- Read `persistence.md` for relational tables and filesystem storage.
- Read `findings_and_remediation.md` for evidence, priorities, and migration steps.
