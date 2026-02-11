from __future__ import annotations

from typing import Any

import pandas as pd

from FAIRS.server.repositories.database.backend import FAIRSDatabase, database


###############################################################################
class DataRepositoryQueries:
    def __init__(self, db: FAIRSDatabase = database) -> None:
        self.database = db

    # -------------------------------------------------------------------------
    def load_table(
        self,
        table_name: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> pd.DataFrame:
        return self.database.load_from_database(table_name, limit=limit, offset=offset)

    # -------------------------------------------------------------------------
    def load_filtered_table(
        self,
        table_name: str,
        conditions: dict[str, Any],
    ) -> pd.DataFrame:
        return self.database.load_filtered(table_name, conditions)

    # -------------------------------------------------------------------------
    def save_table(self, dataset: pd.DataFrame, table_name: str) -> None:
        self.database.save_into_database(dataset, table_name)

    # -------------------------------------------------------------------------
    def append_table(self, dataset: pd.DataFrame, table_name: str) -> None:
        self.database.append_into_database(dataset, table_name)

    # -------------------------------------------------------------------------
    def upsert_table(self, dataset: pd.DataFrame, table_name: str) -> None:
        self.database.upsert_into_database(dataset, table_name)

    # -------------------------------------------------------------------------
    def delete_table_rows(self, table_name: str, conditions: dict[str, Any]) -> None:
        self.database.delete_from_database(table_name, conditions)

    # -------------------------------------------------------------------------
    def clear_table(self, table_name: str) -> None:
        self.database.clear_table(table_name)
