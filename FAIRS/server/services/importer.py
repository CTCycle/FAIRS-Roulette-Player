from __future__ import annotations

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
from FAIRS.server.repositories.serialization.data import DataSerializer
from FAIRS.server.services.process import RouletteSeriesEncoder

DatasetTable = Literal[
    "roulette_series",
    "inference_context",
    "game_sessions",
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
        name: str | None = None,
    ) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe

        if table == ROULETTE_SERIES_TABLE:
            return self.normalize_roulette_series(dataframe, name)

        if table == INFERENCE_CONTEXT_TABLE:
            normalized = dataframe.copy()
            if name is not None:
                cleaned_name = name.strip()
                normalized["name"] = cleaned_name if cleaned_name else "context"
            elif "name" not in normalized.columns:
                normalized["name"] = "context"
            if "outcome" not in normalized.columns and len(normalized.columns) > 0:
                first_col = normalized.columns[0]
                normalized = normalized.rename(columns={first_col: "outcome"})
            if "uploaded_at" not in normalized.columns:
                normalized["uploaded_at"] = datetime.now()
            return normalized.reindex(columns=INFERENCE_CONTEXT_COLUMNS)

        if table == GAME_SESSIONS_TABLE:
            normalized = dataframe.copy()
            if "observed_outcome" not in normalized.columns:
                normalized["observed_outcome"] = None
            return normalized.reindex(columns=GAME_SESSIONS_COLUMNS)

        raise ValueError(f"Unsupported table: {table}")

    # -------------------------------------------------------------------------
    def normalize_roulette_series(
        self,
        dataframe: pd.DataFrame,
        name: str | None = None,
    ) -> pd.DataFrame:
        if len(dataframe.columns) < 2:
            raise ValueError(
                "Roulette upload must contain two columns: extraction index and outcome."
            )

        normalized = pd.DataFrame(
            {
                "series_id": pd.to_numeric(dataframe.iloc[:, 0], errors="coerce"),
                "outcome": pd.to_numeric(dataframe.iloc[:, 1], errors="coerce"),
            }
        )
        integer_mask = (
            normalized["series_id"].notna()
            & normalized["outcome"].notna()
            & normalized["series_id"].mod(1).eq(0)
            & normalized["outcome"].mod(1).eq(0)
        )
        normalized = normalized.loc[integer_mask].copy()
        if normalized.empty:
            raise ValueError(
                "No valid roulette rows found. Extraction index and outcome must be integers."
            )

        normalized["series_id"] = normalized["series_id"].astype(int)
        normalized["outcome"] = normalized["outcome"].astype(int)
        normalized = normalized.loc[normalized["outcome"].between(0, 36)].copy()
        if normalized.empty:
            raise ValueError(
                "No valid roulette outcomes found. Outcomes must be in the range 0 to 36."
            )

        if name is not None:
            cleaned_name = name.strip()
            normalized["name"] = cleaned_name if cleaned_name else "default"
        else:
            normalized["name"] = "default"

        normalized = self.encoder.encode(normalized)
        return normalized.reindex(columns=ROULETTE_SERIES_COLUMNS)

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
        name: str | None = None,
    ) -> int:
        normalized = self.normalize(dataframe, table, name)
        self.persist(normalized, table)
        return int(len(normalized))

