from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from server.common.roulette import encode_roulette_series
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.schemas.models import DatasetOutcomes, Datasets

###############################################################################
class TrainingRepositoryQueries:

    # -------------------------------------------------------------------------
    def __init__(self, database: FAIRSDatabase) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    def load_training_dataset(self, dataset_id: int | None = None) -> pd.DataFrame:
        with self.database.Session() as session:
            stmt = select(DatasetOutcomes.dataset_id, DatasetOutcomes.sequence_index, DatasetOutcomes.outcome_id).join(Datasets, Datasets.dataset_id == DatasetOutcomes.dataset_id).where(Datasets.dataset_kind == "training")
            if dataset_id is not None:
                stmt = stmt.where(DatasetOutcomes.dataset_id == dataset_id)
            stmt = stmt.order_by(DatasetOutcomes.dataset_id, DatasetOutcomes.sequence_index)
            rows = session.execute(stmt).mappings().all()
        frame = pd.DataFrame(rows, columns=["dataset_id", "sequence_index", "outcome_id"])
        if frame.empty:
            return frame
        frame["outcome"] = frame["outcome_id"]
        return encode_roulette_series(frame)
