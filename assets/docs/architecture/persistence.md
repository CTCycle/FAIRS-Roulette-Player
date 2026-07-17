## Persistence

Last updated: 2026-07-14

## Database Backends

- SQLite is used when `EMBEDDED_DATABASE=true`.
- PostgreSQL is used when `EMBEDDED_DATABASE=false`.
- Backend selection is resolved from environment settings during startup.

## Core Tables

- `datasets`
- `dataset_outcomes`
- `inference_sessions`
- `inference_session_steps`

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

- Embedded SQLite creates the canonical schema on startup.
- PostgreSQL initialization is manual and is exposed as option 3 in `start_on_windows.ps1`.
- Startup validates that the canonical tables exist before serving traffic.
- This is a clean schema cutover: an existing legacy database must be recreated or
  migrated before startup; the application does not retain the five-table CRUD
  compatibility layer.

## Persistence Boundaries

- API modules should not embed direct database logic.
- Persistence access flows through explicit dataset/inference repositories, training queries, and serializers.
- Schema, serializer, and API contract changes should be updated together in the same change.

## Related Files

- Read `../../runtime/configuration.md` for the full environment variable surface.
- Read `execution_and_data_flow.md` for the repository and serializer layers that manage persistence.
