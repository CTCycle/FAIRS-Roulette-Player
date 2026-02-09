from __future__ import annotations

import pandas as pd

from FAIRS.server.common.constants import ROULETTE_SERIES_TABLE
from FAIRS.server.repositories.database.backend import FAIRSDatabase, database


###############################################################################
class TrainingRepositoryQueries:
    def __init__(self, db: FAIRSDatabase = database) -> None:
        self.database = db

    # -------------------------------------------------------------------------
    def load_training_dataset(
        self,
        name: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> pd.DataFrame:
        if name:
            return self.database.load_filtered(
                ROULETTE_SERIES_TABLE,
                {"name": name},
            )
        return self.database.load_from_database(
            ROULETTE_SERIES_TABLE,
            limit=limit,
            offset=offset,
        )
