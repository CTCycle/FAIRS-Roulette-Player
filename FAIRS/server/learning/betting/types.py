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


# -----------------------------------------------------------------------------
def is_valid_strategy(strategy_id: int) -> bool:
    return 0 <= int(strategy_id) < STRATEGY_COUNT


# -----------------------------------------------------------------------------
def normalize_strategy_id(strategy_id: int | None, default: int = STRATEGY_KEEP) -> int:
    if strategy_id is None:
        return int(default)
    candidate = int(strategy_id)
    if is_valid_strategy(candidate):
        return candidate
    return int(default)


# -----------------------------------------------------------------------------
def strategy_name(strategy_id: int) -> str:
    normalized = normalize_strategy_id(strategy_id)
    return STRATEGY_NAMES.get(normalized, STRATEGY_NAMES[STRATEGY_KEEP])
