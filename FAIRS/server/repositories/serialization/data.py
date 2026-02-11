from __future__ import annotations

from datetime import datetime
from typing import Any, cast
import uuid

import pandas as pd

from FAIRS.server.common.constants import (
    DATASETS_COLUMNS,
    DATASETS_TABLE,
    DATASET_OUTCOMES_COLUMNS,
    DATASET_OUTCOMES_TABLE,
    DATASET_OUTCOMES_WRITE_COLUMNS,
    INFERENCE_SESSIONS_COLUMNS,
    INFERENCE_SESSIONS_TABLE,
    INFERENCE_SESSION_STEPS_COLUMNS,
    INFERENCE_SESSION_STEPS_TABLE,
)
from FAIRS.server.repositories.queries.data import DataRepositoryQueries


###############################################################################
class DataSerializer:
    def __init__(self, queries: DataRepositoryQueries | None = None) -> None:
        self.queries = queries or DataRepositoryQueries()

    # -------------------------------------------------------------------------
    def ensure_dataset(self, dataset_name: str, dataset_kind: str) -> str:
        clean_name = dataset_name.strip()
        clean_kind = dataset_kind.strip().lower()
        if not clean_name:
            raise ValueError("Dataset name cannot be empty.")
        if clean_kind not in {"training", "inference"}:
            raise ValueError(f"Unsupported dataset kind: {dataset_kind}")

        existing = self.queries.load_filtered_table(
            DATASETS_TABLE,
            {
                "dataset_name": clean_name,
                "dataset_kind": clean_kind,
            },
        )
        if not existing.empty and "dataset_id" in existing.columns:
            resolved = existing.iloc[0]["dataset_id"]
            if isinstance(resolved, str) and resolved:
                return resolved

        dataset_id = uuid.uuid4().hex
        frame = pd.DataFrame(
            [
                {
                    "dataset_id": dataset_id,
                    "dataset_name": clean_name,
                    "dataset_kind": clean_kind,
                    "created_at": datetime.now(),
                }
            ]
        ).reindex(columns=DATASETS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, DATASETS_TABLE)
        return dataset_id

    # -------------------------------------------------------------------------
    def load_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        frame = self.queries.load_filtered_table(
            DATASETS_TABLE,
            {"dataset_id": dataset_id},
        )
        if frame.empty:
            return None
        row = frame.iloc[0].to_dict()
        return {str(key): value for key, value in row.items()}

    # -------------------------------------------------------------------------
    def list_datasets(self, dataset_kind: str | None = None) -> list[dict[str, Any]]:
        if dataset_kind:
            frame = self.queries.load_filtered_table(
                DATASETS_TABLE,
                {"dataset_kind": dataset_kind},
            )
        else:
            frame = self.queries.load_table(DATASETS_TABLE)
        if frame.empty:
            return []
        sort_columns = [
            column
            for column in ("dataset_kind", "dataset_name", "created_at")
            if column in frame.columns
        ]
        if sort_columns:
            frame = frame.sort_values(sort_columns)
        return frame.to_dict(orient="records")

    # -------------------------------------------------------------------------
    def list_datasets_summary(
        self,
        dataset_kind: str | None = None,
    ) -> list[dict[str, Any]]:
        datasets = self.list_datasets(dataset_kind)
        if not datasets:
            return []
        outcomes = self.queries.load_table(DATASET_OUTCOMES_TABLE)
        counts: dict[str, int] = {}
        if not outcomes.empty and "dataset_id" in outcomes.columns:
            grouped = outcomes.groupby("dataset_id").size()
            counts = {str(key): int(value) for key, value in grouped.items()}

        summaries: list[dict[str, Any]] = []
        for row in datasets:
            dataset_id = str(row.get("dataset_id", ""))
            if not dataset_id:
                continue
            summaries.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_name": str(row.get("dataset_name", "")),
                    "dataset_kind": str(row.get("dataset_kind", "")),
                    "created_at": row.get("created_at"),
                    "row_count": counts.get(dataset_id, 0),
                }
            )
        return summaries

    # -------------------------------------------------------------------------
    def replace_dataset_outcomes(self, dataset_id: str, outcomes: pd.DataFrame) -> int:
        self.queries.delete_table_rows(DATASET_OUTCOMES_TABLE, {"dataset_id": dataset_id})
        if outcomes.empty:
            return 0

        frame = outcomes.copy()
        frame["dataset_id"] = dataset_id
        frame = frame.reindex(columns=DATASET_OUTCOMES_WRITE_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.append_table(frame, DATASET_OUTCOMES_TABLE)
        return int(len(frame))

    # -------------------------------------------------------------------------
    def import_dataset(
        self,
        dataset_name: str,
        dataset_kind: str,
        outcomes: pd.DataFrame,
    ) -> dict[str, Any]:
        dataset_id = self.ensure_dataset(dataset_name, dataset_kind)
        rows_imported = self.replace_dataset_outcomes(dataset_id, outcomes)
        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name.strip(),
            "dataset_kind": dataset_kind.strip().lower(),
            "rows_imported": rows_imported,
        }

    # -------------------------------------------------------------------------
    def load_dataset_outcomes(self, dataset_id: str) -> pd.DataFrame:
        frame = self.queries.load_filtered_table(
            DATASET_OUTCOMES_TABLE,
            {"dataset_id": dataset_id},
        )
        if frame.empty:
            return frame
        if "sequence_index" in frame.columns:
            frame = frame.sort_values("sequence_index")
        if "outcome_id" in frame.columns and "outcome" not in frame.columns:
            frame = frame.assign(outcome=frame["outcome_id"])
        return frame

    # -------------------------------------------------------------------------
    def load_training_outcomes(self, dataset_id: str | None = None) -> pd.DataFrame:
        if dataset_id:
            return self.load_dataset_outcomes(dataset_id)

        training = self.list_datasets(dataset_kind="training")
        if not training:
            return pd.DataFrame(columns=DATASET_OUTCOMES_COLUMNS)
        dataset_ids = {str(row.get("dataset_id", "")) for row in training}
        dataset_ids = {value for value in dataset_ids if value}
        if not dataset_ids:
            return pd.DataFrame(columns=DATASET_OUTCOMES_COLUMNS)

        frame = self.queries.load_table(DATASET_OUTCOMES_TABLE)
        if frame.empty:
            return frame
        if "dataset_id" not in frame.columns:
            return pd.DataFrame(columns=DATASET_OUTCOMES_COLUMNS)
        filtered = frame.loc[frame["dataset_id"].astype(str).isin(dataset_ids)].copy()
        if filtered.empty:
            return filtered
        sort_columns = [
            column for column in ("dataset_id", "sequence_index") if column in filtered.columns
        ]
        if sort_columns:
            filtered = filtered.sort_values(sort_columns)
        if "outcome_id" in filtered.columns and "outcome" not in filtered.columns:
            filtered = filtered.assign(outcome=filtered["outcome_id"])
        return filtered

    # -------------------------------------------------------------------------
    def delete_dataset(self, dataset_id: str) -> None:
        self.queries.delete_table_rows(DATASETS_TABLE, {"dataset_id": dataset_id})

    # -------------------------------------------------------------------------
    def clear_datasets(self, dataset_kind: str | None = None) -> None:
        if not dataset_kind:
            self.queries.clear_table(DATASET_OUTCOMES_TABLE)
            self.queries.clear_table(DATASETS_TABLE)
            return
        for row in self.list_datasets(dataset_kind=dataset_kind):
            dataset_id = str(row.get("dataset_id", ""))
            if dataset_id:
                self.delete_dataset(dataset_id)

    # -------------------------------------------------------------------------
    def upsert_inference_session(self, row: dict[str, Any]) -> None:
        frame = pd.DataFrame([row]).reindex(columns=INFERENCE_SESSIONS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, INFERENCE_SESSIONS_TABLE)

    # -------------------------------------------------------------------------
    def mark_inference_session_ended(self, session_id: str) -> None:
        session = self.queries.load_filtered_table(
            INFERENCE_SESSIONS_TABLE,
            {"session_id": session_id},
        )
        if session.empty:
            return
        row = session.iloc[0].to_dict()
        row["ended_at"] = datetime.now()
        self.upsert_inference_session({str(key): value for key, value in row.items()})

    # -------------------------------------------------------------------------
    def upsert_inference_session_step(self, row: dict[str, Any]) -> None:
        frame = pd.DataFrame([row]).reindex(columns=INFERENCE_SESSION_STEPS_COLUMNS)
        frame = frame.where(pd.notnull(frame), cast(Any, None))
        self.queries.upsert_table(frame, INFERENCE_SESSION_STEPS_TABLE)

    # -------------------------------------------------------------------------
    def delete_inference_session(self, session_id: str) -> None:
        self.queries.delete_table_rows(
            INFERENCE_SESSIONS_TABLE,
            {"session_id": session_id},
        )
