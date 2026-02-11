from __future__ import annotations

import os
from typing import Any

import pandas as pd
import sqlalchemy
from sqlalchemy import UniqueConstraint, and_, event, inspect
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from FAIRS.server.configurations import DatabaseSettings
from FAIRS.server.common.constants import RESOURCES_PATH, DATABASE_FILENAME
from FAIRS.server.common.utils.logger import logger
from FAIRS.server.repositories.schemas.models import Base


# [SQLITE DATABASE]
###############################################################################
class SQLiteRepository:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.db_path: str | None = os.path.join(RESOURCES_PATH, DATABASE_FILENAME)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.engine: Engine = sqlalchemy.create_engine(
            f"sqlite:///{self.db_path}", echo=False, future=True
        )
        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.insert_batch_size = settings.insert_batch_size
        Base.metadata.create_all(self.engine)

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
                unique_cols = list(table.primary_key.columns.keys())
            if not unique_cols:
                raise ValueError(f"No unique key found for {table_cls.__name__}")
            records = []
            for record in df.to_dict(orient="records"):
                sanitized: dict[str, Any] = {}
                for key, value in record.items():
                    normalized = None if pd.isna(value) else value
                    if key == "id" and normalized is None:
                        continue
                    sanitized[key] = normalized
                records.append(sanitized)
            for i in range(0, len(records), self.insert_batch_size):
                batch = records[i : i + self.insert_batch_size]
                if not batch:
                    continue
                has_generated_pk = "id" in table.c and all(
                    item.get("id") is None for item in batch
                )
                if has_generated_pk:
                    for item in batch:
                        match_values = {col: item.get(col) for col in unique_cols}
                        update_values = {
                            col: value
                            for col, value in item.items()
                            if col not in unique_cols and col != "id"
                        }
                        where_clause = and_(
                            *[table.c[col] == match_values[col] for col in unique_cols]
                        )
                        if update_values:
                            result = session.execute(
                                sqlalchemy.update(table)
                                .where(where_clause)
                                .values(**update_values)
                            )
                            if result.rowcount and result.rowcount > 0:
                                continue
                        session.execute(insert(table).values(item))
                    session.commit()
                    continue

                stmt = insert(table).values(batch)
                batch_columns = {
                    key for item in batch for key in item.keys()
                }
                update_cols = {
                    col: getattr(stmt.excluded, col)  # type: ignore[attr-defined]
                    for col in batch_columns
                    if col not in unique_cols and col != "id"
                }
                if update_cols:
                    stmt = stmt.on_conflict_do_update(
                        index_elements=unique_cols, set_=update_cols
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing(index_elements=unique_cols)
                session.execute(stmt)
                session.commit()
        finally:
            session.close()

    # -------------------------------------------------------------------------
    def load_from_database(
        self,
        table_name: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> pd.DataFrame:
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            if not inspector.has_table(table_name):
                logger.warning("Table %s does not exist", table_name)
                return pd.DataFrame()
            if limit is None and offset is None:
                data = pd.read_sql_table(table_name, conn)
            else:
                query = f'SELECT * FROM "{table_name}"'
                query_limit = limit if limit is not None else 9223372036854775807
                query_offset = offset if offset is not None else 0
                query += " LIMIT :limit OFFSET :offset"
                data = pd.read_sql(
                    sqlalchemy.text(query),
                    conn,
                    params={"limit": query_limit, "offset": query_offset},
                )
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

