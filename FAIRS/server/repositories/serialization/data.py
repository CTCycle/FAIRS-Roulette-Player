from __future__ import annotations

from typing import Any, cast

import pandas as pd

from FAIRS.server.common.constants import (
    GAME_SESSIONS_COLUMNS,
    GAME_SESSIONS_TABLE,
    INFERENCE_CONTEXT_COLUMNS,
    INFERENCE_CONTEXT_TABLE,
    ROULETTE_SERIES_COLUMNS,
    ROULETTE_SERIES_TABLE,
)
from FAIRS.server.repositories.queries.data import DataRepositoryQueries


###############################################################################
class DataSerializer:
    def __init__(self, queries: DataRepositoryQueries | None = None) -> None:
        self.queries = queries or DataRepositoryQueries()

    # -------------------------------------------------------------------------
    def load_roulette_series(self) -> pd.DataFrame:
        return self.queries.load_table(ROULETTE_SERIES_TABLE)

    # -------------------------------------------------------------------------
    def load_roulette_dataset(self, name: str) -> pd.DataFrame:
        return self.queries.load_filtered_table(
            ROULETTE_SERIES_TABLE,
            {"name": name},
        )

    # -------------------------------------------------------------------------
    def load_inference_context(self, name: str) -> pd.DataFrame:
        return self.queries.load_filtered_table(
            INFERENCE_CONTEXT_TABLE,
            {"name": name},
        )

    # -------------------------------------------------------------------------
    def load_game_sessions(self) -> pd.DataFrame:
        return self.queries.load_table(GAME_SESSIONS_TABLE)

    # -------------------------------------------------------------------------
    def save_roulette_series(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return

        frame = dataset.reindex(columns=ROULETTE_SERIES_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, ROULETTE_SERIES_TABLE)

    # -------------------------------------------------------------------------
    def save_inference_context(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return

        frame = dataset.reindex(columns=INFERENCE_CONTEXT_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, INFERENCE_CONTEXT_TABLE)

    # -------------------------------------------------------------------------
    def save_game_sessions(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return

        frame = dataset.reindex(columns=GAME_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, GAME_SESSIONS_TABLE)

    # -------------------------------------------------------------------------
    def append_game_sessions(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return

        frame = dataset.reindex(columns=GAME_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.append_table(frame, GAME_SESSIONS_TABLE)

    # -------------------------------------------------------------------------
    def upsert_game_sessions(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return

        frame = dataset.reindex(columns=GAME_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, GAME_SESSIONS_TABLE)

    # -------------------------------------------------------------------------
    def delete_game_sessions(self, session_id: str) -> None:
        self.queries.delete_table_rows(GAME_SESSIONS_TABLE, {"session_id": session_id})

    # -------------------------------------------------------------------------
    def delete_roulette_dataset(self, name: str) -> None:
        self.queries.delete_table_rows(
            ROULETTE_SERIES_TABLE,
            {"name": name},
        )

    # -------------------------------------------------------------------------
    def clear_inference_context(self) -> None:
        self.queries.clear_table(INFERENCE_CONTEXT_TABLE)
