from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import create_engine, inspect

from server.contracts.configuration import DatabaseSettings
from server.repositories.database import initializer
from server.repositories.schemas.models import Base

###############################################################################
def _sqlite_settings() -> DatabaseSettings:
    return DatabaseSettings(
        embedded_database=True,
        engine=None,
        host=None,
        port=None,
        database_name=None,
        username=None,
        password=None,
        ssl=False,
        ssl_ca=None,
        connect_timeout=10,
        insert_batch_size=1000,
    )

###############################################################################
def _postgres_settings() -> DatabaseSettings:
    return DatabaseSettings(
        embedded_database=False,
        engine="postgresql+psycopg",
        host="127.0.0.1",
        port=5432,
        database_name="fairs",
        username="postgres",
        password="secret",
        ssl=False,
        ssl_ca=None,
        connect_timeout=10,
        insert_batch_size=1000,
    )

###############################################################################
def test_sqlite_initialization_only_creates_missing_database(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "database.db"
    monkeypatch.setattr(initializer.shared_paths, "DATABASE_PATH", database_path)

    initializer.initialize_sqlite_database_if_missing(_sqlite_settings())

    assert database_path.is_file()
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables)
    finally:
        engine.dispose()

    before_hash = hashlib.sha256(database_path.read_bytes()).digest()
    before_mtime = database_path.stat().st_mtime_ns

    def fail_if_called(_settings: DatabaseSettings) -> None:
        raise AssertionError("existing SQLite database was initialized again")

    monkeypatch.setattr(initializer, "initialize_sqlite_database", fail_if_called)
    initializer.initialize_sqlite_database_if_missing(_sqlite_settings())

    assert hashlib.sha256(database_path.read_bytes()).digest() == before_hash
    assert database_path.stat().st_mtime_ns == before_mtime

###############################################################################
def test_explicit_postgres_initialization_creates_database_and_schema(monkeypatch) -> None:
    create_database_statements: list[str] = []
    schema_calls: list[bool] = []

    ###############################################################################
    class Connection:

        # -------------------------------------------------------------------------
        def __enter__(self) -> "Connection":
            return self

        # -------------------------------------------------------------------------
        def __exit__(self, *_args: object) -> None:
            return None

        # -------------------------------------------------------------------------
        def exec_driver_sql(self, statement: str) -> None:
            create_database_statements.append(statement)

    ###############################################################################
    class AdminEngine:

        # -------------------------------------------------------------------------
        def connect(self) -> Connection:
            return Connection()

        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            return None

    ###############################################################################
    class Database:

        # -------------------------------------------------------------------------
        def create_schema(self) -> None:
            schema_calls.append(True)

        # -------------------------------------------------------------------------
        def dispose(self) -> None:
            return None

    monkeypatch.setattr(initializer, "postgres_database_exists", lambda *_args: False)
    monkeypatch.setattr(initializer.sqlalchemy, "create_engine", lambda *_args, **_kwargs: AdminEngine())
    monkeypatch.setattr(initializer, "FAIRSDatabase", lambda _settings: Database())

    target = initializer.ensure_postgres_database(_postgres_settings())

    assert target == "fairs"
    assert create_database_statements == [
        'CREATE DATABASE "fairs" WITH ENCODING \'UTF8\' TEMPLATE template0'
    ]
    assert schema_calls == [True]
