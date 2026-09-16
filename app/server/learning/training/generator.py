from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from server.common.roulette import build_roulette_number_pool
from server.contracts.configuration import RouletteSettings

###############################################################################
class RouletteSyntheticGenerator:

    # -------------------------------------------------------------------------
    def __init__(
        self,
        configuration: dict[str, Any],
        roulette_settings: RouletteSettings | None = None,
    ) -> None:
        self.configuration = configuration
        self.roulette_settings = roulette_settings or RouletteSettings()
        self.seed = int(configuration["seed"])
        perceptive_size = int(configuration["perceptive_field_size"])
        max_steps = int(configuration["max_steps_episode"])
        requested_samples = int(configuration["num_generated_samples"])

        minimum_length = max(perceptive_size * 2, perceptive_size + 1, max_steps)
        self.series_length = max(requested_samples, minimum_length)

    # -------------------------------------------------------------------------
    def generate(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        pool = np.asarray(
            build_roulette_number_pool(
                minimum_number=self.roulette_settings.minimum_number,
                maximum_number=self.roulette_settings.maximum_number,
                exclude_zero=self.roulette_settings.exclude_zero,
            ),
            dtype=np.int32,
        )
        extractions = rng.choice(pool, size=self.series_length, replace=True)
        return pd.DataFrame({"outcome": extractions.astype(int)})
