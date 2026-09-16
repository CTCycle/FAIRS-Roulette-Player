from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from server.common.constants import ROULETTE_COLOR_MAP
from server.common.roulette import (
    build_roulette_number_pool,
    filter_roulette_series,
    validate_roulette_outcome,
)
from server.contracts.configuration import JsonRouletteSettings, RouletteSettings
from server.learning.training.environment import RouletteWheelRenderer

###############################################################################
def test_number_pool_applies_range_and_zero_exclusion() -> None:
    assert build_roulette_number_pool(5, 8) == (5, 6, 7, 8)
    assert build_roulette_number_pool(0, 3, exclude_zero=True) == (1, 2, 3)

###############################################################################
def test_invalid_or_empty_number_pool_is_rejected() -> None:
    with pytest.raises(ValueError, match="minimum"):
        build_roulette_number_pool(12, 4)
    with pytest.raises(ValueError, match="at least one"):
        build_roulette_number_pool(0, 0, exclude_zero=True)
    with pytest.raises(ValidationError, match="at least one"):
        JsonRouletteSettings(
            minimum_number=0,
            maximum_number=0,
            exclude_zero=True,
        )

###############################################################################
def test_series_filter_and_single_outcome_validation_use_same_pool() -> None:
    source = pd.DataFrame({"outcome": [0, 1, 2, 3, 4, 5]})

    filtered = filter_roulette_series(
        source,
        minimum_number=1,
        maximum_number=4,
        exclude_zero=True,
    )

    assert filtered["outcome"].tolist() == [1, 2, 3, 4]
    assert validate_roulette_outcome(
        4,
        minimum_number=1,
        maximum_number=4,
        exclude_zero=True,
    ) == 4
    with pytest.raises(ValueError, match="configured number pool"):
        validate_roulette_outcome(
            0,
            minimum_number=1,
            maximum_number=4,
            exclude_zero=True,
        )

###############################################################################
def test_renderer_inverts_visual_colors_without_changing_zero() -> None:
    red_numbers = ROULETTE_COLOR_MAP["red"]
    black_numbers = ROULETTE_COLOR_MAP["black"]
    normal = RouletteWheelRenderer(red_numbers, black_numbers)
    inverted = RouletteWheelRenderer(
        red_numbers,
        black_numbers,
        RouletteSettings(invert_colors=True, show_number_labels=False),
    )

    red_number = red_numbers[0]
    black_number = black_numbers[0]
    assert normal.get_number_color(red_number) == normal.base_red
    assert normal.get_number_color(black_number) == normal.base_black
    assert inverted.get_number_color(red_number) == inverted.base_black
    assert inverted.get_number_color(black_number) == inverted.base_red
    assert inverted.get_number_color(0) == inverted.base_green
    assert inverted.show_number_labels is False
