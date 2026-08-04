## Persistence

Last updated: 2026-08-03

## Database Backends

- SQLite is used when `EMBEDDED_DATABASE=true`.
- PostgreSQL is used when `EMBEDDED_DATABASE=false`.
- Backend selection is resolved from environment settings during startup.

## Core Tables

- `datasets`
- `dataset_outcomes`
- `inference_sessions`
- `inference_session_steps`

The schema enforces roulette outcome ranges, positive session/step values, bounded predicted confidence, dataset-kind values, and cascading cleanup from datasets to outcomes and inference sessions.

## Storage Surfaces

- Embedded relational data:
  - `app/resources/database.db` by default
  - `<FAIRS_USER_DATA_DIR>/database.db` when a custom data root is configured
- External relational data:
  - PostgreSQL database defined by the configured connection settings
- Checkpoints:
  - `<data-root>/checkpoints/<checkpoint_id>/...`
- Logs:
  - `<data-root>/logs/*.log`

## Initialization Rules

- Application startup uses different lifecycle rules for the selected backend.
- Embedded SQLite checks only whether the configured database file exists. A missing file is created through SQLAlchemy metadata; an existing file is not initialized, reseeded, reset, or schema-validated during normal startup.
- PostgreSQL is not created or initialized during normal startup. Startup only runs a non-mutating connection probe against the configured database.
- The explicit initializer creates or ensures the PostgreSQL database and schema after the user selects option 3 in `start_on_windows.ps1`.
- The current schema has no applicable seed workflow; initialization does not add or reseed catalog data.

## Persistence Boundaries

- API modules should not embed direct database logic.
- Persistence access flows through explicit dataset/inference repositories, training queries, and serializers.
- Schema, serializer, and API contract changes should be updated together in the same change.

## Related Files

- Read `../../runtime/configuration.md` for the full environment variable surface.
- Read `execution_and_data_flow.md` for the repository and serializer layers that manage persistence.
