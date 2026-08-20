## Architecture Findings And Remediation

Last updated: 2026-08-20

## Review Scope And Method

This review traced the checked-in Python and TypeScript source, FastAPI composition/wiring, route decorators, SQLAlchemy models, repository calls, filesystem checkpoint paths, frontend imports and fetch calls, tests, CI, and existing documentation. Dependency statements below are derived from those sources. Generated bundles, dependency directories, caches, and screenshots were excluded from the structural inventory.

The current baseline is healthy: backend unit tests, Ruff, frontend lint, and the frontend production build pass. No P0 issue was found, and no confirmed circular dependency exists in the meaningful application module graph.

## Current State

FAIRS is a layered local monolith:

- React/Vite presents Training and Inference routes and owns browser state, interaction, defensive payload parsing, and polling.
- FastAPI routers expose `/api/*`, validate transport contracts, translate selected exceptions, and delegate to services.
- Application services own dataset import, checkpoints, training jobs, inference session state, and lifecycle orchestration.
- Learning modules contain betting rules, neural models, training environments, inference players, and worker-process entrypoints.
- Repositories own SQLAlchemy schema/transactions, dataset and session persistence, training queries, and checkpoint/model file serialization.
- Configuration resolves `.env` and JSON settings; common modules provide paths, constants, logging, normalization, errors, and roulette feature encoding.

The repository is designed for one local backend process. Jobs and active inference sessions are in memory; training work runs in a child process; relational history and checkpoint files are durable but are not a distributed coordination mechanism.

See `system_overview.md`, `execution_and_data_flow.md`, and `persistence.md` for the source-derived diagrams.

## Strengths To Preserve

- `app/server/app.py` is a clear composition root that wires concrete dependencies during lifespan startup.
- API modules delegate to services and do not issue SQLAlchemy queries directly.
- Dataset, session, and step persistence has explicit transaction scopes, composite keys, foreign keys, cascades, uniqueness constraints, and value checks.
- Training is isolated from request handling through a monitored worker process and a polling API.
- The checked-in OpenAPI snapshot is generated from the FastAPI application and checked in CI.
- Tests cover service behavior, API workflows, persistence behavior, startup/configuration, and security-sensitive paths.
- The local in-memory job/session model is appropriate for the documented single-process runtime; distributed persistence would add complexity without a current deployment requirement.

## Findings

| ID | Priority | Location | Description and impact | Preferred solution | Timing |
| --- | --- | --- | --- | --- | --- |
| F-01 | P1 | `app/server/domain/*` (renamed to `contracts/*`) | The package contained Pydantic transport/configuration contracts, not framework-independent domain entities. The name made dependency direction and ownership ambiguous for new contributors. | Use `server.contracts` and describe these objects as boundary contracts. Do not create a speculative domain layer. | Resolved now |
| F-02 | P1 | Former `services/process.py`, `learning/training/serializer.py`, `repositories/queries/training.py` | Roulette wheel/color feature derivation existed in both learning-adjacent and repository code. Drift could produce different training features for generated versus persisted data. | Use one narrow `common.roulette.encode_roulette_series` transformation. | Resolved now |
| F-03 | P1 | `server/__init__.py`, `common/path.py`, `common/utils/logger.py`, `configurations/environment.py` | Importing the package loads/creates `.env` and initializes paths/logging from environment variables. Import order therefore has observable filesystem and configuration side effects. | Introduce an explicit bootstrap boundary: load environment and construct runtime paths/logging from the composition root, then pass settings to consumers. Preserve launcher behavior and migrate tests incrementally. | Incremental |
| F-04 | P1 | `learning/training/serializer.py`, `learning/training/worker.py`, `learning/models/qnet.py`, `learning/training/fitting.py` | ML execution code constructs `FAIRSDatabase` and repository queries and reads global server settings. This couples computation to persistence/configuration and makes isolated learning tests harder. | Move process/data orchestration toward an application-owned worker and inject storage/configuration values; keep learning core focused on models, betting, and environments. | Incremental |
| F-05 | P1 | `repositories/database/backend.py`, `initializer.py`, `schemas/models.py` | SQLAlchemy metadata is the schema source of truth, but existing databases are not version-checked or migrated during normal startup. A future model change can leave an existing SQLite/PostgreSQL schema stale. | Adopt an explicit schema-version/migration policy before the next incompatible schema change; keep normal startup non-destructive and make upgrades observable. | Incremental |
| F-06 | P1 | `repositories/serialization/model.py`, checkpoint JSON, `services/datasets.py` | Checkpoint configuration can retain a `dataset_id`, while dataset deletion cascades relational rows without inspecting checkpoint directories. A retained checkpoint may become unusable or misleading after its dataset is deleted. | Add a checkpoint-reference scan or explicit delete policy and return a conflict with affected checkpoints; later consider storing an immutable dataset snapshot only if the workflow requires it. | Incremental |
| F-07 | P2 | `repositories/serialization/data.py`, `repositories/serialization/training.py` | `DataSerializer` is primarily a pass-through facade over repositories, while `TrainingDataSerializer` performs sampling and `ModelSerializer` performs filesystem I/O. The shared “serialization” name obscures different responsibilities. | Rename or consolidate only when a service is next changed; keep domain-specific repository methods rather than adding generic repositories. | Incremental |
| F-08 | P2 | `api/training.py`, `api/inference.py`, `api/upload.py`, `common/api_errors.py` | Exception-to-HTTP translation is partly shared and partly repeated inline, so equivalent failures can acquire different response behavior. | Centralize only stable exception categories in the existing error helper; retain endpoint-specific status semantics for upload size and resource conflicts. | Incremental |
| F-09 | P2 | `services/training.py`, `services/inference.py` | These services are large because they combine lifecycle state, orchestration, and response-shaped dictionaries. They are cohesive enough for the current application but expensive to unit-test at fine granularity. | Extract a cohesive state machine/monitor only when a behavior change creates a natural seam; do not split by arbitrary method count. | Incremental |
| F-10 | P2 | `client/src/components/inference/GameSession.tsx`, Training preview/dashboard components | Feature components combine fetch calls, payload parsing, local state, workflow orchestration, and rendering. Repeated dataset/checkpoint requests can drift in loading/error behavior. | Add narrow feature API hooks/client helpers during future UI changes, keeping route composition and state ownership unchanged. | Incremental |
| F-11 | P3 | `app/client/README.md` | The file was the untouched Vite template and did not explain the actual Training/Inference frontend. | Replace it with project-specific module and development guidance. | Resolved now |

