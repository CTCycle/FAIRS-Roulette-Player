## Persistence

Last updated: 2026-07-11

## Database Backends

- SQLite is used when `EMBEDDED_DATABASE=true`.
- PostgreSQL is used when `EMBEDDED_DATABASE=false`.
- Backend selection is resolved from environment settings during startup.

## Core Tables

- `roulette_outcomes`
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

- Embedded SQLite auto-initializes on startup only when the database file is missing.
- PostgreSQL initialization is manual and is exposed as option 3 in `start_on_windows.ps1`.
- Startup validation ensures required resource directories exist before the app begins serving traffic.

## Persistence Boundaries

- API modules should not embed direct database logic.
- Persistence access flows through repository queries and serializers.
- Schema, serializer, and API contract changes should be updated together in the same change.

## Related Files

- Read `../../runtime/configuration.md` for the full environment variable surface.
- Read `execution_and_data_flow.md` for the repository and serializer layers that manage persistence.
