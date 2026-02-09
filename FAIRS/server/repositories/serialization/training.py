from __future__ import annotations

import pandas as pd

from FAIRS.server.repositories.queries.training import TrainingRepositoryQueries


###############################################################################
class TrainingDataSerializer:
    def __init__(self, queries: TrainingRepositoryQueries | None = None) -> None:
        self.queries = queries or TrainingRepositoryQueries()

    # -------------------------------------------------------------------------
    def load_training_series(
        self,
        sample_size: float = 1.0,
        seed: int = 42,
        name: str | None = None,
    ) -> pd.DataFrame:
        dataset = self.queries.load_training_dataset(name=name)
        if dataset.empty:
            return dataset
        if sample_size < 1.0:
            dataset = dataset.sample(frac=sample_size, random_state=seed)
        return dataset
