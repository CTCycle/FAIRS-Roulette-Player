from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy
from sqlalchemy.sql.elements import TextClause


QUERY_LIMIT_ALL_ROWS = 9223372036854775807
SQLITE_FOREIGN_KEYS_PRAGMA = "PRAGMA foreign_keys=ON"
POSTGRES_DATABASE_EXISTS_QUERY = sqlalchemy.text(
    "SELECT 1 FROM pg_database WHERE datname=:name"
)
ROULETTE_OUTCOMES_COUNT_QUERY = sqlalchemy.text("SELECT COUNT(*) FROM roulette_outcomes")
ROULETTE_OUTCOMES_DELETE_QUERY = sqlalchemy.text("DELETE FROM roulette_outcomes")
ROULETTE_OUTCOMES_INSERT_QUERY = sqlalchemy.text(
    "INSERT INTO roulette_outcomes "
    "(outcome_id, color, color_code, wheel_position) "
    "VALUES (:outcome_id, :color, :color_code, :wheel_position)"
)


# -----------------------------------------------------------------------------
def build_create_database_query(database_name: str) -> TextClause:
    safe_database = database_name.replace('"', '""')
    return sqlalchemy.text(
        f'CREATE DATABASE "{safe_database}" WITH ENCODING \'UTF8\' TEMPLATE template0'
    )


# -----------------------------------------------------------------------------
def build_select_table_query(
    table_name: str,
    limit: int | None = None,
    offset: int | None = None,
) -> tuple[TextClause, dict[str, int]]:
    query = f'SELECT * FROM "{table_name}"'
    params: dict[str, int] = {}
    if limit is not None or offset is not None:
        params["limit"] = limit if limit is not None else QUERY_LIMIT_ALL_ROWS
        params["offset"] = offset if offset is not None else 0
        query += " LIMIT :limit OFFSET :offset"
    return sqlalchemy.text(query), params


# -----------------------------------------------------------------------------
def build_select_filtered_query(table_name: str, columns: Iterable[str]) -> TextClause:
    clauses = " AND ".join([f'"{key}" = :{key}' for key in columns])
    return sqlalchemy.text(f'SELECT * FROM "{table_name}" WHERE {clauses}')


# -----------------------------------------------------------------------------
def build_delete_filtered_query(table_name: str, columns: Iterable[str]) -> TextClause:
    clauses = " AND ".join([f'"{key}" = :{key}' for key in columns])
    return sqlalchemy.text(f'DELETE FROM "{table_name}" WHERE {clauses}')
