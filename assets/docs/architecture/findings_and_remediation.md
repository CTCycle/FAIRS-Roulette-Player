## Architecture Findings And Remediation

Last updated: 2026-09-10

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
| Global JIT/compiler settings | `ServerSettings.device` |
| Environment/database settings | typed environment configuration sourced from `settings/.env` |
| Relational schema | SQLAlchemy models at current Alembic head |
| Relational migration | Alembic only |
| Persisted checkpoint configuration | versioned `CheckpointConfiguration` |
| Old checkpoint conversion | one-time `app/scripts/migrate_checkpoints.py` |
| Dataset SQL | `DatasetRepository` |
| Inference SQL | `InferenceRepository` |
| Checkpoint filesystem I/O | `CheckpointRepository` |
| Active training state | `TrainingRunManager` |
| Active inference state | `InferenceState` |
| Frontend workflow/view state | feature-local React state/hooks |
| Runtime lifecycle | FastAPI lifespan plus `bootstrap_runtime()` |
| Launcher cache roots | `runtimes/cache`, `app/tests/cache` |

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

Alembic revision `0002_rename_relative_preference` performs the database rename. No API alias preserves the superseded field name.

### Checkpoint metadata and format

The `neurons` checkpoint-summary alias is removed. `qnet_neurons` is canonical end to end.

Checkpoint configuration is explicitly versioned. Runtime loading accepts the current format and rejects unversioned/unsupported data. The known old unversioned format is handled only by the one-time migration script, which performs full preflight validation before atomic writes.

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

Only current application-owned runtime, dependency, build, and cache locations are managed.

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

Normal application initialization runs Alembic to current `head`. Revision `0002_rename_relative_preference` renames the persisted inference preference field and check constraint.

### Checkpoints

For existing unversioned checkpoint configuration files, run a read-only preflight first:

```powershell
$env:PYTHONPATH='app'
uv --project app/server run python app/scripts/migrate_checkpoints.py
```

If every checkpoint is recognized and valid:

```powershell
uv --project app/server run python app/scripts/migrate_checkpoints.py --apply
```

Unsupported or incomplete checkpoint formats are rejected rather than normalized with current defaults.

### Existing `.env`

A missing `.env` is created from `.env.example`. Existing files are not patched automatically. Launcher-critical keys missing from an existing `.env` must be added explicitly from the current template.

## Regression Guards

`app/tests/unit/test_architecture_cleanup.py` protects removed paths and names, including old AppState paths, obsolete inference preference naming, permissive strategy helpers, stale polling helpers, the old OpenAPI snapshot, and launcher compatibility-cache behavior.

Additional coverage verifies:

- current Alembic head and migration consistency;
- versioned checkpoint loading and migration behavior;
- strict strategy/action invariants;
- training contract validation;
- inference persistence/lifecycle behavior;
- generated frontend contract parity;
- SQLite and PostgreSQL persistence conformance;
- frontend lint/type/build validation.

## Final Architecture

The target architecture is the current architecture after this remediation: one local layered monolith, one explicit owner per responsibility, strict failure for unsupported old states, and explicit one-time migrations for persisted data that genuinely requires conversion.

No permanent runtime compatibility layer is retained solely because an older implementation once existed.
