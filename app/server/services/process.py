from __future__ import annotations

import pandas as pd

from server.common.constants import (
    ROULETTE_COLOR_CODE,
    ROULETTE_COLOR_MAP,
    ROULETTE_POSITION_MAP,
)

###############################################################################
class RouletteSeriesEncoder:

    # -------------------------------------------------------------------------
    def encode(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        if "outcome" not in dataframe.columns:
            raise ValueError("Missing required column: outcome")

        reverse_color_map = {
            value: key for key, values in ROULETTE_COLOR_MAP.items() for value in values
        }

        dataframe["wheel_position"] = dataframe["outcome"].map(ROULETTE_POSITION_MAP)
        dataframe["color"] = dataframe["outcome"].map(reverse_color_map)
        dataframe["color_code"] = dataframe["color"].map(ROULETTE_COLOR_CODE)

        return dataframe
