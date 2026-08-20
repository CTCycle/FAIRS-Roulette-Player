## Persistence

Last updated: 2026-08-20

## Current Persistence Model

The relational schema is defined directly by SQLAlchemy models in `app/server/repositories/schemas/models.py`. The repository contains no Alembic or other migration history. `Base.metadata.create_all()` creates a missing schema during explicit initialization; normal startup does not validate or migrate an existing database.

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
        float predicted_confidence "nullable"
        smallint observed_outcome_id "nullable"
        int reward "nullable"
        int capital_after
        datetime recorded_at
    }
```

## Tables and Relationships

### `datasets`

- Integer auto-increment primary key `dataset_id`.
- `dataset_kind` is constrained to `training` or `inference` by `ck_datasets_kind`.
- `dataset_name_key` stores the case-folded name used for replacement/import uniqueness.
- The pair `(dataset_kind, dataset_name_key)` is unique through `uq_datasets_kind_name_key`.
- `ix_datasets_kind_name` supports kind/name ordering and lookup.
- A dataset owns its outcome rows and inference sessions.

### `dataset_outcomes`

- Composite primary key `(dataset_id, sequence_index)` makes each sequence position unique within a dataset.
- `dataset_id` references `datasets.dataset_id` with `ON DELETE CASCADE`.
- `sequence_index >= 0` through `ck_dataset_outcomes_sequence`.
- `outcome_id` is restricted to the single-zero roulette range `0..36` through `ck_dataset_outcomes_outcome`.
- `ix_dataset_outcomes_dataset_outcome` supports dataset/outcome lookups.

### `inference_sessions`

- String `session_id` is the primary key and is normalized before persistence.
- `dataset_id` references `datasets.dataset_id` with `ON DELETE CASCADE`.
- `checkpoint_name` is a bounded filesystem checkpoint identifier, not a foreign key to a relational table.
- `initial_capital > 0` through `ck_inference_sessions_initial_capital`.
- `ended_at` is nullable for active sessions.
- `ix_inference_sessions_dataset_started` supports dataset history ordered by start time.

### `inference_session_steps`

- Composite primary key `(session_id, step_number)` makes each step unique within a session.
- `session_id` references `inference_sessions.session_id` with `ON DELETE CASCADE`.
- `step_number > 0` through `ck_inference_steps_step_number`, and `bet_amount > 0` through `ck_inference_steps_bet_amount`.
- `predicted_action` is bounded to `0..46` through `ck_inference_steps_action`, matching the model action space.
- `observed_outcome_id` is nullable and, when present, is bounded to `0..36` through `ck_inference_steps_observed_outcome`.
- `predicted_confidence` is nullable and, when present, is bounded to `0..1` through `ck_inference_steps_confidence`.
- `capital_after`, `recorded_at` are required.
- `ix_inference_steps_session_recorded` supports session history retrieval.

## Storage Surfaces

- **Embedded relational data:** `app/resources/database.db` by default, or `<FAIRS_DATA_DIR>/database.db` when a custom data root is configured.
- **External relational data:** PostgreSQL selected through `settings/.env` and validated at startup with a connection probe.
- **Checkpoints:** `<data-root>/checkpoints/<checkpoint_id>/` containing model files and JSON configuration/history.
- **Logs:** `<data-root>/logs/*.log`.

The checkpoint configuration stores values such as `dataset_id`, but the database cannot enforce a relationship to a checkpoint directory. This is a deliberate cross-storage boundary today and creates a lifecycle risk if a dataset is deleted while a checkpoint still expects it.

## Initialization Rules

- SQLite startup creates the schema only when the configured database file is missing. An existing file is not reset, reseeded, migrated, or schema-validated during normal startup.
- PostgreSQL startup does not create the database or schema. It only executes a non-mutating connection probe.
- The explicit launcher/database initializer creates or ensures the configured schema.
- There is no seed/catalog workflow.

## Persistence Boundaries

- API modules do not embed direct database logic.
- Dataset and inference operations flow through `DatasetRepository` and `InferenceRepository`, exposed to services through the `DataSerializer` facade.
- Training reads use `TrainingRepositoryQueries` and `TrainingDataSerializer`.
- Model/checkpoint files use `ModelSerializer` and `CheckpointService`, outside the relational schema.
- Schema, serializer, and API contract changes should be reviewed together.

## Architectural Assessment

The relational ownership and cascade rules are coherent for datasets, outcomes, sessions, and steps. The main persistence risks are the absence of migration/version checks for existing databases and the unenforced relationship between filesystem checkpoints and dataset lifecycle. Both are documented as incremental P1 recommendations; no schema change is included in this review.

## Related Files

- Read `execution_and_data_flow.md` for repository and serializer call chains.
- Read `../runtime/configuration.md` for database settings.
- Read `../runtime/startup.md` for initialization commands and lifecycle behavior.
- Read `findings_and_remediation.md` for schema-versioning and checkpoint lifecycle risks.
