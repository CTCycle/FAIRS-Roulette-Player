from __future__ import annotations

from numbers import Integral
from typing import Any

import pandas as pd

from server.repositories.datasets import DatasetRepository
from server.repositories.inference import InferenceRepository


###############################################################################
class DataSerializer:
    """Converts repository results to the dictionaries and frames used by services."""

    # -------------------------------------------------------------------------
    def __init__(self, datasets: DatasetRepository, inference: InferenceRepository) -> None:
        self.datasets = datasets
        self.inference = inference

    # -------------------------------------------------------------------------
    @staticmethod
    def require_dataset_id(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1:
            raise ValueError(f"Invalid dataset_id: {value}")
        return int(value)

    # -------------------------------------------------------------------------
    def load_dataset(self, dataset_id: int) -> dict[str, Any] | None:
        try:
            return self.datasets.get(self.require_dataset_id(dataset_id))
        except ValueError:
            return None

    # -------------------------------------------------------------------------
    def list_datasets(self, dataset_kind: str | None = None) -> list[dict[str, Any]]:
        return self.datasets.list(dataset_kind)

    # -------------------------------------------------------------------------
    def list_datasets_summary(self, dataset_kind: str | None = None) -> list[dict[str, Any]]:
        return self.datasets.summaries(dataset_kind)

    # -------------------------------------------------------------------------
    def import_dataset(self, dataset_name: str, dataset_kind: str, outcomes: pd.DataFrame) -> dict[str, Any]:
        return self.datasets.import_replacement(dataset_name, dataset_kind, outcomes)

    # -------------------------------------------------------------------------
    def load_dataset_outcomes(self, dataset_id: int) -> pd.DataFrame:
        return self.datasets.outcomes(self.require_dataset_id(dataset_id))

    # -------------------------------------------------------------------------
    def load_training_outcomes(self, dataset_id: int | None = None) -> pd.DataFrame:
        return self.load_dataset_outcomes(dataset_id) if dataset_id is not None else pd.DataFrame()

    # -------------------------------------------------------------------------
    def delete_dataset(self, dataset_id: int) -> None:
        self.datasets.delete(self.require_dataset_id(dataset_id))

    # -------------------------------------------------------------------------
    def clear_datasets(self, dataset_kind: str | None = None) -> None:
        self.datasets.clear(dataset_kind)

    # -------------------------------------------------------------------------
    def upsert_inference_session(self, row: dict[str, Any]) -> None:
        self.inference.upsert_session(row)

    # -------------------------------------------------------------------------
    def mark_inference_session_ended(self, session_id: str) -> None:
        self.inference.end_session(session_id)

    # -------------------------------------------------------------------------
    def upsert_inference_session_step(self, row: dict[str, Any]) -> None:
        self.inference.upsert_step(row)

    # -------------------------------------------------------------------------
    def clear_inference_session_steps(self, session_id: str) -> None:
        self.inference.clear_steps(session_id)

    # -------------------------------------------------------------------------
    def delete_inference_session(self, session_id: str) -> None:
        self.inference.delete_session(session_id)
