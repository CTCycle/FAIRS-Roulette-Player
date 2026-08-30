from __future__ import annotations

import pytest

from server.common import checkpoints as checkpoint_common
from server.repositories.checkpoints import CheckpointRepository
from server.services.checkpoints import CheckpointReferenceError, CheckpointService


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
                "episodes": 3,
                "batch_size": 8,
                "qnet_neurons": 16,
                "dataset_id": 7,
            },
            {"total_episodes": 3, "history": {"loss": [0.2], "metrics": [0.3]}},
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
    assert metadata["summary"]["neurons"] == 16


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
def test_delete_checkpoint_delegates_filesystem_ownership(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(checkpoint_common.shared_paths, "CHECKPOINT_PATH", tmp_path)
    (tmp_path / "cp1").mkdir()
    repository = DummyCheckpointRepository()
    service = CheckpointService(checkpoint_repository=repository)

    service.delete_checkpoint("cp1")

    assert repository.deleted_paths == [str(tmp_path / "cp1")]


###############################################################################
def test_checkpoint_storage_deletes_checkpoint_folder(tmp_path) -> None:
    checkpoint_path = tmp_path / "cp1"
    checkpoint_path.mkdir()
    (checkpoint_path / "model.keras").write_text("model", encoding="utf-8")

    CheckpointRepository().delete_checkpoint(str(checkpoint_path))

    assert not checkpoint_path.exists()
