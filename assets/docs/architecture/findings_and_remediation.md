## Architecture Findings And Remediation

Last updated: 2026-10-21

## Audit Objective

This audit reviewed frontend, backend, persistence, API contracts, configuration, startup, training/inference execution, checkpoints, migrations, tests, CI, launcher behavior, and documentation with one rule: each responsibility should have one current canonical implementation.

The remediation intentionally removes compatibility aliases, hybrid old/new paths, duplicate defaults, silent fallback behavior, and runtime migration logic where no current external dependency requires them.

## Final Canonical Ownership

| Responsibility | Canonical implementation |
| --- | --- |
| HTTP schemas | `app/server/contracts` and FastAPI/Pydantic |
| Frontend transport types | generated `app/client/src/generated/api.ts` |
| Training defaults | `TrainingConfig` |
| Training semantic validation | `TrainingConfig`, exposed to the UI through `/api/training/validate` |
| Per-training device/mixed precision | `TrainingConfig` |
| Database connection settings | strict, versioned `<data-root>/database-config.json` managed by `DatabaseConfigurationStore` |
| Settings UI preferences | singleton `application_settings` row in the active database, managed by `SettingsService` |
| Active database connection | `RuntimeDatabaseManager` shared by repositories and services |
| Environment settings | typed environment configuration sourced from `settings/.env`, excluding database connection values |
| Relational schema | SQLAlchemy models at current Alembic head |
| Relational migration | Alembic only |
| Persisted checkpoint configuration | versioned `CheckpointConfiguration` |
| Supported checkpoint configuration | versioned `CheckpointConfiguration`; old unversioned files are rejected |
| Dataset SQL | `DatasetRepository` |
| Inference SQL | `InferenceRepository` |
| Checkpoint filesystem I/O | `CheckpointRepository` |
| Active training state | `TrainingRunManager` |
| Active inference state | `InferenceState` |
| Frontend workflow/view state | feature-local React state/hooks |
| Runtime lifecycle | FastAPI lifespan plus `bootstrap_runtime()` |
| Cache ownership | `runtimes/cache` with fixed tool-specific child directories |

## Removed Compatibility And Duplication

### Training configuration

Previously, training defaults and semantic rules existed in Pydantic, frontend code, service reconstruction, and downstream `.get(..., default)` calls. The current path is:

1. `TrainingConfig` defines defaults and cross-field invariants.
2. The frontend obtains generated defaults from the backend-derived transport artifact.
3. The wizard calls `/api/training/validate` instead of duplicating semantic validation.
4. `TrainingService` serializes the already validated model directly.
5. The worker revalidates once at the process boundary.
6. Learning code reads required keys directly and fails if the invariant is violated.

### Device settings

The hybrid JIT/mixed-precision ownership is removed. Global JIT settings live only in `ServerSettings.device`. GPU selection, device ID, and mixed precision are per-training settings owned by `TrainingConfig`.

### API transport contracts

The checked-in `app/shared/openapi.json` snapshot is removed. It was a second stored representation that could drift from the runtime contract.

FastAPI/Pydantic is authoritative. `app/scripts/generate_frontend_contracts.py` derives the checked-in TypeScript transport artifact and CI verifies it with `--check`. `export_openapi.py` remains only an on-demand renderer to stdout or an explicitly selected output path.

### Inference preference semantics

`confidence` and `predicted_confidence` are removed from current API/runtime/schema naming. The canonical names are `relative_preference` and `predicted_relative_preference`, reflecting that the value is a softmax-normalized relative Q-score preference rather than a calibrated probability.

The current baseline stores the canonical field directly. Databases created with previous schema revisions are rejected; no API alias preserves superseded field names.

### Checkpoint metadata and format

The `neurons` checkpoint-summary alias is removed. `qnet_neurons` is canonical end to end.

Checkpoint configuration is explicitly versioned. Runtime loading accepts the current format and rejects unversioned/unsupported data. No conversion utility or fallback path is retained for old checkpoint configuration.

### Strategy and action handling

Permissive strategy normalization and fallback-to-Keep behavior are removed. Fixed strategy mode remains a current supported mode, but identifiers must be valid and explicit.

The strategy model must return exactly the canonical five outputs. The Q model must return the canonical roulette action count. Invalid roulette actions raise instead of silently producing a neutral reward.

