from __future__ import annotations

from hashlib import sha256
import re
from pathlib import Path
from typing import Any

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
import sqlalchemy
from sqlalchemy import DateTime, Engine, Float, Integer, SmallInteger, String, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from server.common.utils.logger import logger
from server.configurations import DatabaseSettings
from server.configurations.startup import get_server_settings
from server.repositories.database.postgres import build_postgres_engine
from server.repositories.database.sqlite import build_sqlite_engine
from server.repositories.database.utils import (
    build_postgres_connect_args,
    is_supported_postgres_engine,
)
from server.repositories.schemas.models import Base

###############################################################################
ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"
ALEMBIC_VERSION_TABLE = "alembic_version"
MIGRATION_LOCK_TIMEOUT_SECONDS = 30


class DatabaseInitializationError(RuntimeError):
    """Base error raised when the database cannot be initialized safely."""


class DatabaseMigrationError(DatabaseInitializationError):
    """Raised when Alembic cannot apply or validate a migration state."""


class DatabaseSchemaDriftError(DatabaseMigrationError):
    """Raised when a database schema differs from the current model metadata."""


class DatabaseRevisionError(DatabaseMigrationError):
    """Raised when database or script revisions are not a supported linear state."""


class DatabaseMigrationLockError(DatabaseMigrationError):
    """Raised when the bounded migration lock wait expires."""


###############################################################################
def build_postgres_url(settings: DatabaseSettings, database_name: str) -> sqlalchemy.URL:
    if not is_supported_postgres_engine(settings.engine):
        raise DatabaseInitializationError(
            f"Unsupported database engine: {settings.engine}"
        )
    return sqlalchemy.URL.create(
        drivername=settings.engine.strip().lower(),
        username=settings.username or "",
        password=settings.password or "",
        host=settings.host,
        port=settings.port or 5432,
        database=database_name,
    )


###############################################################################
def escape_postgres_identifier(identifier: str) -> str:
    return identifier.replace('"', '""')


###############################################################################
def _sqlstate(exc: BaseException) -> str | None:
    original = getattr(exc, "orig", None)
    return getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)


###############################################################################
def is_missing_postgres_database_error(exc: SQLAlchemyError) -> bool:
    """Return true only for PostgreSQL's missing-database SQLSTATE."""
    return _sqlstate(exc) == "3D000"


###############################################################################
def _redact_error(value: object) -> str:
    message = str(value)
    message = re.sub(
        r"(://[^\s:/@]+:)[^\s/@]+@",
        r"\1***@",
        message,
    )
    message = re.sub(
        r"((?:password|passwd)\s*[=:]\s*)[^\s,;]+",
        r"\1***",
        message,
        flags=re.IGNORECASE,
    )
    return message


###############################################################################
def _advisory_lock_key(
    namespace: str,
    *,
    engine: str | None,
    host: str | None,
    port: int | None,
    database_name: str | None,
) -> int:
    material = "|".join(
        (
            namespace,
            engine or "",
            host or "",
            str(port or 5432),
            database_name or "",
        )
    ).encode("utf-8")
    return int.from_bytes(sha256(material).digest()[:8], byteorder="big", signed=True)


###############################################################################
def _engine_advisory_lock_key(engine: Engine) -> int:
    url = engine.url
    return _advisory_lock_key(
        "fairs:migrations:v1",
        engine=url.drivername,
        host=url.host,
        port=url.port,
        database_name=url.database,
    )


###############################################################################
def _alembic_config(connection: Any, config_path: Path | None = None) -> Config:
    path = config_path or ALEMBIC_CONFIG_PATH
    config = Config(str(path))
    config.attributes["connection"] = connection
    return config


###############################################################################
def _include_object(
    _object: Any,
    name: str,
    object_type: str,
    _reflected: bool,
    _compare_to: Any,
) -> bool:
    return not (object_type == "table" and name == ALEMBIC_VERSION_TABLE)


###############################################################################
def _alembic_diffs(connection: Any) -> list[Any]:
    migration_context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "compare_server_default": True,
            "include_object": _include_object,
            "render_as_batch": connection.dialect.name == "sqlite",
        },
    )
    return list(compare_metadata(migration_context, Base.metadata))


