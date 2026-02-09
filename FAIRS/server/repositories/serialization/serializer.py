from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd

from FAIRS.server.repositories.database.manager import database
from FAIRS.server.common.constants import (
    GAME_SESSIONS_COLUMNS,
    GAME_SESSIONS_TABLE,
    INFERENCE_CONTEXT_COLUMNS,
    INFERENCE_CONTEXT_TABLE,
    ROULETTE_SERIES_COLUMNS,
    ROULETTE_SERIES_TABLE,
)


###############################################################################
class DataSerializer:
    def __init__(self) -> None:
        pass

    # -----------------------------------------------------------------------------
    def load_roulette_series(self) -> pd.DataFrame:
        return database.load_from_database(ROULETTE_SERIES_TABLE)

    # -----------------------------------------------------------------------------
    def load_roulette_dataset(self, dataset_name: str) -> pd.DataFrame:
        return database.load_filtered(
            ROULETTE_SERIES_TABLE, {"dataset_name": dataset_name}
        )

    # -----------------------------------------------------------------------------
    def load_inference_context(self, dataset_name: str) -> pd.DataFrame:
        return database.load_filtered(
            INFERENCE_CONTEXT_TABLE, {"dataset_name": dataset_name}
        )

    # -----------------------------------------------------------------------------
    def load_game_sessions(self) -> pd.DataFrame:
        return database.load_from_database(GAME_SESSIONS_TABLE)

    # -----------------------------------------------------------------------------
    # -----------------------------------------------------------------------------
    def save_roulette_series(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=ROULETTE_SERIES_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        dataset_names = [
            name
            for name in frame["dataset_name"].dropna().unique().tolist()
            if str(name).strip()
        ]
        if not dataset_names:
            database.save_into_database(frame, ROULETTE_SERIES_TABLE)
            return

        for dataset_name in dataset_names:
            database.delete_from_database(
                ROULETTE_SERIES_TABLE, {"dataset_name": dataset_name}
            )
        database.append_into_database(frame, ROULETTE_SERIES_TABLE)

    # -----------------------------------------------------------------------------
    def save_inference_context(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=INFERENCE_CONTEXT_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.clear_table(INFERENCE_CONTEXT_TABLE)
        database.append_into_database(frame, INFERENCE_CONTEXT_TABLE)

    # -----------------------------------------------------------------------------
    def save_game_sessions(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=GAME_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.save_into_database(frame, GAME_SESSIONS_TABLE)

    # -----------------------------------------------------------------------------
    def append_game_sessions(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=GAME_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.append_into_database(frame, GAME_SESSIONS_TABLE)

    # -----------------------------------------------------------------------------
    def upsert_game_sessions(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=GAME_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.upsert_into_database(frame, GAME_SESSIONS_TABLE)

    # -----------------------------------------------------------------------------
    def delete_game_sessions(self, session_id: str) -> None:
        database.delete_from_database(GAME_SESSIONS_TABLE, {"session_id": session_id})

    # -----------------------------------------------------------------------------
    # -----------------------------------------------------------------------------
    def delete_roulette_dataset(self, dataset_name: str) -> None:
        database.delete_from_database(
            ROULETTE_SERIES_TABLE, {"dataset_name": dataset_name}
        )

    # -----------------------------------------------------------------------------
    def clear_inference_context(self) -> None:
        database.clear_table(INFERENCE_CONTEXT_TABLE)

