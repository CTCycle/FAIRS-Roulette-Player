from __future__ import annotations

from server.learning.betting.types import validate_strategy_id

###############################################################################
class StrategyHold:

    # -------------------------------------------------------------------------
    def __init__(self, hold_steps: int = 1) -> None:
        if isinstance(hold_steps, bool) or not isinstance(hold_steps, int):
            raise ValueError("Strategy hold steps must be an integer.")
        if hold_steps < 1:
            raise ValueError("Strategy hold steps must be at least 1.")
        self.hold_steps = hold_steps
        self.current_strategy_id: int | None = None
        self.hold_remaining = 0

    # -------------------------------------------------------------------------
    def reset(self, strategy_id: int | None = None) -> None:
        self.current_strategy_id = (
            validate_strategy_id(strategy_id) if strategy_id is not None else None
        )
        self.hold_remaining = 0

    # -------------------------------------------------------------------------
    def resolve(self, selected_strategy_id: int) -> int:
        if self.current_strategy_id is not None and self.hold_remaining > 0:
            self.hold_remaining -= 1
            return self.current_strategy_id

        next_strategy = validate_strategy_id(selected_strategy_id)
        self.current_strategy_id = next_strategy
        self.hold_remaining = self.hold_steps - 1
        return next_strategy
