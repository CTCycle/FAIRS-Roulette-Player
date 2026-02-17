from __future__ import annotations

from FAIRS.server.learning.betting.hold import StrategyHold


def test_hold_persists_strategy_for_configured_steps() -> None:
    selector = StrategyHold(hold_steps=3, fallback_strategy_id=0)

    assert selector.resolve(2) == 2
    assert selector.resolve(1) == 2
    assert selector.resolve(4) == 2
    assert selector.resolve(1) == 1


def test_hold_uses_fallback_when_selection_missing() -> None:
    selector = StrategyHold(hold_steps=2, fallback_strategy_id=3)
    assert selector.resolve(None) == 3
    assert selector.resolve(1) == 3
    assert selector.resolve(1) == 1
