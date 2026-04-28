from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import UniqueConstraint, and_, delete, inspect, or_, select, tuple_
from sqlalchemy.orm import Session, sessionmaker

from FAIRS.server.common.utils.logger import logger
from FAIRS.server.repositories.database.utils import coerce_value_for_sql_column
from FAIRS.server.repositories.schemas.models import Base, get_model_class_for_table

ALLOWED_TABLE_NAMES = frozenset(Base.metadata.tables.keys())


# -----------------------------------------------------------------------------
def normalize_table_name(table_name: str) -> str:
    if not isinstance(table_name, str):
        raise ValueError("Table name must be a string.")
    candidate = table_name.strip()
    if candidate != table_name or not candidate:
        raise ValueError("Invalid table name.")
    if candidate not in ALLOWED_TABLE_NAMES:
        raise ValueError(f"Unsupported table name: {table_name}")
    return candidate


###############################################################################
class SQLAlchemyRepositoryBase:
    Session: sessionmaker[Session]
    insert_batch_size: int

    # -------------------------------------------------------------------------
    def get_table_class(self, table_name: str) -> type[Any]:
        return get_model_class_for_table(normalize_table_name(table_name))

    # -------------------------------------------------------------------------
    @staticmethod
    def normalize_record_values(table: Any, record: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in record.items():
            normalized = None if pd.isna(value) else value
            if key in table.c:
                normalized = coerce_value_for_sql_column(normalized, table.c[key].type)
            if key == "id" and normalized is None:
                continue
            sanitized[key] = normalized
        return sanitized

    # -------------------------------------------------------------------------
    @staticmethod
    def dataframe_from_models(model_cls: type[Any], rows: list[Any]) -> pd.DataFrame:
        columns = [column.name for column in model_cls.__table__.columns]
        if not rows:
            return pd.DataFrame(columns=columns)
        records = [{column: getattr(row, column) for column in columns} for row in rows]
        return pd.DataFrame.from_records(records, columns=columns)

    # -------------------------------------------------------------------------
    @staticmethod
    def build_unique_key(record: dict[str, Any], unique_cols: list[str]) -> tuple[Any, ...]:
        return tuple(record.get(column) for column in unique_cols)

    # -------------------------------------------------------------------------
    @staticmethod
    def unique_columns_for_table(table: Any, model_cls: type[Any]) -> list[str]:
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                return list(constraint.columns.keys())
        primary_keys = [column.name for column in model_cls.__table__.primary_key.columns]
        if primary_keys:
            return primary_keys
        raise ValueError(f"No unique key found for {model_cls.__name__}")

    # -------------------------------------------------------------------------
    @staticmethod
    def build_condition_expression(model_cls: type[Any], conditions: dict[str, Any]) -> Any:
        predicates = []
        table = model_cls.__table__
        for key, raw_value in conditions.items():
            normalized_value = coerce_value_for_sql_column(raw_value, table.c[key].type)
            column = getattr(model_cls, key)
            predicates.append(column.is_(None) if normalized_value is None else column == normalized_value)
        return and_(*predicates)

    # -------------------------------------------------------------------------
    def load_existing_rows(
        self,
        session: Session,
        model_cls: type[Any],
        unique_cols: list[str],
        keys: list[tuple[Any, ...]],
    ) -> dict[tuple[Any, ...], Any]:
        if not keys:
            return {}
        unique_keys = list(dict.fromkeys(keys))
        stmt: Any
        if len(unique_cols) == 1 and all(key[0] is not None for key in unique_keys):
            column_name = unique_cols[0]
            stmt = select(model_cls).where(
                getattr(model_cls, column_name).in_([key[0] for key in unique_keys])
            )
        elif len(unique_cols) > 1 and all(
            all(value is not None for value in key) for key in unique_keys
        ):
            tuple_columns = [getattr(model_cls, column_name) for column_name in unique_cols]
            stmt = select(model_cls).where(tuple_(*tuple_columns).in_(unique_keys))
        else:
            conditions = [
                self.build_condition_expression(
                    model_cls,
                    dict(zip(unique_cols, key_values, strict=True)),
                )
                for key_values in unique_keys
            ]
            stmt = select(model_cls).where(or_(*conditions))
        rows = session.execute(stmt).scalars().all()
        return {
            self.build_unique_key(
                {column_name: getattr(row, column_name) for column_name in unique_cols},
                unique_cols,
            ): row
            for row in rows
        }

    # -------------------------------------------------------------------------
    def ensure_table_exists(self, table_name: str) -> bool:
        return bool(inspect(self.engine).has_table(table_name))

    # -------------------------------------------------------------------------
    def upsert_dataframe(self, df: pd.DataFrame, model_cls: type[Any]) -> None:
        table = model_cls.__table__
        unique_cols = self.unique_columns_for_table(table, model_cls)
        records = [
            self.normalize_record_values(table, record)
            for record in df.to_dict(orient="records")
        ]
        session = self.Session()
        try:
            for start in range(0, len(records), self.insert_batch_size):
                batch = records[start : start + self.insert_batch_size]
                if not batch:
                    continue
                existing_rows = self.load_existing_rows(
                    session,
                    model_cls,
                    unique_cols,
                    [self.build_unique_key(item, unique_cols) for item in batch],
                )
                for item in batch:
                    unique_key = self.build_unique_key(item, unique_cols)
                    existing = existing_rows.get(unique_key)
                    if existing is None:
                        row = model_cls(**item)
                        session.add(row)
                        existing_rows[unique_key] = row
                        continue
                    for key, value in item.items():
                        if key not in unique_cols and key != "id":
                            setattr(existing, key, value)
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
        table_name = normalize_table_name(table_name)
        if not self.ensure_table_exists(table_name):
            logger.warning("Table %s does not exist", table_name)
            return pd.DataFrame()
        model_cls = self.get_table_class(table_name)
        stmt = select(model_cls)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        with self.Session() as session:
            rows = session.execute(stmt).scalars().all()
        return self.dataframe_from_models(model_cls, rows)

    # -------------------------------------------------------------------------
    def load_filtered(
        self,
        table_name: str,
        conditions: dict[str, Any],
    ) -> pd.DataFrame:
        table_name = normalize_table_name(table_name)
        if not self.ensure_table_exists(table_name):
            logger.warning("Table %s does not exist", table_name)
            return pd.DataFrame()
        model_cls = self.get_table_class(table_name)
        if not conditions:
            return self.load_from_database(table_name)
        columns = set(model_cls.__table__.columns.keys())
        for key in conditions:
            if key not in columns:
                logger.warning("Column %s does not exist in %s", key, table_name)
                return pd.DataFrame()
        stmt = select(model_cls).where(
            self.build_condition_expression(model_cls, conditions)
        )
        with self.Session() as session:
            rows = session.execute(stmt).scalars().all()
        return self.dataframe_from_models(model_cls, rows)

    # -------------------------------------------------------------------------
    def append_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        table_name = normalize_table_name(table_name)
        if df.empty:
            return
        model_cls = self.get_table_class(table_name)
        table = model_cls.__table__
        rows = [
            model_cls(**self.normalize_record_values(table, row))
            for row in df.to_dict(orient="records")
        ]
        session = self.Session()
        try:
            session.add_all(rows)
            session.commit()
        finally:
            session.close()

    # -------------------------------------------------------------------------
    def upsert_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        self.upsert_dataframe(df, self.get_table_class(normalize_table_name(table_name)))

    # -------------------------------------------------------------------------
    def delete_from_database(self, table_name: str, conditions: dict[str, Any]) -> None:
        table_name = normalize_table_name(table_name)
        if not conditions:
            return
        if not self.ensure_table_exists(table_name):
            logger.warning("Table %s does not exist", table_name)
            return
        model_cls = self.get_table_class(table_name)
        columns = set(model_cls.__table__.columns.keys())
        for key in conditions:
            if key not in columns:
                logger.warning("Column %s does not exist in %s", key, table_name)
                return
        stmt = delete(model_cls).where(self.build_condition_expression(model_cls, conditions))
        session = self.Session()
        try:
            session.execute(stmt)
            session.commit()
        finally:
            session.close()