### Inference lifecycle

Unused inference state creation/cleanup and duplicate persistence helper paths were removed. `InferenceState` remains the live-session authority, while `InferenceRepository` owns persisted history.

The browser replay payload remains advisory. It does not become a second live-session store.

### Launcher

The Windows launcher no longer:

- stores lists of legacy cache paths;
- recursively discovers old cache directory conventions;
- supplements `.env` with a separate hardcoded default map;
- retries failed dependency sync by assuming an old-location virtual environment;
- includes obsolete root `.venv` or `.angular` paths in uninstall behavior.

Only current application-owned runtime, dependency, build, and cache locations are managed. Every disposable cache is created below `runtimes/cache`; the cleanup action empties that root while preserving its marker, removes source-tree `__pycache__` directories under `app/server`, and recreates child cache paths only when a later runtime operation needs them.

## Current Designs Intentionally Retained

These are current requirements, not legacy compatibility:

- SQLite and PostgreSQL support, because both use the same repository/schema architecture and are covered by persistence conformance tests.
- `X-Preserve-Inference-Session`, because it implements the current transactional replay/replacement workflow.
- Browser inference setup/replay metadata, because it is advisory and does not own the live model session.
- Fixed strategy mode, because it is a current explicit strategy-selection mode.
- The Keras custom-layer registration dependency in checkpoint loading, because it is required for current checkpoint deserialization.
- One backend worker, because active training and inference state is deliberately process-local.

## Migration Requirements

### Relational database

Normal application initialization creates an empty database at the sole `0001_current_schema` baseline. Previous revision IDs and non-empty unversioned schemas fail closed and are not modified; recreate such databases to use the current schema.

### Checkpoints

Only the current versioned checkpoint contract is supported. Unversioned or unsupported checkpoint files are rejected without modification.

### Existing `.env`

A missing `.env` is created from `.env.example`. Existing files are not patched automatically. Launcher-critical keys missing from an existing `.env` must be added explicitly from the current template.

## Regression Guards

The migration removed obsolete AppState paths, inference preference naming, permissive strategy helpers, stale polling helpers, the old OpenAPI snapshot, and launcher compatibility-cache behavior. The current unit suite protects current contracts directly (OpenAPI/schema parity, Alembic consistency, strict strategy/action invariants) rather than scanning for absence of the removed legacy paths.

Additional coverage verifies:

- current Alembic head and migration consistency;
- versioned checkpoint loading and unversioned checkpoint rejection;
- strict strategy/action invariants;
- training contract validation;
- inference persistence/lifecycle behavior;
- generated frontend contract parity;
- SQLite and PostgreSQL persistence conformance;
- frontend lint/type/build validation.

## Validation Priorities

The architecture has one local owner per responsibility, but ownership correctness does not by itself prove the end-to-end product path. The current validation campaign therefore follows the dependency chain `startup → persistence/settings → datasets → training → checkpoint → inference` and keeps the highest-risk boundary explicit: a real serialized checkpoint must load against its recorded dataset and produce a persisted initial inference prediction.

The campaign is tracked by the consolidated, code-backed gate register in [`../project_status_ledger.md`](../project_status_ledger.md). `VAL-00` establishes a disposable real lineage; `VAL-01` refreshes launcher/startup evidence; `VAL-11` begins the live checkpoint-backed inference campaign. All registered `VAL-*` functional gates are currently passed for their recorded profiles; `STARTUP-01` remains `PARTIAL` only because the protected canonical Python/cache boundary prevented one cold-launch path from completing, while the isolated-cache live launch passed. The frontend workflow is also `PARTIAL` for spoken screen-reader evidence because DOM, accessibility-tree, keyboard, and visual checks do not replace user-controlled Narrator/Speech Recap observation. Inference replay/replacement remains a separate state-transition risk, while PostgreSQL, CUDA, mixed precision, and unsupported JIT behavior remain environment-specific gates. A passing unit suite or HTTP health response does not close those boundaries.

## Final Architecture

The target architecture is the current architecture after this remediation: one local layered monolith, one explicit owner per responsibility, strict failure for unsupported old states, and a single current database baseline.

No permanent runtime compatibility layer is retained solely because an older implementation once existed.
