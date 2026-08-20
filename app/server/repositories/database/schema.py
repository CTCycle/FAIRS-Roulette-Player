from __future__ import annotations

from sqlalchemy import Engine, inspect

from server.repositories.schemas.models import Base

CURRENT_SCHEMA_VERSION = 1

###############################################################################
def create_schema(engine: Engine) -> None:
    """Create the current schema and record a native SQLite version marker."""
    Base.metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.exec_driver_sql(
                f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}"
            )

###############################################################################
def _sqlite_schema_version(engine: Engine) -> int | None:
    if engine.dialect.name != "sqlite":
        return None
    with engine.connect() as connection:
        value = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
    return int(value)

###############################################################################
def validate_schema(engine: Engine) -> None:
    """Fail fast when an existing database is structurally stale or newer."""
    inspector = inspect(engine)
    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            missing.append(f"table {table.name}")
            continue
        existing_columns = {
            column["name"] for column in inspector.get_columns(table.name)
        }
        for column in table.columns:
            if column.name not in existing_columns:
                missing.append(f"column {table.name}.{column.name}")

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Database schema is incompatible with version {CURRENT_SCHEMA_VERSION}; "
            f"missing {joined}. Run the explicit database initialization/migration "
            "workflow before starting the application."
        )

    version = _sqlite_schema_version(engine)
    if version is not None and version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} is newer than the supported version "
            f"{CURRENT_SCHEMA_VERSION}."
        )


__all__ = ["CURRENT_SCHEMA_VERSION", "create_schema", "validate_schema"]
