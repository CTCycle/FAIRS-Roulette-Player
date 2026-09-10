from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from server.common.constants import NUMBERS

###############################################################################
class RouletteSyntheticGenerator:

    # -------------------------------------------------------------------------
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.configuration = configuration
        self.seed = int(configuration["seed"])
        perceptive_size = int(configuration["perceptive_field_size"])
        max_steps = int(configuration["max_steps_episode"])
        requested_samples = int(configuration["num_generated_samples"])

        minimum_length = max(perceptive_size * 2, perceptive_size + 1, max_steps)
        self.series_length = max(requested_samples, minimum_length)

    # -------------------------------------------------------------------------
    def generate(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        extractions = rng.integers(low=0, high=NUMBERS, size=self.series_length)
        return pd.DataFrame({"outcome": extractions.astype(int)})
