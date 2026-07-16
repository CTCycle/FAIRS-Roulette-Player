from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from server.configurations import DatabaseSettings
from server.configurations.startup import get_server_settings
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
            from server.repositories.database.sqlite import build_sqlite_engine
            self.engine = build_sqlite_engine(self.settings)
            self.db_path = Path(str(self.engine.url.database)) if self.engine.url.database else None
        else:
            from server.repositories.database.postgres import build_postgres_engine
            self.engine = build_postgres_engine(self.settings)
            self.db_path = None
        self.Session = sessionmaker(bind=self.engine, future=True, expire_on_commit=False)
        self.insert_batch_size = self.settings.insert_batch_size

    # -------------------------------------------------------------------------
    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    # -------------------------------------------------------------------------
    def validate_schema(self) -> None:
        inspector = inspect(self.engine)
        missing_tables = set(Base.metadata.tables) - set(inspector.get_table_names())
        missing_columns = {
            table_name: {column.name for column in table.columns} - {column["name"] for column in inspector.get_columns(table_name)}
            for table_name, table in Base.metadata.tables.items()
            if table_name in inspector.get_table_names()
        }
        missing_columns = {name: columns for name, columns in missing_columns.items() if columns}
        if missing_tables or missing_columns:
            details = [f"tables={', '.join(sorted(missing_tables))}"] if missing_tables else []
            details.extend(f"{name} columns={', '.join(sorted(columns))}" for name, columns in missing_columns.items())
            raise RuntimeError(f"Database schema is incompatible with the canonical schema ({'; '.join(details)}). Recreate or migrate the database.")

    # -------------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self.Session.begin() as session:
            yield session

    # -------------------------------------------------------------------------
    def dispose(self) -> None:
        self.engine.dispose()

    # -------------------------------------------------------------------------
    def close(self) -> None:
        self.dispose()


__all__ = ["FAIRSDatabase"]
