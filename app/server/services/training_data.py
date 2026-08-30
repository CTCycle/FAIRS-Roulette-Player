from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from server.common.roulette import encode_roulette_series
from server.configurations import DatabaseSettings
from server.learning.training.generator import RouletteSyntheticGenerator
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.datasets import DatasetRepository


###############################################################################
class TrainingDataService:
    """Load or generate training series outside the learning core."""

    # -------------------------------------------------------------------------
    def __init__(
        self,
        database_settings: DatabaseSettings | None,
        database_path: str | Path | None = None,
    ) -> None:
        self.database_settings = database_settings
        self.database_path = database_path

    # -------------------------------------------------------------------------
    @staticmethod
    def generate_synthetic_dataset(configuration: dict[str, Any]) -> pd.DataFrame:
        return RouletteSyntheticGenerator(configuration).generate()

    # -------------------------------------------------------------------------
    def _load_training_series(
        self,
        sample_size: float,
        seed: int,
        dataset_id: int | None,
    ) -> pd.DataFrame:
        if self.database_settings is None:
            raise RuntimeError(
                "Training database settings are required for a stored dataset."
            )

        database = FAIRSDatabase(
            self.database_settings,
            database_path=self.database_path,
        )
        try:
            dataset = DatasetRepository(database).training_outcomes(dataset_id)
        finally:
            database.dispose()

        if dataset.empty:
            return dataset
        dataset = encode_roulette_series(dataset)
        if sample_size < 1.0:
            dataset = dataset.sample(frac=sample_size, random_state=seed)
        return dataset

    # -------------------------------------------------------------------------
    def get_training_series(
        self,
        configuration: dict[str, Any],
    ) -> tuple[pd.DataFrame, bool]:
        if configuration["use_data_generator"]:
            dataset = encode_roulette_series(
                self.generate_synthetic_dataset(configuration)
            )
            dataset = dataset.rename(columns={"outcome": "extraction"})
            return dataset, True

        seed = configuration["seed"]
        sample_size = configuration["sample_size"]
        dataset_id = configuration["dataset_id"]
        if dataset_id is not None and (
            isinstance(dataset_id, bool) or not isinstance(dataset_id, int)
        ):
            raise ValueError("dataset_id must be an integer or null.")
        dataset = self._load_training_series(sample_size, seed, dataset_id)
        if "outcome" in dataset.columns and "extraction" not in dataset.columns:
            dataset = dataset.rename(columns={"outcome": "extraction"})
        if dataset.empty or "extraction" not in dataset.columns:
            if dataset_id:
                raise ValueError(
                    f"No roulette dataset available for dataset_id '{dataset_id}'."
                )
            raise ValueError("No roulette dataset available for training.")
        return dataset, False


###############################################################################
def load_training_series(
    configuration: dict[str, Any],
    database_settings: DatabaseSettings | None,
    database_path: str | Path | None,
) -> tuple[pd.DataFrame, bool]:
    """Pickle-safe application callback used by the training process."""
    return TrainingDataService(database_settings, database_path).get_training_series(
        configuration
    )


__all__ = ["TrainingDataService", "load_training_series"]
