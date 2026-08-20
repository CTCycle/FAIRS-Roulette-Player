from __future__ import annotations

from typing import Any

import pandas as pd

from server.common.roulette import encode_roulette_series
from server.learning.training.generator import RouletteSyntheticGenerator
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.queries.training import TrainingRepositoryQueries
from server.repositories.serialization.training import TrainingDataSerializer

###############################################################################
class DataSerializerExtension:

    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        database = FAIRSDatabase()
        queries = TrainingRepositoryQueries(database)
        self.training_serializer = TrainingDataSerializer(queries)

    # -------------------------------------------------------------------------
    def generate_synthetic_dataset(self, configuration: dict[str, Any]) -> pd.DataFrame:
        generator = RouletteSyntheticGenerator(configuration)
        dataset = generator.generate()
        return dataset

    # -------------------------------------------------------------------------
    def get_training_series(
        self, configuration: dict[str, Any]
    ) -> tuple[pd.DataFrame, bool]:
        use_generator = configuration.get("use_data_generator", False)
        if use_generator:
            dataset = self.generate_synthetic_dataset(configuration)
            dataset = encode_roulette_series(dataset)
            dataset = dataset.rename(columns={"outcome": "extraction"})
            return dataset, True

        seed = configuration.get("seed", 42)
        sample_size = configuration.get("sample_size", 1.0)
        dataset_id = configuration.get("dataset_id")
        if not isinstance(dataset_id, int) or isinstance(dataset_id, bool):
            dataset_id = None
        dataset = self.training_serializer.load_training_series(
            sample_size=sample_size,
            seed=seed,
            dataset_id=dataset_id,
        )
        if "outcome" in dataset.columns and "extraction" not in dataset.columns:
            dataset = dataset.rename(columns={"outcome": "extraction"})
        if dataset.empty or "extraction" not in dataset.columns:
            if dataset_id:
                raise ValueError(
                    f"No roulette dataset available for dataset_id '{dataset_id}'."
                )
            raise ValueError("No roulette dataset available for training.")
        # Encoding is done at upload time - no need to encode again

        return dataset, False

__all__ = ["DataSerializerExtension"]
