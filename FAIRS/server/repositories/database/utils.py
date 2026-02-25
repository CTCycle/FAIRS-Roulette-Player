from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import pandas as pd
from sqlalchemy.sql.sqltypes import Date, DateTime

# -----------------------------------------------------------------------------
def normalize_postgres_engine(engine: str | None) -> str:
    if not engine:
        return "postgresql+psycopg"
    lowered = engine.lower()
    if lowered in {"postgres", "postgresql"}:
        return "postgresql+psycopg"
    return engine


# -----------------------------------------------------------------------------
def normalize_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        parsed = pd.to_datetime(candidate, errors="coerce")
        if pd.isna(parsed):
            return None
        if isinstance(parsed, pd.Timestamp):
            return parsed.to_pydatetime()
        if isinstance(parsed, datetime):
            return parsed
    return None


# -----------------------------------------------------------------------------
def coerce_value_for_sql_column(value: Any, column_type: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(column_type, DateTime):
        normalized = normalize_datetime_value(value)
        return normalized if normalized is not None else value
    if isinstance(column_type, Date):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        normalized = normalize_datetime_value(value)
        return normalized.date() if normalized is not None else value
    return value
