from __future__ import annotations

from FAIRS.server.learning.betting.types import STRATEGY_KEEP, normalize_strategy_id


###############################################################################
class StrategyHold:
    def __init__(
        self,
        hold_steps: int = 1,
        fallback_strategy_id: int = STRATEGY_KEEP,
    ) -> None:
        self.hold_steps = max(1, int(hold_steps))
        self.fallback_strategy_id = normalize_strategy_id(fallback_strategy_id)
        self.current_strategy_id: int | None = None
        self.hold_remaining = 0

    # -------------------------------------------------------------------------
    def reset(self, strategy_id: int | None = None) -> None:
        self.current_strategy_id = (
            normalize_strategy_id(strategy_id, self.fallback_strategy_id)
            if strategy_id is not None
            else None
        )
        self.hold_remaining = 0

    # -------------------------------------------------------------------------
    def resolve(self, selected_strategy_id: int | None) -> int:
        if self.current_strategy_id is not None and self.hold_remaining > 0:
            self.hold_remaining -= 1
            return self.current_strategy_id

        next_strategy = normalize_strategy_id(
            selected_strategy_id, self.fallback_strategy_id
        )
        self.current_strategy_id = next_strategy
        self.hold_remaining = max(0, self.hold_steps - 1)
        return next_strategy
