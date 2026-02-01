from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd

from FAIRS.server.repositories.database import database
from FAIRS.server.utils.constants import (
    INFERENCE_CONTEXT_COLUMNS,
    INFERENCE_CONTEXT_TABLE,
    PREDICTED_GAMES_COLUMNS,
    PREDICTED_GAMES_TABLE,
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
    def load_inference_context(self, dataset_name: str) -> pd.DataFrame:
        return database.load_filtered(
            INFERENCE_CONTEXT_TABLE, {"dataset_name": dataset_name}
        )

    # -----------------------------------------------------------------------------
    def load_predicted_games(self) -> pd.DataFrame:
        return database.load_from_database(PREDICTED_GAMES_TABLE)

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
    def save_predicted_games(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=PREDICTED_GAMES_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.save_into_database(frame, PREDICTED_GAMES_TABLE)

    # -----------------------------------------------------------------------------
    def append_predicted_games(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=PREDICTED_GAMES_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.append_into_database(frame, PREDICTED_GAMES_TABLE)

    # -----------------------------------------------------------------------------
    # -----------------------------------------------------------------------------
    def delete_roulette_dataset(self, dataset_name: str) -> None:
        database.delete_from_database(
            ROULETTE_SERIES_TABLE, {"dataset_name": dataset_name}
        )

