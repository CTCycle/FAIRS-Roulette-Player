from __future__ import annotations

from collections.abc import Callable
import urllib.parse
from typing import Any

import pandas as pd
import sqlalchemy
from sqlalchemy import UniqueConstraint, inspect
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from FAIRS.server.configurations import DatabaseSettings
from FAIRS.server.repositories.schema import Base
from FAIRS.server.repositories.utils import normalize_postgres_engine
from FAIRS.server.utils.logger import logger


###############################################################################
class PostgresRepository:
    def __init__(self, settings: DatabaseSettings) -> None:
        if not settings.host:
            raise ValueError("Database host must be provided for external database.")
        if not settings.database_name:
            raise ValueError(
                "Database name must be provided for external database."
            )
        if not settings.username:
            raise ValueError(
                "Database username must be provided for external database."
            )

        port = settings.port or 5432
        engine_name = normalize_postgres_engine(settings.engine)
        password = settings.password or ""
        connect_args: dict[str, Any] = {"connect_timeout": settings.connect_timeout}
        if settings.ssl:
            connect_args["sslmode"] = "require"
            if settings.ssl_ca:
                connect_args["sslrootcert"] = settings.ssl_ca

        safe_username = urllib.parse.quote_plus(settings.username)
        safe_password = urllib.parse.quote_plus(password)
        self.db_path: str | None = None
        self.engine: Engine = sqlalchemy.create_engine(
            f"{engine_name}://{safe_username}:{safe_password}@{settings.host}:{port}/{settings.database_name}",
            echo=False,
            future=True,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.insert_batch_size = settings.insert_batch_size

    # -------------------------------------------------------------------------
    def get_table_class(self, table_name: str) -> Any:
        for cls in Base.__subclasses__():
            if getattr(cls, "__tablename__", None) == table_name:
                return cls
        raise ValueError(f"No table class found for name {table_name}")

    # -------------------------------------------------------------------------
    def upsert_dataframe(self, df: pd.DataFrame, table_cls) -> None:
        table = table_cls.__table__
        session = self.Session()
        try:
            unique_cols = []
            for uc in table.constraints:
                if isinstance(uc, UniqueConstraint):
                    unique_cols = uc.columns.keys()
                    break
            if not unique_cols:
                raise ValueError(f"No unique constraint found for {table_cls.__name__}")
            records = df.to_dict(orient="records")
            records = [{k: (None if pd.isna(v) else v) for k, v in record.items()} for record in records]
            for i in range(0, len(records), self.insert_batch_size):
                batch = records[i : i + self.insert_batch_size]
                if not batch:
                    continue
                stmt = insert(table).values(batch)
                update_cols = {
                    col: getattr(stmt.excluded, col)  # type: ignore[attr-defined]
                    for col in batch[0]
                    if col not in unique_cols
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=unique_cols, set_=update_cols
                )
                session.execute(stmt)
                session.commit()
        finally:
            session.close()

    # -------------------------------------------------------------------------
    def load_from_database(self, table_name: str) -> pd.DataFrame:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                logger.warning("Table %s does not exist", table_name)
                return pd.DataFrame()
            data = pd.read_sql_table(table_name, conn)
        return data

    # -------------------------------------------------------------------------
    def load_filtered(
        self, table_name: str, conditions: dict[str, Any]
    ) -> pd.DataFrame:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                logger.warning("Table %s does not exist", table_name)
                return pd.DataFrame()
            if not conditions:
                return pd.read_sql_table(table_name, conn)
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            for key in conditions:
                if key not in columns:
                    logger.warning("Column %s does not exist in %s", key, table_name)
                    return pd.DataFrame()
            clauses = " AND ".join([f'"{key}" = :{key}' for key in conditions])
            query = sqlalchemy.text(f'SELECT * FROM "{table_name}" WHERE {clauses}')
            data = pd.read_sql(query, conn, params=conditions)
        return data

    # -------------------------------------------------------------------------
    def save_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        with self.engine.begin() as conn:
            inspector = inspect(conn)
            if inspector.has_table(table_name):
                conn.execute(sqlalchemy.text(f'DELETE FROM "{table_name}"'))
            df.to_sql(table_name, conn, if_exists="append", index=False)

    # -------------------------------------------------------------------------
    def clear_table(self, table_name: str) -> None:
        with self.engine.begin() as conn:
            inspector = inspect(conn)
            if inspector.has_table(table_name):
                conn.execute(sqlalchemy.text(f'DELETE FROM "{table_name}"'))

    # -------------------------------------------------------------------------
    def append_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        if df.empty:
            return
        with self.engine.begin() as conn:
            df.to_sql(table_name, conn, if_exists="append", index=False)

    # -------------------------------------------------------------------------
    def upsert_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        table_cls = self.get_table_class(table_name)
        self.upsert_dataframe(df, table_cls)

    # -------------------------------------------------------------------------
    def delete_from_database(self, table_name: str, conditions: dict[str, Any]) -> None:
        if not conditions:
            return
        with self.engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                logger.warning("Table %s does not exist", table_name)
                return
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            for key in conditions:
                if key not in columns:
                    logger.warning("Column %s does not exist in %s", key, table_name)
                    return
            clauses = " AND ".join([f'"{key}" = :{key}' for key in conditions])
            query = sqlalchemy.text(f'DELETE FROM "{table_name}" WHERE {clauses}')
            conn.execute(query, conditions)

    # -------------------------------------------------------------------------
    def count_rows(self, table_name: str) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text(f'SELECT COUNT(*) FROM "{table_name}"')
            )
            value = result.scalar() or 0
        return int(value)

    # -------------------------------------------------------------------------
    def load_paginated(self, table_name: str, offset: int, limit: int) -> pd.DataFrame:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                logger.warning("Table %s does not exist", table_name)
                return pd.DataFrame()
            query = sqlalchemy.text(
                f'SELECT * FROM "{table_name}" LIMIT :limit OFFSET :offset'
            )
            data = pd.read_sql(query, conn, params={"limit": limit, "offset": offset})
        return data

    # -------------------------------------------------------------------------
    def count_columns(self, table_name: str) -> int:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                return 0
            columns = inspector.get_columns(table_name)
        return len(columns)

    # -------------------------------------------------------------------------
    def load_distinct_values(self, table_name: str, column_name: str) -> list[str]:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                return []
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if column_name not in columns:
                return []
            query = sqlalchemy.text(
                f'SELECT DISTINCT "{column_name}" FROM "{table_name}" ORDER BY "{column_name}"'
            )
            rows = conn.execute(query).fetchall()
        values = [row[0] for row in rows if row[0] is not None]
        return [str(value) for value in values]

    # -------------------------------------------------------------------------
    def load_grouped_counts(
        self, table_name: str, column_name: str
    ) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                return []
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if column_name not in columns:
                return []
            query = sqlalchemy.text(
                f'SELECT "{column_name}" as value, COUNT(*) as row_count '
                f'FROM "{table_name}" '
                f'WHERE "{column_name}" IS NOT NULL '
                f'GROUP BY "{column_name}" '
                f'ORDER BY "{column_name}"'
            )
            rows = conn.execute(query).fetchall()
        return [
            {"value": row[0], "count": int(row[1] or 0)}
            for row in rows
            if row[0] is not None
        ]
