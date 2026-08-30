from __future__ import annotations

import math
from typing import Any


###############################################################################
def coerce_finite_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        candidate = float(value)
    except TypeError, ValueError:
        return default
    if math.isfinite(candidate):
        return candidate
    return default


###############################################################################
def coerce_finite_int(
    value: Any,
    default: int = 0,
    minimum: int | None = None,
) -> int:
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return default
        candidate = int(value)
        if minimum is not None and candidate < minimum:
            return minimum
        return candidate
    return default


__all__ = [
    "coerce_finite_float",
    "coerce_finite_int",
]
