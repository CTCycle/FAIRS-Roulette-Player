from __future__ import annotations

from typing import Any

import pandas as pd

from FAIRS.server.learning.training.generator import RouletteSyntheticGenerator
from FAIRS.server.repositories.serialization.model import ModelSerializer
from FAIRS.server.repositories.serialization.training import TrainingDataSerializer
from FAIRS.server.services.process import RouletteSeriesEncoder


###############################################################################
class DataSerializerExtension:
    def __init__(self) -> None:
        self.encoder = RouletteSeriesEncoder()
        self.training_serializer = TrainingDataSerializer()

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
            dataset = self.encoder.encode(dataset)
            return dataset, True

        seed = configuration.get("seed", 42)
        sample_size = configuration.get("sample_size", 1.0)
        name = configuration.get("name")
        if isinstance(name, str):
            name = name.strip()
        if not name:
            name = None
        dataset = self.load_roulette_dataset(sample_size, seed, name)
        if "outcome" in dataset.columns and "extraction" not in dataset.columns:
            dataset = dataset.rename(columns={"outcome": "extraction"})
        if dataset.empty or "extraction" not in dataset.columns:
            if name:
                raise ValueError(
                    f"No roulette dataset available for '{name}'."
                )
            raise ValueError("No roulette dataset available for training.")
        # Encoding is done at upload time - no need to encode again

        return dataset, False

    # -------------------------------------------------------------------------
    def load_roulette_dataset(
        self,
        sample_size: float = 1.0,
        seed: int = 42,
        name: str | None = None,
    ) -> pd.DataFrame:
        return self.training_serializer.load_training_series(
            sample_size=sample_size,
            seed=seed,
            name=name,
        )


__all__ = ["DataSerializerExtension", "ModelSerializer"]
