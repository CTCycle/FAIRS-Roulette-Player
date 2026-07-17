from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from server.common.constants import ROULETTE_COLOR_CODE, ROULETTE_COLOR_MAP, ROULETTE_POSITION_MAP
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
        reverse_color = {number: color for color, numbers in ROULETTE_COLOR_MAP.items() for number in numbers}
        frame["color"] = frame["outcome_id"].map(reverse_color)
        frame["color_code"] = frame["color"].map(ROULETTE_COLOR_CODE)
        frame["wheel_position"] = frame["outcome_id"].map(ROULETTE_POSITION_MAP)
        return frame
