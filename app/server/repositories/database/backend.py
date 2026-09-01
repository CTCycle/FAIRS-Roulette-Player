from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.configurations import DatabaseSettings
from server.repositories.database.postgres import build_postgres_engine
from server.repositories.database.sqlite import build_sqlite_engine


###############################################################################
class FAIRSDatabase:
    """Owns the application SQLAlchemy engine, sessions, and transactions."""

    # -------------------------------------------------------------------------
    def __init__(
        self,
        settings: DatabaseSettings,
        engine: Engine | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        self.settings = settings
        owns_engine = engine is None
        constructed_engine: Engine | None = None
        try:
            if engine is not None:
                self.engine = engine
                self.db_path = None
            elif self.settings.embedded_database:
                constructed_engine = build_sqlite_engine(
                    self.settings,
                    database_path=database_path,
                )
                self.engine = constructed_engine
                self.db_path = (
                    Path(str(self.engine.url.database))
                    if self.engine.url.database
                    else None
                )
            else:
                constructed_engine = build_postgres_engine(self.settings)
                self.engine = constructed_engine
                self.db_path = None
            self.Session = sessionmaker(
                bind=self.engine, future=True, expire_on_commit=False
            )
            self.insert_batch_size = self.settings.insert_batch_size
        except Exception:
            if owns_engine and constructed_engine is not None:
                constructed_engine.dispose()
            raise

    # -------------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self.Session.begin() as session:
            yield session

    # -------------------------------------------------------------------------
    def dispose(self) -> None:
        self.engine.dispose()


__all__ = ["FAIRSDatabase"]
