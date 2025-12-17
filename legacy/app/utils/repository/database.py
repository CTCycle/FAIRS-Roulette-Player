from __future__ import annotations

import os
from typing import Any

import pandas as pd
import sqlalchemy
from sqlalchemy import Column, Float, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import declarative_base, sessionmaker

from FAIRS.app.utils.constants import DATA_PATH, INFERENCE_PATH, SOURCE_PATH
from FAIRS.app.utils.logger import logger
from FAIRS.app.utils.singleton import singleton

Base = declarative_base()


###############################################################################
class RouletteSeries(Base):
    __tablename__ = "ROULETTE_SERIES"
    id = Column(Integer, primary_key=True)
    extraction = Column(Integer)
    color = Column(String)
    color_code = Column(Integer)
    position = Column(Integer)
    __table_args__ = (UniqueConstraint("id"),)


###############################################################################
class PredictedGames(Base):
    __tablename__ = "PREDICTED_GAMES"
    id = Column(Integer, primary_key=True)
    checkpoint = Column(String)
    extraction = Column(Integer)
    predicted_action = Column(String)
    __table_args__ = (UniqueConstraint("id"),)


###############################################################################
class CheckpointSummary(Base):
    __tablename__ = "CHECKPOINTS_SUMMARY"
    checkpoint = Column(String, primary_key=True)
    sample_size = Column(Float)
    seed = Column(Integer)
    precision = Column(Integer)
    episodes = Column(Integer)
    max_steps_episode = Column(Integer)
    batch_size = Column(Integer)
    jit_compile = Column(String)
    has_tensorboard_logs = Column(String)
    learning_rate = Column(Float)
    neurons = Column(Integer)
    embedding_dimensions = Column(Integer)
    perceptive_field_size = Column(Integer)
    exploration_rate = Column(Float)
    exploration_rate_decay = Column(Float)
    discount_rate = Column(Float)
    model_update_frequency = Column(Integer)
    loss = Column(Float)
    accuracy = Column(Float)
    __table_args__ = (UniqueConstraint("checkpoint"),)


# [DATABASE]
###############################################################################
@singleton
class FAIRSDatabase:
    def __init__(self) -> None:
        self.db_path = os.path.join(DATA_PATH, "sqlite.db")
        self.source_path = os.path.join(SOURCE_PATH, "FAIRS_dataset.csv")
        self.inference_path = os.path.join(INFERENCE_PATH, "predicted_games.csv")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}", echo=False, future=True
        )
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.insert_batch_size = 1000

    # -------------------------------------------------------------------------
    def initialize_database(self) -> None:
        if not os.path.exists(self.db_path):
            Base.metadata.create_all(self.engine)

    # -------------------------------------------------------------------------
    def get_table_class(self, table_name: str) -> Any:
        for cls in Base.__subclasses__():
            if hasattr(cls, "__tablename__") and cls.__tablename__ == table_name:
                return cls
        raise ValueError(f"No table class found for name {table_name}")

    # -------------------------------------------------------------------------
    def update_database_from_source(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        roulette_dataset = pd.read_csv(self.source_path, sep=";", encoding="utf-8")
        roulette_predictions = pd.read_csv(
            self.inference_path, sep=";", encoding="utf-8"
        )
        self.save_into_database(roulette_dataset, "ROULETTE_SERIES")
        self.save_into_database(roulette_predictions, "PREDICTED_GAMES")

        return roulette_dataset, roulette_predictions

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

            # Batch insertions for speed
            records = df.to_dict(orient="records")
            for i in range(0, len(records), self.insert_batch_size):
                batch = records[i : i + self.insert_batch_size]
                stmt = insert(table).values(batch)
                # Columns to update on conflict
                update_cols = {
                    c: getattr(stmt.excluded, c)  # type: ignore
                    for c in batch[0]
                    if c not in unique_cols
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=unique_cols, set_=update_cols
                )
                session.execute(stmt)
                session.commit()
            session.commit()
        finally:
            session.close()

    # -------------------------------------------------------------------------
    def load_from_database(self, table_name: str) -> pd.DataFrame:
        with self.engine.connect() as conn:
            data = pd.read_sql_table(table_name, conn)

        return data

    # -------------------------------------------------------------------------
    def save_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(sqlalchemy.text(f'DELETE FROM "{table_name}"'))
            df.to_sql(table_name, conn, if_exists="append", index=False)

    # -------------------------------------------------------------------------
    def upsert_into_database(self, df: pd.DataFrame, table_name: str) -> None:
        table_cls = self.get_table_class(table_name)
        self.upsert_dataframe(df, table_cls)

    # -------------------------------------------------------------------------
    def export_all_tables_as_csv(
        self, export_dir: str, chunksize: int | None = None
    ) -> None:
        os.makedirs(export_dir, exist_ok=True)
        with self.engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                table_name = table.name
                csv_path = os.path.join(export_dir, f"{table_name}.csv")

                # Build a safe SELECT for arbitrary table names (quote with "")
                query = sqlalchemy.text(f'SELECT * FROM "{table_name}"')

                if chunksize:
                    first = True
                    for chunk in pd.read_sql(query, conn, chunksize=chunksize):
                        chunk.to_csv(
                            csv_path,
                            index=False,
                            header=first,
                            mode="w" if first else "a",
                            encoding="utf-8",
                            sep=",",
                        )
                        first = False
                    # If no chunks were returned, still write the header row
                    if first:
                        pd.DataFrame(columns=[c.name for c in table.columns]).to_csv(
                            csv_path, index=False, encoding="utf-8", sep=","
                        )
                else:
                    df = pd.read_sql(query, conn)
                    if df.empty:
                        pd.DataFrame(columns=[c.name for c in table.columns]).to_csv(
                            csv_path, index=False, encoding="utf-8", sep=","
                        )
                    else:
                        df.to_csv(csv_path, index=False, encoding="utf-8", sep=",")

        logger.info(f"All tables exported to CSV at {os.path.abspath(export_dir)}")

    # -------------------------------------------------------------------------
    def delete_all_data(self) -> None:
        with self.engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


# -----------------------------------------------------------------------------
database = FAIRSDatabase()
