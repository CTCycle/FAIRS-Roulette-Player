from __future__ import annotations

import pytest

from server.learning.betting.hold import StrategyHold

###############################################################################
def test_hold_persists_strategy_for_configured_steps() -> None:
    selector = StrategyHold(hold_steps=3)

    assert selector.resolve(2) == 2
    assert selector.resolve(1) == 2
    assert selector.resolve(4) == 2
    assert selector.resolve(1) == 1

###############################################################################
def test_hold_requires_explicit_selection_when_uninitialized() -> None:
    selector = StrategyHold(hold_steps=2)

    with pytest.raises((TypeError, ValueError)):
        selector.resolve(None)  # type: ignore[arg-type]

###############################################################################
def test_hold_reset_clears_previous_strategy_state() -> None:
    selector = StrategyHold(hold_steps=3)
    assert selector.resolve(2) == 2
    assert selector.resolve(4) == 2

    selector.reset()
    assert selector.current_strategy_id is None
    assert selector.resolve(3) == 3
    assert selector.resolve(1) == 3
    assert selector.resolve(1) == 3
    assert selector.resolve(1) == 1

###############################################################################
def test_hold_steps_is_clamped_to_minimum_one() -> None:
    selector = StrategyHold(hold_steps=0)
    assert selector.resolve(4) == 4
    assert selector.resolve(2) == 2
