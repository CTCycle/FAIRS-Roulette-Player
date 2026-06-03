## Persistence

Last updated: 2026-06-02

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
  - `app/resources/database.db`
- External relational data:
  - PostgreSQL database defined by the configured connection settings
- Checkpoints:
  - `app/resources/checkpoints/<checkpoint_id>/...`
- Logs:
  - `app/resources/logs/*.log`

## Initialization Rules

- Embedded SQLite auto-initializes on startup only when the database file is missing.
- PostgreSQL initialization is manual and is exposed through the maintenance script.
- Startup validation ensures required resource directories exist before the app begins serving traffic.

## Persistence Boundaries

- API modules should not embed direct database logic.
- Persistence access flows through repository queries and serializers.
- Schema, serializer, and API contract changes should be updated together in the same change.

## Related Files

- Read `../../runtime/configuration.md` for the full environment variable surface.
- Read `execution_and_data_flow.md` for the repository and serializer layers that manage persistence.
