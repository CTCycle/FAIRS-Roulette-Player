from __future__ import annotations

import pandas as pd

from server.common.constants import DATASET_OUTCOMES_WRITE_COLUMNS
from server.domain.upload import DatasetKind
from server.repositories.serialization.data import DataSerializer


###############################################################################
class DatasetImportService:
    def __init__(self, serializer: DataSerializer) -> None:
        self.serializer = serializer

    # -------------------------------------------------------------------------
    def normalize(
        self,
        dataframe: pd.DataFrame,
        dataset_kind: DatasetKind,
    ) -> tuple[pd.DataFrame, str]:
        if dataframe.empty:
            return dataframe, dataset_kind

        if dataset_kind == "training":
            return self.normalize_training_dataset(dataframe), "training"

        if dataset_kind == "inference":
            return self.normalize_inference_dataset(dataframe), "inference"

        raise ValueError(f"Unsupported dataset kind: {dataset_kind}")

    # -------------------------------------------------------------------------
    def normalize_training_dataset(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        if len(dataframe.columns) < 2:
            raise ValueError(
                "Roulette upload must contain two columns: extraction index and outcome."
            )

        normalized = pd.DataFrame(
            {
                "sequence_index": pd.to_numeric(dataframe.iloc[:, 0], errors="coerce"),
                "outcome_id": pd.to_numeric(dataframe.iloc[:, 1], errors="coerce"),
            }
        )
        integer_mask = (
            normalized["sequence_index"].notna()
            & normalized["outcome_id"].notna()
            & normalized["sequence_index"].mod(1).eq(0)
            & normalized["outcome_id"].mod(1).eq(0)
        )
        normalized = normalized.loc[integer_mask].copy()
        if normalized.empty:
            raise ValueError(
                "No valid roulette rows found. Extraction index and outcome must be integers."
            )

        normalized["sequence_index"] = normalized["sequence_index"].astype(int)
        normalized["outcome_id"] = normalized["outcome_id"].astype(int)
        normalized = normalized.loc[
            normalized["sequence_index"].ge(0) & normalized["outcome_id"].between(0, 36)
        ].copy()
        if normalized.empty:
            raise ValueError(
                "No valid roulette outcomes found. Outcomes must be in the range 0 to 36."
            )
        return normalized.reindex(columns=DATASET_OUTCOMES_WRITE_COLUMNS)

    # -------------------------------------------------------------------------
    def normalize_inference_dataset(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe
        source = dataframe.copy()
        if "outcome" in source.columns:
            outcomes = pd.to_numeric(source["outcome"], errors="coerce")
        else:
            outcomes = pd.to_numeric(source.iloc[:, 0], errors="coerce")

        normalized = pd.DataFrame({"outcome_id": outcomes})
        normalized = normalized.loc[
            normalized["outcome_id"].notna() & normalized["outcome_id"].mod(1).eq(0)
        ].copy()
        if normalized.empty:
            raise ValueError("No valid roulette outcomes found for inference context.")
        normalized["outcome_id"] = normalized["outcome_id"].astype(int)
        normalized = normalized.loc[normalized["outcome_id"].between(0, 36)].copy()
        if normalized.empty:
            raise ValueError(
                "No valid roulette outcomes found. Outcomes must be in the range 0 to 36."
            )
        normalized.insert(0, "sequence_index", range(len(normalized)))
        return normalized.reindex(columns=DATASET_OUTCOMES_WRITE_COLUMNS)

    # -------------------------------------------------------------------------
    def import_dataframe(
        self,
        dataframe: pd.DataFrame,
        dataset_kind: DatasetKind,
        dataset_name: str | None = None,
    ) -> dict[str, object]:
        normalized, dataset_kind = self.normalize(dataframe, dataset_kind)
        if dataset_name is not None and dataset_name.strip():
            clean_name = dataset_name.strip()
        else:
            clean_name = "dataset" if dataset_kind == "training" else "context"
        return self.serializer.import_dataset(
            dataset_name=clean_name,
            dataset_kind=dataset_kind,
            outcomes=normalized,
        )
