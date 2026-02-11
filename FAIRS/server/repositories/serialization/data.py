from __future__ import annotations

from datetime import datetime
from typing import Any, cast

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
    @staticmethod
    def normalize_dataset_id(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value > 0 else None
        if isinstance(value, float):
            if not value.is_integer():
                return None
            candidate = int(value)
            return candidate if candidate > 0 else None
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate.isdigit():
                return None
            resolved = int(candidate)
            return resolved if resolved > 0 else None
        return None

    # -------------------------------------------------------------------------
    def to_storage_dataset_id(self, dataset_id: int | str) -> str:
        resolved = self.normalize_dataset_id(dataset_id)
        if resolved is None:
            raise ValueError(f"Invalid dataset_id: {dataset_id}")
        return str(resolved)

    # -------------------------------------------------------------------------
    def next_dataset_id(self) -> int:
        frame = self.queries.load_table(DATASETS_TABLE)
        if frame.empty or "dataset_id" not in frame.columns:
            return 1
        values = [
            self.normalize_dataset_id(value)
            for value in frame["dataset_id"].tolist()
        ]
        numeric_ids = [value for value in values if value is not None]
        if not numeric_ids:
            return 1
        return max(numeric_ids) + 1

    # -------------------------------------------------------------------------
    def ensure_dataset(self, dataset_name: str, dataset_kind: str) -> int:
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
        legacy_dataset_ids: list[str] = []
        if not existing.empty and "dataset_id" in existing.columns:
            for resolved in existing["dataset_id"].tolist():
                normalized = self.normalize_dataset_id(resolved)
                if normalized is not None:
                    return normalized
                legacy_id = str(resolved).strip()
                if legacy_id:
                    legacy_dataset_ids.append(legacy_id)

        for legacy_dataset_id in legacy_dataset_ids:
            self.queries.delete_table_rows(
                INFERENCE_SESSIONS_TABLE,
                {"dataset_id": legacy_dataset_id},
            )
            self.queries.delete_table_rows(
                DATASETS_TABLE,
                {"dataset_id": legacy_dataset_id},
            )

        dataset_id = self.next_dataset_id()
        frame = pd.DataFrame(
            [
                {
                    "dataset_id": str(dataset_id),
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
    def load_dataset(self, dataset_id: int | str) -> dict[str, Any] | None:
        try:
            storage_dataset_id = self.to_storage_dataset_id(dataset_id)
        except ValueError:
            return None
        frame = self.queries.load_filtered_table(
            DATASETS_TABLE,
            {"dataset_id": storage_dataset_id},
        )
        if frame.empty:
            return None
        row = frame.iloc[0].to_dict()
        normalized_dataset_id = self.normalize_dataset_id(row.get("dataset_id"))
        if normalized_dataset_id is None:
            return None
        row["dataset_id"] = normalized_dataset_id
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
        rows = frame.to_dict(orient="records")
        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            normalized_dataset_id = self.normalize_dataset_id(row.get("dataset_id"))
            if normalized_dataset_id is None:
                continue
            normalized_row = {str(key): value for key, value in row.items()}
            normalized_row["dataset_id"] = normalized_dataset_id
            normalized_rows.append(normalized_row)
        return normalized_rows

    # -------------------------------------------------------------------------
    def list_datasets_summary(
        self,
        dataset_kind: str | None = None,
    ) -> list[dict[str, Any]]:
        datasets = self.list_datasets(dataset_kind)
        if not datasets:
            return []
        outcomes = self.queries.load_table(DATASET_OUTCOMES_TABLE)
        counts: dict[int, int] = {}
        if not outcomes.empty and "dataset_id" in outcomes.columns:
            normalized_ids = outcomes["dataset_id"].apply(self.normalize_dataset_id)
            valid = outcomes.loc[normalized_ids.notna()].copy()
            if not valid.empty:
                valid["dataset_id"] = normalized_ids.loc[normalized_ids.notna()].astype(int)
                grouped = valid.groupby("dataset_id").size()
                counts = {int(key): int(value) for key, value in grouped.items()}

        summaries: list[dict[str, Any]] = []
        for row in datasets:
            dataset_id = self.normalize_dataset_id(row.get("dataset_id"))
            if dataset_id is None:
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
    def replace_dataset_outcomes(self, dataset_id: int | str, outcomes: pd.DataFrame) -> int:
        storage_dataset_id = self.to_storage_dataset_id(dataset_id)
        self.queries.delete_table_rows(
            DATASET_OUTCOMES_TABLE,
            {"dataset_id": storage_dataset_id},
        )
        if outcomes.empty:
            return 0

        frame = outcomes.copy()
        frame["dataset_id"] = storage_dataset_id
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
    def load_dataset_outcomes(self, dataset_id: int | str) -> pd.DataFrame:
        storage_dataset_id = self.to_storage_dataset_id(dataset_id)
        frame = self.queries.load_filtered_table(
            DATASET_OUTCOMES_TABLE,
            {"dataset_id": storage_dataset_id},
        )
        if frame.empty:
            return frame
        if "sequence_index" in frame.columns:
            frame = frame.sort_values("sequence_index")
        if "outcome_id" in frame.columns and "outcome" not in frame.columns:
            frame = frame.assign(outcome=frame["outcome_id"])
        return frame

    # -------------------------------------------------------------------------
    def load_training_outcomes(self, dataset_id: int | None = None) -> pd.DataFrame:
        if dataset_id:
            return self.load_dataset_outcomes(dataset_id)

        training = self.list_datasets(dataset_kind="training")
        if not training:
            return pd.DataFrame(columns=DATASET_OUTCOMES_COLUMNS)
        dataset_ids = {
            dataset_id_value
            for dataset_id_value in (
                self.normalize_dataset_id(row.get("dataset_id"))
                for row in training
            )
            if dataset_id_value is not None
        }
        if not dataset_ids:
            return pd.DataFrame(columns=DATASET_OUTCOMES_COLUMNS)

        frame = self.queries.load_table(DATASET_OUTCOMES_TABLE)
        if frame.empty:
            return frame
        if "dataset_id" not in frame.columns:
            return pd.DataFrame(columns=DATASET_OUTCOMES_COLUMNS)
        normalized_ids = frame["dataset_id"].apply(self.normalize_dataset_id)
        filtered = frame.loc[normalized_ids.isin(dataset_ids)].copy()
        if filtered.empty:
            return filtered
        filtered["dataset_id"] = normalized_ids.loc[normalized_ids.isin(dataset_ids)].astype(int)
        sort_columns = [
            column for column in ("dataset_id", "sequence_index") if column in filtered.columns
        ]
        if sort_columns:
            filtered = filtered.sort_values(sort_columns)
        if "outcome_id" in filtered.columns and "outcome" not in filtered.columns:
            filtered = filtered.assign(outcome=filtered["outcome_id"])
        return filtered

    # -------------------------------------------------------------------------
    def delete_dataset(self, dataset_id: int | str) -> None:
        storage_dataset_id = self.to_storage_dataset_id(dataset_id)
        self.queries.delete_table_rows(DATASETS_TABLE, {"dataset_id": storage_dataset_id})

    # -------------------------------------------------------------------------
    def clear_datasets(self, dataset_kind: str | None = None) -> None:
        if not dataset_kind:
            self.queries.clear_table(DATASET_OUTCOMES_TABLE)
            self.queries.clear_table(DATASETS_TABLE)
            return
        for row in self.list_datasets(dataset_kind=dataset_kind):
            dataset_id = self.normalize_dataset_id(row.get("dataset_id"))
            if dataset_id is not None:
                self.delete_dataset(dataset_id)

    # -------------------------------------------------------------------------
    def upsert_inference_session(self, row: dict[str, Any]) -> None:
        resolved_row = {**row}
        dataset_id = resolved_row.get("dataset_id")
        if dataset_id is not None:
            normalized_dataset_id = self.normalize_dataset_id(dataset_id)
            if normalized_dataset_id is not None:
                resolved_row["dataset_id"] = str(normalized_dataset_id)
            else:
                resolved_row["dataset_id"] = str(dataset_id)
        frame = pd.DataFrame([resolved_row]).reindex(columns=INFERENCE_SESSIONS_COLUMNS)
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
