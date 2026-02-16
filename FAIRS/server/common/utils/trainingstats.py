from __future__ import annotations

import math
from typing import Any

from FAIRS.server.common.utils.types import coerce_finite_float, coerce_finite_int

TRAINING_METRIC_KEYS = (
    "loss",
    "rmse",
    "val_loss",
    "val_rmse",
    "reward",
    "val_reward",
    "total_reward",
    "capital",
    "capital_gain",
)


def coerce_optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(candidate):
        return candidate
    return None


def sanitize_training_stats(
    stats: dict[str, Any],
    *,
    allowed_statuses: set[str] | None = None,
) -> dict[str, Any]:
    if not stats:
        return {}

    sanitized: dict[str, Any] = {**stats}
    if "epoch" in stats:
        sanitized["epoch"] = coerce_finite_int(stats.get("epoch"), 0, minimum=0)
    if "total_epochs" in stats:
        sanitized["total_epochs"] = coerce_finite_int(
            stats.get("total_epochs"), 0, minimum=0
        )
    if "max_steps" in stats:
        sanitized["max_steps"] = coerce_finite_int(stats.get("max_steps"), 0, minimum=0)
    if "time_step" in stats:
        sanitized["time_step"] = coerce_finite_int(stats.get("time_step"), 0, minimum=0)

    for metric_key in TRAINING_METRIC_KEYS:
        if metric_key not in stats:
            continue
        sanitized[metric_key] = coerce_optional_finite_float(stats.get(metric_key))

    if allowed_statuses is not None:
        status_value = stats.get("status")
        if isinstance(status_value, str) and status_value in allowed_statuses:
            sanitized["status"] = status_value
        elif "status" in sanitized:
            sanitized.pop("status")

    return sanitized
