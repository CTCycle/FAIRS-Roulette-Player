from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd

from FAIRS.server.database.database import database
from FAIRS.server.utils.constants import (
    CHECKPOINTS_SUMMARY_COLUMNS,
    CHECKPOINTS_SUMMARY_TABLE,
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
    def load_predicted_games(self) -> pd.DataFrame:
        return database.load_from_database(PREDICTED_GAMES_TABLE)

    # -----------------------------------------------------------------------------
    def load_checkpoints_summary(self) -> pd.DataFrame:
        return database.load_from_database(CHECKPOINTS_SUMMARY_TABLE)

    # -----------------------------------------------------------------------------
    def save_roulette_series(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=ROULETTE_SERIES_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.save_into_database(frame, ROULETTE_SERIES_TABLE)

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
    def upsert_checkpoints_summary(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            return
        frame = dataset.reindex(columns=CHECKPOINTS_SUMMARY_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        database.upsert_into_database(frame, CHECKPOINTS_SUMMARY_TABLE)
