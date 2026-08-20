from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from server.common import path as shared_paths
from server.configurations import DatabaseSettings

###############################################################################
def _enable_write_ahead_logging(cursor: Any) -> None:
    """Enable WAL, retrying briefly while a concurrent initializer holds a lock."""
    for attempt in range(10):
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as exc:
            if "database is locked" not in str(exc).lower() or attempt == 9:
                raise
            time.sleep(min(0.05 * (2**attempt), 1.0))


###############################################################################
def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    previous_autocommit = getattr(dbapi_connection, "autocommit", None)
    if previous_autocommit is not None:
        dbapi_connection.autocommit = True
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        _enable_write_ahead_logging(cursor)
    finally:
        cursor.close()
        if previous_autocommit is not None:
            dbapi_connection.autocommit = previous_autocommit

###############################################################################
def build_sqlite_engine(
    settings: DatabaseSettings,
    database_path: str | Path | None = None,
) -> Engine:
    db_path = Path(database_path) if database_path is not None else Path(shared_paths.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = sqlalchemy.create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        future=True,
        connect_args={"autocommit": False, "check_same_thread": False},
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    return engine


__all__ = ["build_sqlite_engine", "set_sqlite_pragma"]
