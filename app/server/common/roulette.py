from __future__ import annotations

import pandas as pd

from server.common.constants import (
    ROULETTE_COLOR_CODE,
    ROULETTE_COLOR_MAP,
    ROULETTE_POSITION_MAP,
)

ROULETTE_RUNTIME_ATTR = "fairs_roulette_runtime_settings"

###############################################################################
def build_roulette_number_pool(
    minimum_number: int = 0,
    maximum_number: int = 36,
    exclude_zero: bool = False,
) -> tuple[int, ...]:
    """Return the validated roulette outcomes enabled by runtime settings."""
    if minimum_number < 0 or maximum_number > 36:
        raise ValueError("Roulette number range must stay between 0 and 36.")
    if minimum_number > maximum_number:
        raise ValueError("Roulette minimum number must not exceed maximum number.")

    pool = tuple(
        number
        for number in range(minimum_number, maximum_number + 1)
        if not (exclude_zero and number == 0)
    )
    if not pool:
        raise ValueError("Roulette number pool must contain at least one number.")
    return pool

###############################################################################
def filter_roulette_series(
    dataframe: pd.DataFrame,
    *,
    minimum_number: int = 0,
    maximum_number: int = 36,
    exclude_zero: bool = False,
    column: str = "outcome",
) -> pd.DataFrame:
    """Return roulette rows whose outcome belongs to the configured number pool."""
    if column not in dataframe.columns:
        raise ValueError(f"Missing required column: {column}")
    pool = set(
        build_roulette_number_pool(
            minimum_number=minimum_number,
            maximum_number=maximum_number,
            exclude_zero=exclude_zero,
        )
    )
    numeric = pd.to_numeric(dataframe[column], errors="coerce")
    return dataframe.loc[numeric.isin(pool)].reset_index(drop=True)

###############################################################################
def validate_roulette_outcome(
    outcome: int,
    *,
    minimum_number: int = 0,
    maximum_number: int = 36,
    exclude_zero: bool = False,
) -> int:
    """Validate one roulette outcome against the configured runtime pool."""
    if outcome not in build_roulette_number_pool(
        minimum_number=minimum_number,
        maximum_number=maximum_number,
        exclude_zero=exclude_zero,
    ):
        raise ValueError("Roulette outcome is outside the configured number pool.")
    return outcome

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


__all__ = [
    "ROULETTE_RUNTIME_ATTR",
    "build_roulette_number_pool",
    "encode_roulette_series",
    "filter_roulette_series",
    "validate_roulette_outcome",
]
