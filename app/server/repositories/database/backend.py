from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from server.configurations import DatabaseSettings
from server.configurations.startup import get_server_settings
from server.repositories.database.postgres import build_postgres_engine
from server.repositories.database.sqlite import build_sqlite_engine
from server.repositories.schemas.models import Base

###############################################################################
class FAIRSDatabase:
    """Owns the SQLAlchemy engine, sessions, schema lifecycle, and transactions."""

    # -------------------------------------------------------------------------
    def __init__(self, settings: DatabaseSettings | None = None, engine: Engine | None = None) -> None:
        self.settings = settings or get_server_settings().database
        if engine is not None:
            self.engine = engine
            self.db_path = None
        elif self.settings.embedded_database:
            self.engine = build_sqlite_engine(self.settings)
            self.db_path = Path(str(self.engine.url.database)) if self.engine.url.database else None
        else:
            self.engine = build_postgres_engine(self.settings)
            self.db_path = None
        self.Session = sessionmaker(bind=self.engine, future=True, expire_on_commit=False)
        self.insert_batch_size = self.settings.insert_batch_size

    # -------------------------------------------------------------------------
    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    # -------------------------------------------------------------------------
    def check_connection(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    # -------------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self.Session.begin() as session:
            yield session

    # -------------------------------------------------------------------------
    def dispose(self) -> None:
        self.engine.dispose()


__all__ = ["FAIRSDatabase"]
