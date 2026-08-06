from __future__ import annotations

import sqlalchemy
from sqlalchemy.engine import Engine, URL

from server.configurations import DatabaseSettings
from server.repositories.database.utils import build_postgres_connect_args, normalize_postgres_engine

###############################################################################
def build_postgres_engine(settings: DatabaseSettings) -> Engine:
    if not settings.host or not settings.database_name or not settings.username:
        raise ValueError("PostgreSQL host, database name, and username are required.")
    url = URL.create(
        drivername=normalize_postgres_engine(settings.engine),
        username=settings.username,
        password=settings.password or "",
        host=settings.host,
        port=settings.port or 5432,
        database=settings.database_name,
    )
    return sqlalchemy.create_engine(
        url,
        echo=False,
        future=True,
        connect_args=build_postgres_connect_args(settings),
        pool_pre_ping=True,
    )


__all__ = ["build_postgres_engine"]
