from __future__ import annotations

from pathlib import Path
from typing import Any

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from server.common import path as shared_paths
from server.configurations import DatabaseSettings


def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def build_sqlite_engine(settings: DatabaseSettings) -> Engine:
    db_path = Path(shared_paths.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = sqlalchemy.create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    return engine


__all__ = ["build_sqlite_engine", "set_sqlite_pragma"]
