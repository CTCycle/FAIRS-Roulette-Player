from __future__ import annotations

from datetime import datetime, timezone
from numbers import Integral
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select

from server.repositories.database.backend import FAIRSDatabase
from server.repositories.schemas.models import DatasetOutcomes, Datasets

MAX_DATASET_NAME_LENGTH = 128


###############################################################################
def normalize_dataset_name(value: str) -> str:
    name = value.strip()
    if (
        not name
        or len(name) > MAX_DATASET_NAME_LENGTH
        or any(ord(char) < 32 for char in name)
    ):
        raise ValueError("Invalid dataset name.")
    return name


###############################################################################
class DatasetRepository:
    # -------------------------------------------------------------------------
    def __init__(self, database: FAIRSDatabase) -> None:
        self.database = database

    # -------------------------------------------------------------------------
    @staticmethod
    def _key(name: str) -> str:
        return name.casefold()

    # -------------------------------------------------------------------------
    @staticmethod
    def require_dataset_id(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1:
            raise ValueError(f"Invalid dataset_id: {value}")
        return int(value)

    # -------------------------------------------------------------------------
    @staticmethod
    def _row(dataset: Datasets, row_count: int | None = None) -> dict[str, Any]:
        result = {
            "dataset_id": dataset.dataset_id,
            "dataset_name": dataset.dataset_name,
            "dataset_kind": dataset.dataset_kind,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
        }
        if row_count is not None:
            result["row_count"] = row_count
        return result

    # -------------------------------------------------------------------------
    def get(self, dataset_id: int) -> dict[str, Any] | None:
        with self.database.Session() as session:
            dataset = session.get(Datasets, dataset_id)
            return None if dataset is None else self._row(dataset)

    # -------------------------------------------------------------------------
    def list(
        self,
        dataset_kind: str | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self.database.Session() as session:
            stmt = select(Datasets)
            if dataset_kind:
                stmt = stmt.where(Datasets.dataset_kind == dataset_kind.strip().lower())
            stmt = stmt.order_by(
                Datasets.dataset_kind, Datasets.dataset_name_key, Datasets.dataset_id
            ).offset(max(offset, 0))
            if limit is not None:
                stmt = stmt.limit(max(limit, 0))
            return [self._row(dataset) for dataset in session.scalars(stmt)]

    # -------------------------------------------------------------------------
    def summaries(self, dataset_kind: str | None = None) -> list[dict[str, Any]]:
        with self.database.Session() as session:
            count = (
                select(func.count(DatasetOutcomes.sequence_index))
                .where(DatasetOutcomes.dataset_id == Datasets.dataset_id)
                .scalar_subquery()
            )
            stmt = select(Datasets, count.label("row_count"))
            if dataset_kind:
                stmt = stmt.where(Datasets.dataset_kind == dataset_kind.strip().lower())
            stmt = stmt.order_by(
                Datasets.dataset_kind, Datasets.dataset_name_key, Datasets.dataset_id
            )
            return [
                self._row(dataset, int(row_count))
                for dataset, row_count in session.execute(stmt)
            ]

    # -------------------------------------------------------------------------
    def import_replacement(
        self, dataset_name: str, dataset_kind: str, outcomes: pd.DataFrame
    ) -> dict[str, Any]:
        clean_name = normalize_dataset_name(dataset_name)
        clean_kind = dataset_kind.strip().lower()
        if clean_kind not in {"training", "inference"}:
            raise ValueError(f"Unsupported dataset kind: {dataset_kind}")
        records = (
            outcomes[["sequence_index", "outcome_id"]]
            .astype(int)
            .to_dict(orient="records")
            if not outcomes.empty
            else []
        )
        now = datetime.now(timezone.utc)
        with self.database.transaction() as session:
            dataset = session.scalar(
                select(Datasets)
                .where(
                    Datasets.dataset_kind == clean_kind,
                    Datasets.dataset_name_key == self._key(clean_name),
                )
                .with_for_update()
            )
            if dataset is None:
                dataset = Datasets(
                    dataset_name=clean_name,
                    dataset_name_key=self._key(clean_name),
                    dataset_kind=clean_kind,
                    created_at=now,
                    updated_at=now,
                )
                session.add(dataset)
                session.flush()
            else:
                dataset.dataset_name = clean_name
                dataset.updated_at = now
            session.execute(
                delete(DatasetOutcomes).where(
                    DatasetOutcomes.dataset_id == dataset.dataset_id
                )
            )
            for start in range(0, len(records), self.database.insert_batch_size):
                session.execute(
                    DatasetOutcomes.__table__.insert(),
                    [
                        {"dataset_id": dataset.dataset_id, **row}
                        for row in records[
                            start : start + self.database.insert_batch_size
                        ]
                    ],
                )
            return {
                "dataset_id": dataset.dataset_id,
                "dataset_name": dataset.dataset_name,
                "dataset_kind": dataset.dataset_kind,
                "rows_imported": len(records),
            }

    # -------------------------------------------------------------------------
    def outcomes(self, dataset_id: int) -> pd.DataFrame:
        dataset_id = self.require_dataset_id(dataset_id)
        with self.database.Session() as session:
            rows = (
                session.execute(
                    select(
                        DatasetOutcomes.dataset_id,
                        DatasetOutcomes.sequence_index,
                        DatasetOutcomes.outcome_id,
                    )
                    .where(DatasetOutcomes.dataset_id == dataset_id)
                    .order_by(DatasetOutcomes.sequence_index)
                )
                .mappings()
                .all()
            )
        frame = pd.DataFrame(
            rows, columns=["dataset_id", "sequence_index", "outcome_id"]
        )
        if not frame.empty:
            frame["outcome"] = frame["outcome_id"]
        return frame

    # -------------------------------------------------------------------------
    def training_outcomes(self, dataset_id: int | None = None) -> pd.DataFrame:
        if dataset_id is not None:
            dataset_id = self.require_dataset_id(dataset_id)
        with self.database.Session() as session:
            stmt = (
                select(
                    DatasetOutcomes.dataset_id,
                    DatasetOutcomes.sequence_index,
                    DatasetOutcomes.outcome_id,
                )
                .join(Datasets, Datasets.dataset_id == DatasetOutcomes.dataset_id)
                .where(Datasets.dataset_kind == "training")
                .order_by(
                    DatasetOutcomes.dataset_id,
                    DatasetOutcomes.sequence_index,
                )
            )
            if dataset_id is not None:
                stmt = stmt.where(DatasetOutcomes.dataset_id == dataset_id)
            rows = session.execute(stmt).mappings().all()
        frame = pd.DataFrame(
            rows,
            columns=["dataset_id", "sequence_index", "outcome_id"],
        )
        if not frame.empty:
            frame["outcome"] = frame["outcome_id"]
        return frame

    # -------------------------------------------------------------------------
    def delete(self, dataset_id: int) -> None:
        with self.database.transaction() as session:
            session.execute(delete(Datasets).where(Datasets.dataset_id == dataset_id))

    # -------------------------------------------------------------------------
    def clear(self, dataset_kind: str | None = None) -> None:
        with self.database.transaction() as session:
            stmt = delete(Datasets)
            if dataset_kind:
                stmt = stmt.where(Datasets.dataset_kind == dataset_kind.strip().lower())
            session.execute(stmt)
