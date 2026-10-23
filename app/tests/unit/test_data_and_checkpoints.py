# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import pandas as pd
import pytest
import os
from unittest.mock import Mock
from server.contracts.upload import UploadRequest
from server.services.checkpoints import CheckpointReferenceError, CheckpointService
from server.services.datasets import DatasetService, normalize_csv_separator, normalize_filename, normalize_sheet_name
from pathlib import Path
from server.common import checkpoints as checkpoint_common
from server.repositories.checkpoints import CheckpointRepository
from server.common.checkpoints import normalize_checkpoint_identifier, resolve_checkpoint_path
from server.common.path import CHECKPOINT_PATH
from server.repositories.datasets import normalize_dataset_name

###############################################################################
def build_dataset_service() -> tuple[DatasetService, Mock, Mock, Mock]:
    dataset_repository = Mock()
    importer = Mock()
    loader = Mock()
    service = DatasetService(
        dataset_repository=dataset_repository,
        importer=importer,
        loader=loader,
    )
    return service, dataset_repository, importer, loader

###############################################################################
def test_import_upload_normalizes_filename_separator_and_sheet_name() -> None:
    service, _, importer, loader = build_dataset_service()
    loader.load_bytes.return_value = pd.DataFrame({"idx": [0], "outcome": [1]})
    importer.import_dataframe.return_value = {
        "rows_imported": 1,
        "dataset_id": 10,
        "dataset_name": "sample",
        "dataset_kind": "training",
    }

    response = service.import_upload(
        content=b"idx,outcome\n0,1\n",
        filename=r"..\sample.csv",
        request=UploadRequest(dataset_kind="training", csv_separator=",", sheet_name=0),
    )

    assert response.filename == "sample.csv"
    assert response.rows_imported == 1
    loader.load_bytes.assert_called_once()
    importer.import_dataframe.assert_called_once()

###############################################################################
def test_import_upload_rejects_oversized_payload() -> None:
    service, _, _, _ = build_dataset_service()
    with pytest.raises(ValueError, match="too large"):
        service.import_upload(
            content=b"x" * (25 * 1024 * 1024 + 1),
            filename="big.csv",
            request=UploadRequest(dataset_kind="training"),
        )

###############################################################################
def test_dataset_list_and_delete_delegate_to_repository() -> None:
    service, dataset_repository, _, _ = build_dataset_service()
    dataset_repository.list.return_value = [
        {
            "dataset_id": 1,
            "dataset_name": "a",
            "dataset_kind": "training",
            "created_at": None,
        }
    ]
    dataset_repository.summaries.return_value = [
        {
            "dataset_id": 1,
            "dataset_name": "a",
            "dataset_kind": "training",
            "created_at": None,
            "row_count": 5,
        }
    ]

    list_response = service.list_training_datasets()
    summary_response = service.list_training_dataset_summaries()
    delete_response = service.delete_training_dataset(1)

    assert len(list_response.datasets) == 1
    assert len(summary_response.datasets) == 1
    assert delete_response.status == "deleted"
    dataset_repository.delete.assert_called_once_with(1)

###############################################################################
def test_dataset_delete_blocks_checkpoint_references() -> None:
    service, dataset_repository, _, _ = build_dataset_service()
    checkpoint_service = Mock()
    checkpoint_service.find_dataset_references.return_value = ["FAIRS_20260820"]
    service.checkpoint_service = checkpoint_service

    with pytest.raises(CheckpointReferenceError, match="referenced"):
        service.delete_training_dataset(1)

    dataset_repository.delete.assert_not_called()

###############################################################################
class DummyCheckpointRepository:

    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self._checkpoints = ["cp1"]
        self.deleted_paths: list[str] = []

    # -------------------------------------------------------------------------
    def scan_checkpoints_folder(self) -> list[str]:
        return list(self._checkpoints)

    # -------------------------------------------------------------------------
    def load_training_configuration(self, path: str) -> tuple[dict, dict]:  # noqa: ARG002
        return (
            {
                "dataset_id": 7,
                "sample_size": 1.0,
                "seed": 42,
                "episodes": 3,
                "batch_size": 8,
                "learning_rate": 0.0001,
                "perceptive_field_size": 64,
                "qnet_neurons": 16,
                "embedding_dimensions": 200,
                "exploration_rate": 0.75,
                "exploration_rate_decay": 0.995,
                "discount_rate": 0.5,
                "model_update_frequency": 10,
                "bet_amount": 10,
                "initial_capital": 1000,
            },
            {
                "total_episodes": 3,
                "history": {
                    "loss": [0.2],
                    "metrics": [0.3],
                    "val_loss": [0.4, None],
                    "val_rmse": [0.5, None],
                },
            },
        )

    # -------------------------------------------------------------------------
    def delete_checkpoint(self, path: str) -> None:
        self.deleted_paths.append(path)

###############################################################################
class InvalidCheckpointRepository(DummyCheckpointRepository):

    # -------------------------------------------------------------------------
    def load_training_configuration(self, path: str) -> tuple[list, dict]:  # noqa: ARG002
        return [], {}

