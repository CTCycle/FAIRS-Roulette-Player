from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from FAIRS.app.utils.constants import NUMBERS


###############################################################################
class RouletteSyntheticGenerator:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.configuration = configuration
        self.seed: int | None = configuration.get("seed")
        perceptive_size = int(configuration.get("perceptive_field_size", 64))
        max_steps = int(configuration.get("max_steps_episode", 0))
        requested_samples = int(configuration.get("num_generated_samples", 10000))

        minimum_length = max(perceptive_size * 2, perceptive_size + 1)
        if max_steps:
            minimum_length = max(minimum_length, max_steps)

        self.series_length = max(requested_samples, minimum_length)

    # -------------------------------------------------------------------------
    def generate(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        extractions = rng.integers(low=0, high=NUMBERS, size=self.series_length)
        dataframe = pd.DataFrame({"extraction": extractions.astype(int)})

        return dataframe
