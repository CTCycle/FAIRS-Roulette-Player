from __future__ import annotations

from FAIRS.server.learning.betting.sizer import BetSizer
from FAIRS.server.learning.betting.types import (
    STRATEGY_DALEMBERT,
    STRATEGY_FIBONACCI,
    STRATEGY_KEEP,
    STRATEGY_MARTINGALE,
    STRATEGY_REVERSE,
)


def test_keep_strategy_preserves_bet() -> None:
    sizer = BetSizer({"bet_amount": 10, "initial_capital": 1000})
    assert sizer.apply(STRATEGY_KEEP, capital=1000) == 10
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_KEEP, capital=1000) == 10


def test_martingale_strategy_updates_deterministically() -> None:
    sizer = BetSizer({"bet_amount": 10, "initial_capital": 1000})
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 20
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 10


def test_reverse_strategy_updates_deterministically() -> None:
    sizer = BetSizer({"bet_amount": 10, "initial_capital": 1000})
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_REVERSE, capital=1000) == 20
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_REVERSE, capital=1000) == 40
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_REVERSE, capital=1000) == 10


def test_dalembert_strategy_updates_deterministically() -> None:
    sizer = BetSizer({"bet_amount": 10, "bet_unit": 5, "initial_capital": 1000})
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 15
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 20
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 15
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_DALEMBERT, capital=1000) == 10


def test_fibonacci_strategy_updates_deterministically() -> None:
    sizer = BetSizer({"bet_amount": 10, "initial_capital": 1000})
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 10
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 20
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 30
    sizer.set_last_outcome_from_reward(10)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 10


def test_bounds_with_bet_max_and_capital_limit() -> None:
    sizer = BetSizer(
        {
            "bet_amount": 10,
            "initial_capital": 1000,
            "bet_max": 25,
            "bet_enforce_capital": True,
        }
    )
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 20
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 25
    sizer.set_last_outcome_from_reward(-10)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=12) == 12


def test_neutral_outcome_does_not_progress_sequences() -> None:
    sizer = BetSizer({"bet_amount": 10, "initial_capital": 1000})
    sizer.set_last_outcome_from_reward(0)
    assert sizer.apply(STRATEGY_MARTINGALE, capital=1000) == 10
    sizer.set_last_outcome_from_reward(0)
    assert sizer.apply(STRATEGY_FIBONACCI, capital=1000) == 10


def test_none_bet_unit_falls_back_to_base_bet() -> None:
    sizer = BetSizer({"bet_amount": 10, "bet_unit": None, "initial_capital": 1000})
    assert sizer.unit == 10