###############################################################################
def test_resolve_existing_checkpoint_rejects_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    service = CheckpointService(checkpoint_repository=DummyCheckpointRepository())
    with pytest.raises(FileNotFoundError):
        service.resolve_existing_checkpoint("missing")

###############################################################################
def test_get_metadata_returns_summary_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    (tmp_path / "cp1").mkdir()
    service = CheckpointService(checkpoint_repository=DummyCheckpointRepository())
    metadata = service.get_metadata("cp1")
    assert metadata["checkpoint"] == "cp1"
    assert "summary" in metadata
    assert metadata["summary"]["episodes"] == 3
    assert metadata["summary"]["qnet_neurons"] == 16
    assert metadata["summary"]["final_val_loss"] == 0.4
    assert metadata["summary"]["final_val_rmse"] == 0.5

###############################################################################
def test_find_dataset_references_reads_checkpoint_configuration(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    (tmp_path / "cp1").mkdir()
    service = CheckpointService(checkpoint_repository=DummyCheckpointRepository())

    assert service.find_dataset_references(7) == ["cp1"]
    assert service.find_dataset_references(8) == []

###############################################################################
def test_find_dataset_references_blocks_malformed_configuration(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    (tmp_path / "cp1").mkdir()
    service = CheckpointService(checkpoint_repository=InvalidCheckpointRepository())

    with pytest.raises(CheckpointReferenceError, match="Unable to inspect checkpoint"):
        service.find_dataset_references(7)

###############################################################################
def test_delete_checkpoint_removes_folder_through_service(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    checkpoint_path = tmp_path / "cp1"
    checkpoint_path.mkdir()
    (checkpoint_path / "saved_model.keras").write_text("model", encoding="utf-8")
    configuration = checkpoint_path / "configuration"
    configuration.mkdir()
    (configuration / "configuration.json").write_text("{}", encoding="utf-8")
    (configuration / "session_history.json").write_text("{}", encoding="utf-8")

    service = CheckpointService(checkpoint_repository=CheckpointRepository())
    service.delete_checkpoint("cp1")

    assert not checkpoint_path.exists()

###############################################################################
def test_checkpoint_staging_is_not_visible_until_complete_publish(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    repository = CheckpointRepository()
    final_path, staging_path = repository.create_checkpoint_workspace("cp1")
    staging = Path(staging_path)
    (staging / "saved_model.keras").write_text("model", encoding="utf-8")
    configuration = staging / "configuration"
    configuration.mkdir(exist_ok=True)
    (configuration / "configuration.json").write_text("{}", encoding="utf-8")
    (configuration / "session_history.json").write_text("{}", encoding="utf-8")

    assert repository.scan_checkpoints_folder() == []
    repository.publish_checkpoint(staging_path, final_path)

    assert not staging.exists()
    assert Path(final_path, ".complete").is_file()
    assert repository.scan_checkpoints_folder() == ["cp1"]

###############################################################################
def test_incomplete_checkpoint_workspaces_are_cleaned_on_startup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    repository = CheckpointRepository()
    _, staging_path = repository.create_checkpoint_workspace("cp1")

    repository.cleanup_incomplete_workspaces()

    assert not Path(staging_path).exists()





os.environ.setdefault("KERAS_BACKEND", "torch")

###############################################################################
def test_checkpoint_name_validation_rejects_path_traversal_patterns() -> None:
    for candidate in ("", ".", "..", "../x", "..\\x", "x/y", "C:temp", "bad\x00name"):
        with pytest.raises(ValueError):
            normalize_checkpoint_identifier(candidate)

    assert normalize_checkpoint_identifier("checkpoint_01") == "checkpoint_01"

###############################################################################
def test_checkpoint_path_builder_stays_under_checkpoint_root() -> None:
    checkpoint_root = CHECKPOINT_PATH.resolve()
    resolved = resolve_checkpoint_path("safe-checkpoint")

    assert checkpoint_root in resolved.parents
    assert resolved == checkpoint_root / "safe-checkpoint"

###############################################################################
def test_upload_parameter_normalizers_apply_bounds() -> None:
    assert normalize_csv_separator(";") == ";"
    assert normalize_csv_separator("\t") == "\t"
    assert normalize_sheet_name(0) == 0
    assert normalize_sheet_name("Sheet1") == "Sheet1"
    assert normalize_filename(r"..\dataset.csv") == "dataset.csv"

    with pytest.raises(ValueError):
        normalize_csv_separator("::")
    with pytest.raises(ValueError):
        normalize_sheet_name(-1)
    with pytest.raises(ValueError):
        normalize_sheet_name("x" * 129)
    with pytest.raises(ValueError):
        normalize_filename(None)
    with pytest.raises(ValueError):
        normalize_filename("bad\x00.csv")

###############################################################################
def test_dataset_name_normalization_rejects_invalid_values() -> None:
    assert normalize_dataset_name("training_set") == "training_set"

    with pytest.raises(ValueError):
        normalize_dataset_name("")
    with pytest.raises(ValueError):
        normalize_dataset_name("x" * 129)
    with pytest.raises(ValueError):
        normalize_dataset_name("bad\x00name")


###############################################################################
