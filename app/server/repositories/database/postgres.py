from __future__ import annotations

import urllib.parse
from typing import Any

import sqlalchemy
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from FAIRS.server.configurations import DatabaseSettings
from FAIRS.server.repositories.database.common import (
    SQLAlchemyRepositoryBase,
    normalize_table_name as normalize_table_name,
)
from FAIRS.server.repositories.database.utils import normalize_postgres_engine


###############################################################################
class PostgresRepository(SQLAlchemyRepositoryBase):
    def __init__(self, settings: DatabaseSettings) -> None:
        if not settings.host:
            raise ValueError("Database host must be provided for external database.")
        if not settings.database_name:
            raise ValueError("Database name must be provided for external database.")
        if not settings.username:
            raise ValueError(
                "Database username must be provided for external database."
            )

        port = settings.port or 5432
        engine_name = normalize_postgres_engine(settings.engine)
        connect_args: dict[str, Any] = {"connect_timeout": settings.connect_timeout}
        if settings.ssl:
            connect_args["sslmode"] = "require"
            if settings.ssl_ca:
                connect_args["sslrootcert"] = settings.ssl_ca

        safe_username = urllib.parse.quote_plus(settings.username)
        safe_password = urllib.parse.quote_plus(settings.password or "")
        self.db_path: str | None = None
        self.engine: Engine = sqlalchemy.create_engine(
            f"{engine_name}://{safe_username}:{safe_password}@{settings.host}:{port}/{settings.database_name}",
            echo=False,
            future=True,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.insert_batch_size = settings.insert_batch_size
