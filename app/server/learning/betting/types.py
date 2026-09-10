from __future__ import annotations

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
def validate_strategy_id(strategy_id: int) -> int:
    if isinstance(strategy_id, bool) or not isinstance(strategy_id, int):
        raise ValueError("Strategy id must be an integer.")
    if strategy_id < 0 or strategy_id >= STRATEGY_COUNT:
        raise ValueError(
            f"Strategy id must be between 0 and {STRATEGY_COUNT - 1}."
        )
    return strategy_id

###############################################################################
def strategy_name(strategy_id: int) -> str:
    return STRATEGY_NAMES[validate_strategy_id(strategy_id)]