###############################################################################
def _normalize_sql_expression(value: object) -> str:
    expression = re.sub(r"\s+", " ", str(value)).strip().lower()
    while expression.startswith("(") and expression.endswith(")"):
        depth = 0
        balanced = True
        for index, character in enumerate(expression):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(expression) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        expression = expression[1:-1].strip()
    return expression


###############################################################################
def _type_signature(value: Any, *, dialect_name: str | None = None) -> tuple[Any, ...]:
    implementation = getattr(value, "impl", value)
    if isinstance(implementation, String):
        return ("string", implementation.length)
    if isinstance(implementation, SmallInteger):
        return ("smallinteger",)
    if isinstance(implementation, Integer):
        return ("integer",)
    if isinstance(implementation, Float):
        return ("float", implementation.precision, implementation.asdecimal)
    if isinstance(implementation, DateTime):
        timezone = False if dialect_name == "sqlite" else implementation.timezone
        return ("datetime", timezone)
    affinity = getattr(implementation, "_type_affinity", None)
    affinity_name = getattr(affinity, "__name__", type(implementation).__name__)
    return (affinity_name.lower(), str(implementation).lower())


###############################################################################
def _ondelete(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().upper()


###############################################################################
def _model_signature(*, dialect_name: str | None = None) -> dict[str, Any]:
    signature: dict[str, Any] = {}
    for table in Base.metadata.sorted_tables:
        indexes = tuple(
            sorted(
                (
                    index.name,
                    tuple(column.name for column in index.columns),
                    bool(index.unique),
                )
                for index in table.indexes
                if index.name
            )
        )
        unique_constraints = tuple(
            sorted(
                (
                    constraint.name,
                    tuple(column.name for column in constraint.columns),
                )
                for constraint in table.constraints
                if isinstance(constraint, sqlalchemy.UniqueConstraint)
                and constraint.name
            )
        )
        checks = tuple(
            sorted(
                (
                    constraint.name,
                    _normalize_sql_expression(constraint.sqltext),
                )
                for constraint in table.constraints
                if isinstance(constraint, sqlalchemy.CheckConstraint)
                and constraint.name
            )
        )
        foreign_keys = tuple(
            sorted(
                (
                    tuple(element.parent.name for element in constraint.elements),
                    constraint.elements[0].column.table.name,
                    tuple(element.column.name for element in constraint.elements),
                    _ondelete(constraint.elements[0].ondelete),
                )
                for constraint in table.foreign_key_constraints
            )
        )
        signature[table.name] = {
            "columns": tuple(
                (
                    column.name,
                    _type_signature(column.type, dialect_name=dialect_name),
                    bool(column.nullable),
                )
                for column in table.columns
            ),
            "primary_key": tuple(column.name for column in table.primary_key.columns),
            "indexes": indexes,
            "unique_constraints": unique_constraints,
            "checks": checks,
            "foreign_keys": foreign_keys,
        }
    return signature


###############################################################################
def _database_signature(connection: Any) -> dict[str, Any]:
    inspector = inspect(connection)
    signature: dict[str, Any] = {}
    for table_name in sorted(
        name
        for name in inspector.get_table_names()
        if name != ALEMBIC_VERSION_TABLE
    ):
        columns = tuple(
            (
                column["name"],
                _type_signature(column["type"], dialect_name=connection.dialect.name),
                bool(column["nullable"]),
            )
            for column in inspector.get_columns(table_name)
        )
        primary_key = tuple(
            inspector.get_pk_constraint(table_name).get("constrained_columns") or ()
        )
        indexes = tuple(
            sorted(
                (
                    index["name"],
                    tuple(index.get("column_names") or ()),
                    bool(index.get("unique")),
                )
                for index in inspector.get_indexes(table_name)
                if index.get("name")
            )
        )
        unique_constraints = tuple(
            sorted(
                (
                    constraint.get("name"),
                    tuple(constraint.get("column_names") or ()),
                )
                for constraint in inspector.get_unique_constraints(table_name)
                if constraint.get("name")
            )
        )
        checks = tuple(
            sorted(
                (
                    constraint.get("name"),
                    _normalize_sql_expression(constraint.get("sqltext", "")),
                )
                for constraint in inspector.get_check_constraints(table_name)
                if constraint.get("name")
            )
        )
        foreign_keys = tuple(
            sorted(
                (
                    tuple(foreign_key.get("constrained_columns") or ()),
                    foreign_key.get("referred_table"),
                    tuple(foreign_key.get("referred_columns") or ()),
                    _ondelete((foreign_key.get("options") or {}).get("ondelete")),
                )
                for foreign_key in inspector.get_foreign_keys(table_name)
            )
        )
        signature[table_name] = {
            "columns": columns,
            "primary_key": primary_key,
            "indexes": indexes,
            "unique_constraints": unique_constraints,
            "checks": checks,
            "foreign_keys": foreign_keys,
        }
    return signature


###############################################################################
def validate_database_metadata(connection: Any) -> None:
    """Require both Alembic's comparison and exact structural signatures to match."""
    diffs = _alembic_diffs(connection)
    if diffs:
        rendered = _redact_error(repr(diffs[:8]))
        raise DatabaseSchemaDriftError(
            "Database schema drift detected by Alembic metadata comparison. "
            f"Review the schema before retrying; differences: {rendered}"
        )

    expected = _model_signature(dialect_name=connection.dialect.name)
    actual = _database_signature(connection)
    if actual != expected:
        expected_tables = ", ".join(sorted(expected))
        actual_tables = ", ".join(sorted(actual))
        raise DatabaseSchemaDriftError(
            "Database schema does not exactly match the current SQLAlchemy metadata "
            f"(expected tables: {expected_tables}; detected tables: {actual_tables}). "
            "Automatic repair is disabled; inspect and explicitly migrate the database."
        )


###############################################################################
def _current_heads(connection: Any) -> tuple[str, ...]:
    context = MigrationContext.configure(connection)
    return tuple(context.get_current_heads())


###############################################################################
def _script_and_head(config: Config) -> tuple[ScriptDirectory, str]:
    script = ScriptDirectory.from_config(config)
    heads = tuple(script.get_heads())
    if len(heads) != 1:
        found = ", ".join(heads) or "none"
        raise DatabaseRevisionError(
            "Alembic script directory must have exactly one head; "
            f"detected {len(heads)} ({found}). Resolve the branch before startup."
        )
    return script, heads[0]


###############################################################################
def _pending_revisions(
    script: ScriptDirectory,
    current_revision: str,
    target_revision: str,
) -> tuple[str, ...]:
    try:
        revisions = tuple(script.iterate_revisions(target_revision, current_revision))
    except Exception as exc:
        raise DatabaseRevisionError(
            "The recorded Alembic revision is not an ancestor of the configured "
            "script head. Resolve the migration branch before startup."
        ) from exc

    pending = tuple(
        revision.revision
        for revision in revisions
        if revision.revision != current_revision
    )
    if not pending:
        raise DatabaseRevisionError(
            f"Alembic revision {current_revision} is neither the configured head "
            f"{target_revision} nor a supported revision behind it."
        )
    return pending


###############################################################################
def _assert_current_head(connection: Any, target_revision: str) -> None:
    detected = _current_heads(connection)
    if detected != (target_revision,):
        rendered = ", ".join(detected) or "none"
        raise DatabaseRevisionError(
            f"Alembic did not finish at the configured head {target_revision}; "
            f"detected revisions: {rendered}."
        )


###############################################################################
def _application_tables(connection: Any) -> set[str]:
    return {
        name
        for name in inspect(connection).get_table_names()
        if name != ALEMBIC_VERSION_TABLE
    }


###############################################################################
def _run_locked_migrations(connection: Any, config_path: Path | None = None) -> None:
    config = _alembic_config(connection, config_path)
    script, target_revision = _script_and_head(config)
    detected = _current_heads(connection)
    if len(detected) > 1:
        rendered = ", ".join(detected)
        raise DatabaseRevisionError(
            "Database contains multiple Alembic heads; resolve the database branch "
            f"before startup (detected: {rendered})."
        )

    current_revision = detected[0] if detected else None
    logger.info(
        "Database migration state detected: backend=%s current=%s target=%s",
        connection.dialect.name,
        current_revision or "unversioned",
        target_revision,
    )

    if current_revision is None:
        tables = _application_tables(connection)
        if not tables:
            logger.info("Database is empty; applying Alembic upgrade to head.")
            command.upgrade(config, "head")
            logger.info("Alembic migrations applied: %s", target_revision)
        else:
            validate_database_metadata(connection)
            logger.info(
                "Adopting unversioned legacy database with exact baseline metadata; "
                "application rows will be preserved."
            )
            command.stamp(config, "head")
            logger.info("Legacy database stamped at Alembic head %s", target_revision)

        validate_database_metadata(connection)
        _assert_current_head(connection, target_revision)
        return

    try:
        recorded_script = script.get_revision(current_revision)
    except Exception as exc:
        raise DatabaseRevisionError(
            f"Database records unknown Alembic revision {current_revision}; "
            "restore the matching migration scripts before startup."
        ) from exc
    if recorded_script is None:
        raise DatabaseRevisionError(
            f"Database records unknown or ahead Alembic revision {current_revision}; "
            "restore the matching migration scripts before startup."
        )

    if current_revision == target_revision:
        validate_database_metadata(connection)
        logger.info("Database is already at Alembic head %s; migration no-op.", target_revision)
        return

    pending = _pending_revisions(script, current_revision, target_revision)
    logger.info(
        "Applying pending Alembic revisions in order: %s",
        ", ".join(pending),
    )
    command.upgrade(config, "head")
    logger.info("Alembic migrations applied: %s", ", ".join(pending))
    validate_database_metadata(connection)
    _assert_current_head(connection, target_revision)


###############################################################################
def _is_lock_timeout(exc: BaseException) -> bool:
    return _sqlstate(exc) == "55P03" or "lock timeout" in str(exc).lower()


###############################################################################
def _run_sqlite_migrations(
    engine: Engine,
    config_path: Path | None = None,
) -> None:
    with engine.connect() as connection:
        dbapi_connection = connection.connection.driver_connection
        try:
            # Python 3.14's autocommit=False mode intentionally opens a
            # deferred transaction when the connection is created. End that
            # empty driver transaction just before taking the exclusive
            # migration lock, then restore the requested mode inside the
            # explicit BEGIN IMMEDIATE transaction.
            if hasattr(dbapi_connection, "autocommit"):
                dbapi_connection.autocommit = True
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            if hasattr(dbapi_connection, "autocommit"):
                dbapi_connection.autocommit = False
            _run_locked_migrations(connection, config_path)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


###############################################################################
def _run_postgres_migrations(
    engine: Engine,
    config_path: Path | None = None,
) -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(
                f"SET LOCAL lock_timeout = '{MIGRATION_LOCK_TIMEOUT_SECONDS}s'"
            )
            lock_key = _engine_advisory_lock_key(engine)
            connection.execute(
                text("SELECT pg_advisory_xact_lock(CAST(:lock_key AS BIGINT))"),
                {"lock_key": lock_key},
            )
            _run_locked_migrations(connection, config_path)
            transaction.commit()
        except Exception as exc:
            transaction.rollback()
            if _is_lock_timeout(exc):
                raise DatabaseMigrationLockError(
                    "Timed out waiting for the PostgreSQL migration lock after "
                    f"{MIGRATION_LOCK_TIMEOUT_SECONDS} seconds. Stop the competing "
                    "initializer or inspect active database sessions, then retry."
                ) from exc
            raise


###############################################################################
def run_migrations_on_engine(
    engine: Engine,
    *,
    config_path: Path | None = None,
) -> None:
    """Run the shared Alembic state machine on an existing SQLAlchemy engine."""
    try:
        if engine.dialect.name == "sqlite":
            _run_sqlite_migrations(engine, config_path)
        elif engine.dialect.name == "postgresql":
            _run_postgres_migrations(engine, config_path)
        else:
            raise DatabaseInitializationError(
                f"Unsupported SQLAlchemy database dialect: {engine.dialect.name}"
            )
    except DatabaseInitializationError as exc:
        logger.error("Database migration failed: %s", _redact_error(exc))
        raise
    except Exception as exc:
        logger.error(
            "Database migration failed (%s): %s",
            type(exc).__name__,
            _redact_error(exc),
        )
        raise DatabaseMigrationError(
            "Alembic database migration failed. Review the migration error and "
            "database state before retrying."
        ) from exc


###############################################################################
def _create_missing_postgres_database(settings: DatabaseSettings) -> None:
    target = settings.database_name
    if not settings.host or not settings.username or not target:
        raise DatabaseInitializationError(
            "PostgreSQL host, username, and database name are required."
        )

    connect_args = build_postgres_connect_args(settings)
    admin = sqlalchemy.create_engine(
        build_postgres_url(settings, "postgres"),
        future=True,
        connect_args=connect_args,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    lock_key = _advisory_lock_key(
        "fairs:database-create:v1",
        engine=settings.engine,
        host=settings.host,
        port=settings.port,
        database_name=target,
    )
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(
                f"SET lock_timeout = '{MIGRATION_LOCK_TIMEOUT_SECONDS}s'"
            )
            connection.execute(
                text("SELECT pg_advisory_lock(CAST(:lock_key AS BIGINT))"),
                {"lock_key": lock_key},
            )
            try:
                exists = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                    {"database_name": target},
                ).scalar_one_or_none()
                if exists is None:
                    identifier = escape_postgres_identifier(target)
                    connection.exec_driver_sql(
                        f'CREATE DATABASE "{identifier}" '
                        "WITH ENCODING 'UTF8' TEMPLATE template0"
                    )
                    logger.info("Created missing PostgreSQL database.")
                else:
                    logger.info("PostgreSQL database was created by another initializer.")
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(CAST(:lock_key AS BIGINT))"),
                    {"lock_key": lock_key},
                )
    except Exception as exc:
        if _is_lock_timeout(exc):
            raise DatabaseMigrationLockError(
                "Timed out waiting for the PostgreSQL database-creation lock after "
                f"{MIGRATION_LOCK_TIMEOUT_SECONDS} seconds. Stop the competing "
                "initializer or inspect active database sessions, then retry."
            ) from exc
        raise DatabaseInitializationError(
            "The configured PostgreSQL database is missing and could not be created. "
            "The server must be reachable and the configured role must have CREATEDB "
            "privilege, or an administrator must create the database first."
        ) from exc
    finally:
        admin.dispose()


