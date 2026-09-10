"""Dynamic betting engine used by training and inference.

The engine consumes the canonical training betting keys. Inference explicitly maps
its game capital and bet into those keys before constructing the engine, so there is
no secondary ``game_*`` compatibility path inside this module.
"""

from __future__ import annotations

from typing import Any

from server.learning.betting.types import (
    BET_OUTCOME_LOSS,
    BET_OUTCOME_NEUTRAL,
    BET_OUTCOME_WIN,
    STRATEGY_DALEMBERT,
    STRATEGY_FIBONACCI,
    STRATEGY_KEEP,
    STRATEGY_MARTINGALE,
    STRATEGY_REVERSE,
    require_strategy_id,
)

###############################################################################
class BetSizer:

    # -------------------------------------------------------------------------
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.base_bet = max(1, int(configuration["bet_amount"]))

        configured_unit = configuration["bet_unit"]
        if configured_unit is None:
            configured_unit = self.base_bet
        self.unit = max(1, int(configured_unit))
        self.bet_enforce_capital = bool(configuration["bet_enforce_capital"])
        self.bet_max = self._resolve_bet_max(configuration)

        self.current_bet = self.base_bet
        self.fib_index = 0
        self.fib_values = [self.base_bet, self.base_bet]
        self.last_outcome = BET_OUTCOME_NEUTRAL

    # -------------------------------------------------------------------------
    def _resolve_bet_max(self, configuration: dict[str, Any]) -> int:
        configured_bet_max = configuration["bet_max"]
        if configured_bet_max is not None:
            return max(1, int(configured_bet_max))

        capital_cap = max(1, int(configuration["initial_capital"]))
        conservative_cap = max(self.base_bet, self.base_bet * 128)
        return max(1, min(capital_cap, conservative_cap))

    # -------------------------------------------------------------------------
    def _clamp_bet(self, bet_amount: int | float, capital: int | float | None) -> int:
        resolved = max(1, int(round(float(bet_amount))))
        resolved = min(resolved, self.bet_max)
        if self.bet_enforce_capital and capital is not None:
            resolved = min(resolved, max(1, int(capital)))
        return max(1, int(resolved))

    # -------------------------------------------------------------------------
    def _ensure_fib_index(self, target_index: int) -> None:
        while target_index >= len(self.fib_values):
            self.fib_values.append(self.fib_values[-1] + self.fib_values[-2])

    # -------------------------------------------------------------------------
    def set_last_outcome_from_reward(self, reward: int | float) -> str:
        reward_value = float(reward)
        if reward_value > 0:
            self.last_outcome = BET_OUTCOME_WIN
        elif reward_value < 0:
            self.last_outcome = BET_OUTCOME_LOSS
        else:
            self.last_outcome = BET_OUTCOME_NEUTRAL
        return self.last_outcome

    # -------------------------------------------------------------------------
    def set_base_bet(self, bet_amount: int, capital: int | float | None = None) -> None:
        resolved_base = max(1, int(bet_amount))
        self.base_bet = resolved_base
        self.unit = max(1, self.unit)
        self.fib_values = [resolved_base, resolved_base]
        self.fib_index = 0
        self.current_bet = self._clamp_bet(resolved_base, capital)

    # -------------------------------------------------------------------------
    def set_current_bet(
        self, bet_amount: int, capital: int | float | None = None
    ) -> int:
        self.current_bet = self._clamp_bet(bet_amount, capital)
        return self.current_bet

    # -------------------------------------------------------------------------
    def _resolve_next_bet(self, strategy_id: int) -> int:
        if strategy_id == STRATEGY_KEEP:
            return self.current_bet

        if self.last_outcome == BET_OUTCOME_NEUTRAL:
            return self.current_bet

        if strategy_id == STRATEGY_MARTINGALE:
            if self.last_outcome == BET_OUTCOME_LOSS:
                return self.current_bet * 2
            return self.base_bet

        if strategy_id == STRATEGY_REVERSE:
            if self.last_outcome == BET_OUTCOME_WIN:
                return self.current_bet * 2
            return self.base_bet

        if strategy_id == STRATEGY_DALEMBERT:
            if self.last_outcome == BET_OUTCOME_LOSS:
                return self.current_bet + self.unit
            if self.current_bet > self.base_bet:
                return self.current_bet - self.unit
            return self.base_bet

        if strategy_id == STRATEGY_FIBONACCI:
            if self.last_outcome == BET_OUTCOME_LOSS:
                self.fib_index += 1
            elif self.last_outcome == BET_OUTCOME_WIN:
                self.fib_index = max(0, self.fib_index - 2)
            self._ensure_fib_index(self.fib_index)
            return self.fib_values[self.fib_index]

        raise ValueError(f"Unsupported betting strategy id: {strategy_id}")

    # -------------------------------------------------------------------------
    def preview(self, strategy_id: int, capital: int | float | None = None) -> int:
        validated_strategy = require_strategy_id(strategy_id)
        previous_bet = self.current_bet
        previous_index = self.fib_index
        next_bet = self._resolve_next_bet(validated_strategy)
        self.current_bet = previous_bet
        self.fib_index = previous_index
        return self._clamp_bet(next_bet, capital)

    # -------------------------------------------------------------------------
    def apply(self, strategy_id: int, capital: int | float | None = None) -> int:
        validated_strategy = require_strategy_id(strategy_id)
        next_bet = self._resolve_next_bet(validated_strategy)
        self.current_bet = self._clamp_bet(next_bet, capital)
        return self.current_bet
