from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

import pandas as pd

from server.configurations import DatabaseSettings
from server.configurations.startup import get_server_settings
from server.common.utils.logger import logger
from server.repositories.database.postgres import PostgresRepository
from server.repositories.database.sqlite import SQLiteRepository


###############################################################################
class DatabaseBackend(Protocol):
    db_path: str | None
    engine: Any

    # -------------------------------------------------------------------------
    def load_from_database(
        self,
        table_name: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> pd.DataFrame: ...

    # -------------------------------------------------------------------------
    def append_into_database(self, df: pd.DataFrame, table_name: str) -> None: ...

    # -------------------------------------------------------------------------
    def upsert_into_database(self, df: pd.DataFrame, table_name: str) -> None: ...

    # -------------------------------------------------------------------------
    def delete_from_database(
        self, table_name: str, conditions: dict[str, Any]
    ) -> None: ...

    # -------------------------------------------------------------------------
    def load_filtered(
        self, table_name: str, conditions: dict[str, Any]
    ) -> pd.DataFrame: ...


BackendFactory = Callable[[DatabaseSettings], DatabaseBackend]


BACKEND_FACTORIES: dict[str, BackendFactory] = {
    "sqlite": SQLiteRepository,
    "postgres": PostgresRepository,
}


# [DATABASE]
###############################################################################
class FAIRSDatabase:
    def __init__(self) -> None:
        self.settings = get_server_settings().database
        self.backend = self._build_backend(self.settings.embedded_database)

    # -------------------------------------------------------------------------
    def _build_backend(self, is_embedded: bool) -> DatabaseBackend:
        backend_name = "sqlite" if is_embedded else (self.settings.engine or "postgres")
        normalized_name = backend_name.lower()
        logger.info("Initializing %s database backend", backend_name)
        if normalized_name not in BACKEND_FACTORIES:
            raise ValueError(f"Unsupported database engine: {backend_name}")
        factory = BACKEND_FACTORIES[normalized_name]
        return factory(self.settings)

    # -------------------------------------------------------------------------
    @property
    def db_path(self) -> str | None:
        return getattr(self.backend, "db_path", None)

    # -------------------------------------------------------------------------
    def load_from_database(
        self,
        table_name: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> pd.DataFrame:
        return self.backend.load_from_database(table_name, limit=limit, offset=offset)

    # -------------------------------------------------------------------------
    def append_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        self.backend.append_into_database(df, table_name)

    # -------------------------------------------------------------------------
    def upsert_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        self.backend.upsert_into_database(df, table_name)

    # -------------------------------------------------------------------------
    def delete_from_database(self, table_name: str, conditions: dict[str, Any]) -> None:
        self.backend.delete_from_database(table_name, conditions)

    # -------------------------------------------------------------------------
    def load_filtered(
        self, table_name: str, conditions: dict[str, Any]
    ) -> pd.DataFrame:
        return self.backend.load_filtered(table_name, conditions)
