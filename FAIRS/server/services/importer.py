from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal

import pandas as pd

from FAIRS.server.common.constants import (
    GAME_SESSIONS_COLUMNS,
    GAME_SESSIONS_TABLE,
    INFERENCE_CONTEXT_COLUMNS,
    INFERENCE_CONTEXT_TABLE,
    ROULETTE_SERIES_COLUMNS,
    ROULETTE_SERIES_TABLE,
)
from FAIRS.server.repositories.serializer import DataSerializer
from FAIRS.server.services.process import RouletteSeriesEncoder

DatasetTable = Literal[
    "ROULETTE_SERIES",
    "INFERENCE_CONTEXT",
    "GAME_SESSIONS",
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
            # Rename first column to "extraction" if not already present
            if "extraction" not in normalized.columns and len(normalized.columns) > 0:
                first_col = normalized.columns[0]
                normalized = normalized.rename(columns={first_col: "extraction"})
            # Always encode to add color, color_code, and position
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

        if table == GAME_SESSIONS_TABLE:
            normalized = dataframe.copy()
            if "id" not in normalized.columns:
                normalized.insert(0, "id", range(1, len(normalized) + 1))
            return normalized.reindex(columns=GAME_SESSIONS_COLUMNS)

        raise ValueError(f"Unsupported table: {table}")

    # -------------------------------------------------------------------------
    def persist(self, dataframe: pd.DataFrame, table: DatasetTable) -> None:
        if table == ROULETTE_SERIES_TABLE:
            self.serializer.save_roulette_series(dataframe)
            return
        if table == INFERENCE_CONTEXT_TABLE:
            self.serializer.save_inference_context(dataframe)
            return
        if table == GAME_SESSIONS_TABLE:
            self.serializer.save_game_sessions(dataframe)
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

