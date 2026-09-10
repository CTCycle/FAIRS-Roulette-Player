from __future__ import annotations

from numbers import Integral

STRATEGY_KEEP = 0
STRATEGY_MARTINGALE = 1
STRATEGY_REVERSE = 2
STRATEGY_DALEMBERT = 3
STRATEGY_FIBONACCI = 4
STRATEGY_COUNT = 5

STRATEGY_NAMES = {
    STRATEGY_KEEP: "Keep",
    STRATEGY_MARTINGALE: "Martingale",
    STRATEGY_REVERSE: "Reverse",
    STRATEGY_DALEMBERT: "DAlembert",
    STRATEGY_FIBONACCI: "Fibonacci",
}

BET_OUTCOME_WIN = "win"
BET_OUTCOME_LOSS = "loss"
BET_OUTCOME_NEUTRAL = "neutral"

###############################################################################
def is_valid_strategy(strategy_id: object) -> bool:
    return (
        isinstance(strategy_id, Integral)
        and not isinstance(strategy_id, bool)
        and 0 <= int(strategy_id) < STRATEGY_COUNT
    )

###############################################################################
def require_strategy_id(strategy_id: object) -> int:
    if not is_valid_strategy(strategy_id):
        raise ValueError(
            f"Invalid betting strategy id {strategy_id!r}; expected 0-{STRATEGY_COUNT - 1}."
        )
    return int(strategy_id)

###############################################################################
def strategy_name(strategy_id: int) -> str:
    return STRATEGY_NAMES[require_strategy_id(strategy_id)]
