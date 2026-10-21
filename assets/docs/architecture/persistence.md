## Persistence

Last updated: 2026-10-21

## Canonical Persistence Model

The relational schema is defined by SQLAlchemy models in `app/server/repositories/schemas/models.py`. Alembic is the only schema-evolution mechanism. Runtime initialization never calls `Base.metadata.create_all()` and never stamps or repairs an unknown schema.

The current migration history is one baseline, `0001_current_schema`, containing the complete current model schema. Databases stamped with previous revisions are rejected; recreate them to use this schema. Startup never deletes or rewrites an existing database.

```mermaid
erDiagram
    DATASETS ||--o{ DATASET_OUTCOMES : contains
    DATASETS ||--o{ INFERENCE_SESSIONS : supplies
    INFERENCE_SESSIONS ||--o{ INFERENCE_SESSION_STEPS : records

    DATASETS {
        int dataset_id PK
        string dataset_name
        string dataset_name_key
        string dataset_kind
        datetime created_at
        datetime updated_at
    }

    DATASET_OUTCOMES {
        int dataset_id PK, FK
        int sequence_index PK
        smallint outcome_id
    }

    INFERENCE_SESSIONS {
        string session_id PK
        int dataset_id FK
        string checkpoint_name
        int initial_capital
        datetime started_at
        datetime ended_at "nullable"
    }

    INFERENCE_SESSION_STEPS {
        string session_id PK, FK
        int step_number PK
        int bet_amount
        int predicted_action
        float predicted_relative_preference "nullable"
        smallint observed_outcome_id "nullable"
        int reward "nullable"
        int capital_after
        datetime recorded_at
    }

    APPLICATION_SETTINGS {
        int settings_id PK "singleton id 1"
        json jobs
        json device
        json roulette
    }
```

## Tables and Relationships

### `datasets`

- `dataset_id` is the integer primary key.
- `dataset_kind` is constrained to `training` or `inference`.
- `(dataset_kind, dataset_name_key)` is unique.
- Dataset outcomes and inference sessions are owned by the dataset and cascade on deletion where permitted by application policy.

### `dataset_outcomes`

- `(dataset_id, sequence_index)` is the composite primary key.
- `outcome_id` is constrained to the single-zero roulette range `0..36`.

### `inference_sessions`

- `session_id` is the normalized string primary key.
- `dataset_id` references `datasets.dataset_id`.
- `checkpoint_name` identifies a filesystem checkpoint, not a relational checkpoint row.
- `ended_at` is nullable while a persisted session is active.

### `inference_session_steps`

- `(session_id, step_number)` is the composite primary key.
- `predicted_action` is constrained to `0..46`, matching the canonical action space.
- `predicted_relative_preference` is nullable and, when present, is constrained to `0..1` by `ck_inference_steps_relative_preference`.
- `observed_outcome_id` is nullable and constrained to `0..36` when present.
- `reward` is nullable until an outcome is supplied.

### `application_settings`

- `settings_id` is constrained to the singleton value `1`.
- `jobs`, `device`, and `roulette` store the validated Settings UI contracts as JSON.
- A new database is seeded with backend defaults when this row does not exist. Settings are never imported from files; runtime database switching never copies the row or other data.

## Storage Surfaces

- Database connection configuration: `<data-root>/database-config.json`, independent of the selected database. It stores only the backend and connection details; PostgreSQL passwords are protected with Windows DPAPI for the current user.
- Embedded relational data: `data/database.db` by default, or the configured SQLite file when a custom data root or path is selected.
- External relational data: PostgreSQL through the same repository/schema model when selected in the Database section of Settings.
- Checkpoints: `<data-root>/checkpoints/<checkpoint_id>/`.
- Logs: `<data-root>/logs/*.log`.
- Application settings: the `application_settings` row in the active database.

The Settings page persists each valid non-database control change through `PATCH /api/settings`; numeric and text fields use a short debounce. Database connection fields remain a client draft until the explicit switch action succeeds, then the standalone configuration file is atomically updated. Neither ordinary UI settings nor their runtime values are stored in that connection file.

Application settings are relational data. The standalone JSON database configuration is not stored in or read from the database, avoiding a circular initialization dependency. Missing settings rows receive current defaults; old settings files are ignored.

SQLite and PostgreSQL are both supported persistence modes. They use the same SQLAlchemy schema, repositories, Alembic chain, and service contracts. Live switching drains in-flight database operations and is rejected while training or inference is active; each target database remains an independent data store.

## Database Initialization Rules

`server.repositories.database.initializer.initialize_database()` is the single create/upgrade runner used by FastAPI lifespan, the CLI, and the Windows launcher.

- Empty databases upgrade to Alembic `head`.
- Empty databases upgrade to `head`, and known revisions in the current migration chain upgrade in order.
- A database already at `head` receives strict metadata validation and otherwise remains unchanged.
- Non-empty unversioned databases are rejected unchanged.
- Removed historical revisions, unknown or ahead revisions, multiple heads, and structural drift fail before services start.
- There is no runtime adoption, compatibility stamping, destructive reset, or automatic schema repair.
- SQLite serializes migrations with `BEGIN IMMEDIATE`.
- PostgreSQL uses advisory locks for database creation and target migrations.

## Versioned Checkpoint Contract

Checkpoint JSON is explicit and versioned. `CheckpointConfiguration` in `app/server/contracts/training.py` is the persisted contract and currently requires:

```text
format_version = 1
training = complete TrainingConfig payload
```

`CheckpointRepository` saves this versioned shape and rejects unversioned, incomplete, or unsupported checkpoint configuration at runtime. Old checkpoint files are not converted or modified; only current versioned checkpoints are supported.

## Checkpoint and Dataset Ownership

- `CheckpointRepository` owns checkpoint filesystem I/O and persisted checkpoint validation.
- `CheckpointService` owns checkpoint lifecycle policy.
- `DatasetRepository` owns dataset SQL persistence.
- `InferenceRepository` owns inference session and step persistence.
- Dataset deletion scans checkpoint metadata first. A referenced dataset or unreadable checkpoint configuration blocks deletion rather than creating a broken cross-storage reference.
- Active inference model objects remain process-local and are not reconstructed from persisted session history after restart.

## Development Migration Workflow

From `app/server`, create and review a new Alembic revision rather than editing an existing migration:

```powershell
uv run alembic -c alembic.ini revision --autogenerate -m "describe schema change"
uv run alembic -c alembic.ini check
uv run alembic -c alembic.ini current --check-heads
uv run alembic -c alembic.ini upgrade head
```

This baseline contains the current schema. Future schema changes must be represented by new migrations; do not edit the baseline after release.

## Related Files

- Read `execution_and_data_flow.md` for persistence call chains.
- Read `../runtime/configuration.md` for database selection.
- Read `../runtime/startup.md` for startup and migration behavior.
