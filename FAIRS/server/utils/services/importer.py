from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal

import pandas as pd

from FAIRS.server.utils.constants import (
    CHECKPOINTS_SUMMARY_COLUMNS,
    CHECKPOINTS_SUMMARY_TABLE,
    INFERENCE_CONTEXT_COLUMNS,
    INFERENCE_CONTEXT_TABLE,
    PREDICTED_GAMES_COLUMNS,
    PREDICTED_GAMES_TABLE,
    ROULETTE_SERIES_COLUMNS,
    ROULETTE_SERIES_TABLE,
)
from FAIRS.server.utils.repository.serializer import DataSerializer
from FAIRS.server.utils.services.process import RouletteSeriesEncoder

DatasetTable = Literal[
    "ROULETTE_SERIES",
    "INFERENCE_CONTEXT",
    "PREDICTED_GAMES",
    "CHECKPOINTS_SUMMARY",
]


###############################################################################
class DatasetImportService:
    def __init__(self) -> None:
        self.serializer = DataSerializer()
        self.encoder = RouletteSeriesEncoder()

    # -------------------------------------------------------------------------
    def normalize(
        self,
        dataframe: pd.DataFrame,
        table: DatasetTable,
        dataset_name: str | None = None,
    ) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe

        if table == ROULETTE_SERIES_TABLE:
            normalized = dataframe.copy()
            if dataset_name is not None:
                cleaned_name = dataset_name.strip()
                normalized["dataset_name"] = cleaned_name if cleaned_name else "default"
            elif "dataset_name" not in normalized.columns:
                normalized["dataset_name"] = "default"
            else:
                normalized["dataset_name"] = normalized["dataset_name"].fillna("default")
            if "color" not in normalized.columns or "position" not in normalized.columns:
                normalized = self.encoder.encode(normalized)
            if "id" not in normalized.columns:
                normalized.insert(0, "id", range(1, len(normalized) + 1))
            return normalized.reindex(columns=ROULETTE_SERIES_COLUMNS)

        if table == INFERENCE_CONTEXT_TABLE:
            normalized = dataframe.copy()
            if dataset_name is not None:
                cleaned_name = dataset_name.strip()
                normalized["dataset_name"] = cleaned_name if cleaned_name else "context"
            elif "dataset_name" not in normalized.columns:
                normalized["dataset_name"] = "context"
            if "id" not in normalized.columns:
                normalized.insert(0, "id", range(1, len(normalized) + 1))
            if "uploaded_at" not in normalized.columns:
                normalized["uploaded_at"] = datetime.now()
            return normalized.reindex(columns=INFERENCE_CONTEXT_COLUMNS)

        if table == PREDICTED_GAMES_TABLE:
            normalized = dataframe.copy()
            if "id" not in normalized.columns:
                normalized.insert(0, "id", range(1, len(normalized) + 1))
            return normalized.reindex(columns=PREDICTED_GAMES_COLUMNS)

        if table == CHECKPOINTS_SUMMARY_TABLE:
            return dataframe.reindex(columns=CHECKPOINTS_SUMMARY_COLUMNS)

        raise ValueError(f"Unsupported table: {table}")

    # -------------------------------------------------------------------------
    def persist(self, dataframe: pd.DataFrame, table: DatasetTable) -> None:
        if table == ROULETTE_SERIES_TABLE:
            self.serializer.save_roulette_series(dataframe)
            return
        if table == INFERENCE_CONTEXT_TABLE:
            self.serializer.save_inference_context(dataframe)
            return
        if table == PREDICTED_GAMES_TABLE:
            self.serializer.save_predicted_games(dataframe)
            return
        if table == CHECKPOINTS_SUMMARY_TABLE:
            self.serializer.upsert_checkpoints_summary(dataframe)
            return
        raise ValueError(f"Unsupported table: {table}")

    # -------------------------------------------------------------------------
    def import_dataframe(
        self,
        dataframe: pd.DataFrame,
        table: DatasetTable,
        dataset_name: str | None = None,
    ) -> int:
        normalized = self.normalize(dataframe, table, dataset_name)
        self.persist(normalized, table)
        return int(len(normalized))

