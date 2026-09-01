## Architecture Findings And Remediation

Last updated: 2026-09-01

## Review Scope And Method

This review traced the checked-in Python and TypeScript source, FastAPI composition/wiring, route decorators, SQLAlchemy models, repository calls, filesystem checkpoint paths, frontend imports and fetch calls, tests, CI, and existing documentation. Dependency statements below are derived from those sources. Generated bundles, dependency directories, caches, and screenshots were excluded from the structural inventory.

The current baseline is healthy: the CI workflow validates backend Ruff/unit/OpenAPI/Alembic/persistence checks plus frontend lint and production build on Node 22. No P0 issue was found, and no confirmed circular dependency exists in the meaningful application module graph. This remediation pass removes the remaining legacy compatibility paths and duplicate state owners identified by the pasted audit.

## Current State

FAIRS is a layered local monolith:

- React/Vite presents Training and Inference routes and owns browser state, interaction, defensive payload parsing, and polling.
- FastAPI routers expose `/api/*`, validate transport contracts, translate selected exceptions, and delegate to services.
- Application services own dataset import, checkpoints, training jobs, inference session state, and lifecycle orchestration.
- Learning modules contain betting rules, neural models, training environments, and inference players. Training process orchestration is application-owned under `services/training_worker.py`.
- Repositories own SQLAlchemy schema/transactions, dataset and session persistence, and checkpoint/model file I/O. `DatasetRepository` is the sole SQL authority for dataset metadata and outcomes.
- Configuration resolves `.env` and JSON settings; common modules provide paths, constants, logging, version lookup, normalization, errors, and roulette feature encoding.

The repository is designed for one local backend process. Jobs and active inference sessions are in memory; training work runs in a child process; relational history and checkpoint files are durable but are not a distributed coordination mechanism.

See `system_overview.md`, `execution_and_data_flow.md`, and `persistence.md` for the source-derived diagrams.

## Strengths To Preserve

- `app/server/app.py` is a clear composition root that wires concrete dependencies during lifespan startup.
- API modules delegate to services and do not issue SQLAlchemy queries directly.
- Dataset, session, and step persistence has explicit transaction scopes, composite keys, foreign keys, cascades, uniqueness constraints, and value checks.
- Training is isolated from request handling through a monitored worker process and a polling API.
- The checked-in OpenAPI snapshot is generated from the FastAPI application and checked in CI.
- Tests cover service behavior, API workflows, persistence behavior, startup/configuration, and security-sensitive paths.
- The local in-memory training-run/session model is appropriate for the documented single-process runtime; distributed persistence would add complexity without a current deployment requirement.

## Findings

| ID | Priority | Location | Description and impact | Preferred solution | Timing |
| --- | --- | --- | --- | --- | --- |
| F-01 | P1 | `app/server/domain/*` (renamed to `contracts/*`) | The package contained Pydantic transport/configuration contracts, not framework-independent domain entities. The name made dependency direction and ownership ambiguous for new contributors. | Use `server.contracts` and describe these objects as boundary contracts. Do not create a speculative domain layer. | Resolved now |
| F-02 | P1 | Former `services/process.py`, `learning/training/serializer.py`, `repositories/queries/training.py` | Roulette wheel/color feature derivation existed in both learning-adjacent and repository code. Drift could produce different training features for generated versus persisted data. | Use one narrow `common.roulette.encode_roulette_series` transformation. | Resolved now |
| F-03 | P1 | `server/__init__.py`, `bootstrap.py`, `common/path.py`, `common/utils/logger.py`, `configurations/environment.py` | Importing the package no longer loads/creates `.env` or configures paths/logging. FastAPI lifespan performs those actions before importing Keras-backed application modules. | Keep `server.bootstrap.bootstrap_runtime()` as the only application bootstrap boundary; direct utility imports and app construction remain filesystem/ML-free. | Resolved now |
| F-04 | P1 | `services/training_data.py`, `services/training_worker.py`, `learning/models/qnet.py`, `learning/training/fitting.py` | Training data/configuration orchestration was coupled to learning code, which constructed `FAIRSDatabase` and read global server settings. | Data loading lives in `TrainingDataService`, `services/training_worker.py` owns process orchestration, and the worker receives a top-level loader plus concrete database/path/device/polling values. | Resolved now |
| F-05 | P1 | `repositories/database/initializer.py`, `repositories/database/backend.py`, `schemas/models.py`, `alembic/` | Schema evolution previously relied on `create_all()` and a native SQLite marker, leaving existing databases without an authoritative revision history. | Alembic is authoritative. Empty databases upgrade to `head`; every non-empty unversioned database is rejected unchanged. The shared runner rejects drift/unknown states and validates post-upgrade metadata; explicit migration is required for older databases. | Resolved now; future revisions remain incremental |
| F-06 | P1 | `repositories/serialization/model.py`, checkpoint JSON, `services/checkpoints.py`, `services/datasets.py` | Checkpoint configuration can retain a `dataset_id`, while dataset deletion cascades relational rows without inspecting checkpoint directories. | Dataset deletion scans checkpoint metadata and returns a `409` conflict listing affected checkpoints; unreadable checkpoint metadata also blocks deletion. Immutable dataset snapshots remain deferred. | Resolved now; immutable snapshots deferred |
| F-07 | P2 | `repositories/serialization/*`, `repositories/queries/*`, dataset and training services | Persistence responsibilities were split across generic serializer/query paths and a facade, obscuring the authoritative owner for datasets, training reads, and checkpoint files. | Removed the obsolete serialization/query paths. `DatasetRepository` owns dataset SQL, `TrainingDataService` owns encoding/sampling, and `CheckpointRepository` owns checkpoint filesystem/configuration I/O. | Resolved now |
| F-08 | P2 | `api/training.py`, `api/inference.py`, `api/upload.py`, `api/datasets.py`, `common/api_errors.py` | Exception-to-HTTP translation was partly shared and partly repeated inline, so equivalent failures could acquire different response behavior. | Stable categories now use the existing error helper across training, inference lifecycle, upload, and dataset deletion; upload size and dataset/checkpoint conflicts retain endpoint-specific status semantics. | Resolved incrementally |
| F-09 | P2 | `services/training.py`, `services/inference.py` | These services are large because they combine lifecycle state, orchestration, and response-shaped dictionaries. They are cohesive enough for the current application but expensive to unit-test at fine granularity. | Extract a cohesive state machine/monitor only when a behavior change creates a natural seam; do not split by arbitrary method count. | Incremental |
| F-10 | P2 | `client/src/components/inference/GameSession.tsx`, `client/src/utils/*Api.ts`, Training preview/dashboard components | Feature components combined fetch calls, payload parsing, local state, workflow orchestration, and rendering. Repeated requests could drift in loading/error behavior. | `trainingApi.ts` and `inferenceApi.ts` own their current request/response contracts. Training status has one polling hook; Training and Inference pages own local workflow snapshots, and parsers reject malformed/legacy shapes. | Resolved now |
| F-11 | P3 | `app/client/README.md` | The file was the untouched Vite template and did not explain the actual Training/Inference frontend. | Replace it with project-specific module and development guidance. | Resolved now |
| F-12 | P1 | `services/inference.py`, `api/inference.py` | Bounded in-memory inference sessions could be evicted or replaced without ending the persisted session; context clearing could remove inference datasets while a live session still referenced them. | `InferenceService` marks sessions ended before removing them for shutdown, replacement, or capacity eviction, and rejects context clearing while sessions are live with the existing `409 Conflict` mapping. Unit and API tests cover these lifecycle paths. | Resolved now |