###############################################################################
def _build_postgres_target_engine(settings: DatabaseSettings) -> Engine:
    target_engine = build_postgres_engine(settings)
    try:
        with target_engine.connect():
            return target_engine
    except SQLAlchemyError as exc:
        target_engine.dispose()
        if not is_missing_postgres_database_error(exc):
            raise

    _create_missing_postgres_database(settings)
    return build_postgres_engine(settings)


###############################################################################
def initialize_database(
    settings: DatabaseSettings | None = None,
    *,
    database_path: str | Path | None = None,
) -> None:
    """Initialize or upgrade the configured database, then dispose owned resources."""
    resolved = settings or get_server_settings().database
    engine: Engine | None = None
    try:
        if resolved.embedded_database:
            engine = build_sqlite_engine(resolved, database_path=database_path)
        else:
            if not is_supported_postgres_engine(resolved.engine):
                raise DatabaseInitializationError(
                    f"Unsupported database engine: {resolved.engine}"
                )
            engine = _build_postgres_target_engine(resolved)
        run_migrations_on_engine(engine)
    except DatabaseInitializationError as exc:
        logger.error("Database initialization failed: %s", _redact_error(exc))
        raise
    except Exception as exc:
        logger.error(
            "Database initialization failed (%s): %s",
            type(exc).__name__,
            _redact_error(exc),
        )
        raise DatabaseInitializationError(
            "Database initialization failed. Review the sanitized error above and "
            "resolve the database state before retrying."
        ) from exc
    finally:
        if engine is not None:
            engine.dispose()


__all__ = [
    "DatabaseInitializationError",
    "DatabaseMigrationError",
    "DatabaseSchemaDriftError",
    "DatabaseRevisionError",
    "DatabaseMigrationLockError",
    "build_postgres_url",
    "escape_postgres_identifier",
    "initialize_database",
    "is_missing_postgres_database_error",
    "run_migrations_on_engine",
    "validate_database_metadata",
]
