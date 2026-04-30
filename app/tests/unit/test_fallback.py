from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd
import pytest


###############################################################################
class DummyModel:
    def predict(self, inputs: dict[str, Any], verbose: int = 0) -> np.ndarray:  # noqa: ARG002
        logits = np.zeros((1, 47), dtype=np.float32)
        logits[0, 12] = 1.0
        return logits


class EmptyLogitsModel:
    def predict(self, inputs: dict[str, Any], verbose: int = 0) -> np.ndarray:  # noqa: ARG002
        return np.zeros((1, 0), dtype=np.float32)


class DummySerializer:
    def __init__(self, outcomes: list[int]) -> None:
        self._frame = pd.DataFrame({"outcome": outcomes})

    def load_dataset_outcomes(self, dataset_id: int) -> pd.DataFrame:  # noqa: ARG002
        return self._frame


def test_fallback_strategy_is_deterministic_when_model_disabled() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from FAIRS.server.learning.inference.player import RoulettePlayer

    config = {
        "seed": 42,
        "perceptive_field_size": 4,
        "game_capital": 100,
        "game_bet": 10,
        "dynamic_betting_enabled": True,
        "bet_strategy_model_enabled": False,
        "bet_strategy_fixed_id": 3,
        "strategy_hold_steps": 2,
    }
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_id=1,
        serializer=DummySerializer([1, 2, 3, 4, 5, 6, 7, 8]),
    )

    prediction = player.predict_next()

    assert prediction["bet_strategy_id"] == 3
    assert prediction["bet_strategy_name"] == "DAlembert"
    assert prediction["suggested_bet_amount"] == 10
    assert prediction["current_bet_amount"] == 10


def test_predict_next_raises_when_model_returns_empty_logits() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from FAIRS.server.learning.inference.player import RoulettePlayer

    config = {
        "seed": 42,
        "perceptive_field_size": 4,
        "game_capital": 100,
        "game_bet": 10,
        "dynamic_betting_enabled": False,
    }
    player = RoulettePlayer(
        model=EmptyLogitsModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_id=1,
        serializer=DummySerializer([1, 2, 3, 4, 5, 6, 7, 8]),
    )
    with pytest.raises(ValueError, match="empty logits"):
        player.predict_next()


def test_predict_next_requires_minimum_context_length() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from FAIRS.server.learning.inference.player import RoulettePlayer

    config = {
        "seed": 42,
        "perceptive_field_size": 8,
        "game_capital": 100,
        "game_bet": 10,
        "dynamic_betting_enabled": False,
    }
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_id=1,
        serializer=DummySerializer([1, 2, 3]),
    )
    with pytest.raises(
        ValueError, match="at least the perceptive field size"
    ):
        player.predict_next()


def test_update_with_true_extraction_validates_input() -> None:
    os.environ.setdefault("KERAS_BACKEND", "torch")
    from FAIRS.server.learning.inference.player import RoulettePlayer

    config = {
        "seed": 42,
        "perceptive_field_size": 4,
        "game_capital": 100,
        "game_bet": 10,
        "dynamic_betting_enabled": False,
    }
    player = RoulettePlayer(
        model=DummyModel(),  # type: ignore[arg-type]
        configuration=config,
        session_id="session",
        dataset_id=1,
        serializer=DummySerializer([1, 2, 3, 4, 5, 6, 7, 8]),
    )
    player.predict_next()

    with pytest.raises(ValueError, match="must be an integer"):
        player.update_with_true_extraction("invalid")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="between 0 and 36"):
        player.update_with_true_extraction(37)