## Dependency Direction Assessment

The current graph has a sound outer direction from composition/API toward services and persistence. The main violations are not API-to-database leaks or circular imports; they are lower-level learning modules reaching into repositories/configuration and repository checkpoint loading importing learning model registration. These edges are explicit and testable, but they reduce substitution and isolated testing.

The new `test_architecture_boundaries.py` protects the boundaries that can be enforced without inventing new interfaces. It intentionally does not pretend that F-03 through F-06 are already solved.

## Target State

The target is still a local layered monolith:

1. The composition root explicitly loads configuration and constructs adapters.
2. API handlers depend on contracts and application services only.
3. Services own orchestration and receive learning/persistence collaborators.
4. Learning core depends on roulette/common primitives and explicit inputs, not global settings or database construction.
5. Persistence adapters own SQLAlchemy and checkpoint files; their names describe whether they query, serialize, or store.
6. Database schema evolution is versioned and observable without destructive startup behavior.
7. Checkpoint and dataset lifecycle rules are explicit at the service boundary.
8. Frontend feature hooks own API calls and parsing while pages/components remain responsible for workflow and presentation.

This target does not require microservices, event queues, generic repositories, dependency-injection frameworks, or a new domain model hierarchy.

## Remediation Roadmap

### Phase 0 — Completed in this review

- Rename `server.domain` to `server.contracts`.
- Consolidate roulette feature derivation.
- Add import-boundary regression coverage.
- Refresh architecture, persistence, API, coding, project-index, README, and frontend documentation.

### Phase 1 — Next high-value runtime work

- Define explicit environment/path/logger bootstrap while preserving launcher behavior.
- Move training worker/data-access orchestration out of learning modules and pass concrete configuration/storage collaborators.
- Establish schema versioning before changing relational models.
- Add a checkpoint/dataset deletion policy and API conflict behavior.

### Phase 2 — Opportunistic maintainability work

- Clarify repository/serializer ownership and reduce pass-through facades.
- Consolidate stable HTTP error mapping.
- Extract feature-level frontend API hooks from the largest components.
- Split service state machines only at tested behavioral seams.

## Validation Boundaries

The implementation must preserve the checked-in OpenAPI snapshot, all route paths/statuses, database table/constraint behavior, checkpoint file layout, and frontend routes. Mermaid diagrams are source documentation and should be parsed/rendered in a temporary location when a Mermaid CLI is available. PostgreSQL contract validation is conditional on an available PostgreSQL service; it must not be reported as passed when unavailable.