## Dependency Direction Assessment

The current graph has a sound outer direction from composition/API toward services and persistence. Learning no longer imports repositories: `InferenceService` injects the prepared dataframe into `RoulettePlayer`, and `services/training_worker.py` owns process orchestration. The remaining repository-to-learning coupling is the checkpoint repository’s custom-layer registration import, required for Keras deserialization and kept explicit.

The new `test_architecture_boundaries.py` plus focused bootstrap, schema, checkpoint-lifecycle, and API-service tests protect the boundaries that can be enforced without inventing new interfaces.

## Target State

The target is still a local layered monolith:

1. The composition root explicitly loads configuration and constructs adapters.
2. API handlers depend on contracts and application services only.
3. Services own orchestration and receive learning/persistence collaborators.
4. Learning core depends on roulette/common primitives and explicit inputs, not global settings or database construction.
5. Persistence adapters own SQLAlchemy and checkpoint files; their names identify the dataset, inference, or checkpoint resource they own.
6. Database schema evolution is versioned and observable without destructive startup behavior.
7. Checkpoint and dataset lifecycle rules are explicit at the service boundary.
8. Frontend feature hooks own API calls and parsing while pages own workflow snapshots and components remain responsible for presentation.

This target does not require microservices, event queues, generic repositories, dependency-injection frameworks, or a new domain model hierarchy.

## Remediation Roadmap

### Phase 0 — Completed at the pushed checkpoint

- Rename `server.domain` to `server.contracts`.
- Consolidate roulette feature derivation.
- Add import-boundary regression coverage.
- Refresh architecture, persistence, API, coding, project-index, README, and frontend documentation.

### Phase 1 — Implemented incrementally in this change

- Define explicit environment/path/logger bootstrap while preserving launcher behavior.
- Move training data/configuration orchestration out of learning modules and pass concrete configuration/storage collaborators.
- Establish Alembic as the authoritative schema version and structural compatibility check; reject non-empty unversioned databases without runtime stamping.
- Add a checkpoint/dataset deletion policy and API conflict behavior.

### Phase 2 — Implemented selectively; remaining work deferred

- Collapse duplicate repository/query/serializer paths into resource-owned repositories.
- Consolidate stable HTTP error mapping.
- Add narrow feature-specific frontend API helpers and one training-status polling hook.
- Keep immutable dataset snapshots and distributed job/session persistence deferred because they are outside the local runtime scope.

## Validation Boundaries

The implementation must preserve the checked-in OpenAPI snapshot, all route paths/statuses for successful operations, database table/constraint behavior, checkpoint file layout, and frontend routes. Dataset deletion now has an explicit `409` conflict for referenced checkpoints, and inference context clearing returns `409` while an active session exists. Frontend CI runs `npm ci`, `npm run lint`, and `npm run build` on Node 22. Mermaid diagrams are source documentation and should be parsed/rendered in a temporary location when a Mermaid CLI is available. PostgreSQL contract validation is conditional on an available PostgreSQL service; it must not be reported as passed when unavailable.
