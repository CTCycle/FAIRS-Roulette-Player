from __future__ import annotations

import pandas as pd

from FAIRS.server.common.constants import DATASETS_TABLE, DATASET_OUTCOMES_TABLE
from FAIRS.server.repositories.database.backend import FAIRSDatabase, database


###############################################################################
class TrainingRepositoryQueries:
    def __init__(self, db: FAIRSDatabase = database) -> None:
        self.database = db

    # -------------------------------------------------------------------------
    def load_training_dataset(
        self,
        dataset_id: str | None = None,
    ) -> pd.DataFrame:
        training_datasets = self.database.load_filtered(
            DATASETS_TABLE,
            {"dataset_kind": "training"},
        )
        if training_datasets.empty or "dataset_id" not in training_datasets.columns:
            return pd.DataFrame()

        available_ids = {
            str(value)
            for value in training_datasets["dataset_id"].tolist()
            if isinstance(value, str) and value
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
        filtered = outcomes.loc[
            outcomes["dataset_id"].astype(str).isin(dataset_ids)
        ].copy()
        if filtered.empty:
            return filtered
        sort_columns = [
            column for column in ("dataset_id", "sequence_index") if column in filtered.columns
        ]
        if sort_columns:
            filtered = filtered.sort_values(sort_columns)
        if "outcome_id" in filtered.columns and "outcome" not in filtered.columns:
            filtered = filtered.assign(outcome=filtered["outcome_id"])
        return filtered
