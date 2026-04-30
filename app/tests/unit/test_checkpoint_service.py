from __future__ import annotations

import pytest

from server.common import checkpoints as checkpoint_common
from server.services.checkpoints import CheckpointService


class DummyModelSerializer:
    def __init__(self) -> None:
        self._checkpoints = ["cp1"]

    def scan_checkpoints_folder(self) -> list[str]:
        return list(self._checkpoints)

    def load_training_configuration(self, path: str) -> tuple[dict, dict]:  # noqa: ARG002
        return (
            {"episodes": 3, "batch_size": 8, "qnet_neurons": 16},
            {"total_episodes": 3, "history": {"loss": [0.2], "metrics": [0.3]}},
        )


def test_resolve_existing_checkpoint_rejects_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(checkpoint_common, "CHECKPOINT_PATH", str(tmp_path))
    service = CheckpointService(model_serializer=DummyModelSerializer())
    with pytest.raises(FileNotFoundError):
        service.resolve_existing_checkpoint("missing")


def test_get_metadata_returns_summary_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(checkpoint_common, "CHECKPOINT_PATH", str(tmp_path))
    (tmp_path / "cp1").mkdir()
    service = CheckpointService(model_serializer=DummyModelSerializer())
    metadata = service.get_metadata("cp1")
    assert metadata["checkpoint"] == "cp1"
    assert "summary" in metadata
    assert metadata["summary"]["episodes"] == 3
    assert metadata["summary"]["neurons"] == 16
