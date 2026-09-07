from __future__ import annotations

import pandas as pd

from server.common.constants import (
    ROULETTE_COLOR_CODE,
    ROULETTE_COLOR_MAP,
    ROULETTE_POSITION_MAP,
)

###############################################################################
def encode_roulette_series(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return roulette outcomes enriched with the canonical wheel features."""
    if "outcome" not in dataframe.columns:
        raise ValueError("Missing required column: outcome")

    encoded = dataframe.copy()
    reverse_color_map = {
        value: key for key, values in ROULETTE_COLOR_MAP.items() for value in values
    }
    encoded["wheel_position"] = encoded["outcome"].map(ROULETTE_POSITION_MAP)
    encoded["color"] = encoded["outcome"].map(reverse_color_map)
    encoded["color_code"] = encoded["color"].map(ROULETTE_COLOR_CODE)
    return encoded


__all__ = ["encode_roulette_series"]
