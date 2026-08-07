from __future__ import annotations

import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

from server.common import path as shared_paths
from server.common.utils.logger import logger
from server.configurations import DatabaseSettings
from server.configurations.startup import get_server_settings
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.database.utils import (
    build_postgres_connect_args,
    is_supported_postgres_engine,
)

###############################################################################
def build_postgres_url(settings: DatabaseSettings, database_name: str) -> sqlalchemy.URL:
    if not is_supported_postgres_engine(settings.engine):
        raise ValueError(f"Unsupported database engine: {settings.engine}")
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
def is_missing_postgres_database_error(exc: SQLAlchemyError, target_database: str) -> bool:
    original = getattr(exc, "orig", None)
    sql_state = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    return sql_state == "3D000" or ("does not exist" in str(exc).lower() and target_database.lower() in str(exc).lower())

###############################################################################
def postgres_database_exists(settings: DatabaseSettings, target_database: str, connect_args: dict[str, object]) -> bool:
    engine = sqlalchemy.create_engine(build_postgres_url(settings, target_database), future=True, connect_args=connect_args, pool_pre_ping=True)
    try:
        with engine.connect():
            return True
    except SQLAlchemyError as exc:
        if is_missing_postgres_database_error(exc, target_database):
            return False
        raise
    finally:
        engine.dispose()

###############################################################################
def initialize_sqlite_database(settings: DatabaseSettings) -> None:
    database = FAIRSDatabase(settings)
    database.create_schema()
    database.dispose()
    logger.info("Initialized SQLite database at %s", database.db_path)

###############################################################################
def initialize_sqlite_database_if_missing(settings: DatabaseSettings) -> None:
    database_path = shared_paths.DATABASE_PATH
    if database_path.is_file():
        logger.info("SQLite database already exists at %s; skipped initialization", database_path)
        return
    initialize_sqlite_database(settings)

###############################################################################
def ensure_postgres_database(settings: DatabaseSettings) -> str:
    if not settings.host or not settings.username or not settings.database_name:
        raise ValueError("PostgreSQL host, username, and database name are required.")
    target = settings.database_name
    connect_args = build_postgres_connect_args(settings)
    admin = sqlalchemy.create_engine(build_postgres_url(settings, "postgres"), future=True, connect_args=connect_args, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        if not postgres_database_exists(settings, target, connect_args):
            identifier = escape_postgres_identifier(target)
            with admin.connect() as connection:
                connection.exec_driver_sql(f'CREATE DATABASE "{identifier}" WITH ENCODING \'UTF8\' TEMPLATE template0')
    finally:
        admin.dispose()
    database = FAIRSDatabase(settings)
    database.create_schema()
    database.dispose()
    logger.info("Ensured PostgreSQL schema exists in %s", target)
    return target

###############################################################################
def initialize_database(settings: DatabaseSettings | None = None) -> None:
    resolved = settings or get_server_settings().database
    try:
        if resolved.embedded_database:
            initialize_sqlite_database_if_missing(resolved)
            return
        if not is_supported_postgres_engine(resolved.engine):
            raise ValueError(f"Unsupported database engine: {resolved.engine}")
        ensure_postgres_database(resolved)
    except (SQLAlchemyError, ValueError) as exc:
        logger.error("Database initialization failed: %s", exc)
        raise SystemExit(1) from exc


__all__ = [
    "build_postgres_url",
    "ensure_postgres_database",
    "initialize_database",
    "initialize_sqlite_database",
    "initialize_sqlite_database_if_missing",
]
