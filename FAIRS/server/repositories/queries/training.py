from __future__ import annotations

import pandas as pd

from FAIRS.server.common.constants import DATASETS_TABLE, DATASET_OUTCOMES_TABLE
from FAIRS.server.repositories.database.backend import FAIRSDatabase, database


###############################################################################
class TrainingRepositoryQueries:
    def __init__(self, db: FAIRSDatabase = database) -> None:
        self.database = db

    # -------------------------------------------------------------------------
    @staticmethod
    def normalize_dataset_id(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value > 0 else None
        if isinstance(value, float):
            if not value.is_integer():
                return None
            candidate = int(value)
            return candidate if candidate > 0 else None
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate.isdigit():
                return None
            resolved = int(candidate)
            return resolved if resolved > 0 else None
        return None

    # -------------------------------------------------------------------------
    def load_training_dataset(
        self,
        dataset_id: int | None = None,
    ) -> pd.DataFrame:
        training_datasets = self.database.load_filtered(
            DATASETS_TABLE,
            {"dataset_kind": "training"},
        )
        if training_datasets.empty or "dataset_id" not in training_datasets.columns:
            return pd.DataFrame()

        available_ids = {
            normalized
            for value in training_datasets["dataset_id"].tolist()
            for normalized in [self.normalize_dataset_id(value)]
            if normalized is not None
        }
        if dataset_id:
            if dataset_id not in available_ids:
                return pd.DataFrame()
            dataset_ids = {dataset_id}
        else:
            dataset_ids = available_ids
        if not dataset_ids:
            return pd.DataFrame()

        outcomes = self.database.load_from_database(DATASET_OUTCOMES_TABLE)
        if outcomes.empty or "dataset_id" not in outcomes.columns:
            return pd.DataFrame()
        normalized_outcome_ids = outcomes["dataset_id"].apply(self.normalize_dataset_id)
        filtered = outcomes.loc[
            normalized_outcome_ids.isin(dataset_ids)
        ].copy()
        if filtered.empty:
            return filtered
        filtered["dataset_id"] = normalized_outcome_ids.loc[
            normalized_outcome_ids.isin(dataset_ids)
        ].astype(int)
        sort_columns = [
            column for column in ("dataset_id", "sequence_index") if column in filtered.columns
        ]
        if sort_columns:
            filtered = filtered.sort_values(sort_columns)
        if "outcome_id" in filtered.columns and "outcome" not in filtered.columns:
            filtered = filtered.assign(outcome=filtered["outcome_id"])
        return filtered
