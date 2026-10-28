# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import pytest
from unittest.mock import Mock
from fastapi import HTTPException
from server.api.datasets import delete_roulette_dataset
from server.api.training import _map_training_exception
from server.services.checkpoints import CheckpointReferenceError
from pathlib import Path
from scripts.generate_frontend_contracts import OUTPUT_PATH, render_typescript


###############################################################################
def test_training_exception_mapping_preserves_conflict_category() -> None:
    mapped = _map_training_exception(RuntimeError("training is already running"))

    assert mapped.status_code == 409
    assert mapped.detail == "training is already running"


###############################################################################
def test_dataset_delete_route_maps_checkpoint_reference_to_conflict() -> None:
    service = Mock()
    service.delete_training_dataset.side_effect = CheckpointReferenceError(
        "dataset is referenced by FAIRS_20260820"
    )

    with pytest.raises(HTTPException) as error:
        delete_roulette_dataset(dataset_id=7, service=service)

    assert error.value.status_code == 409
    assert error.value.detail == "dataset is referenced by FAIRS_20260820"


###############################################################################
def test_generated_frontend_contract_matches_runtime_backend_contract() -> None:
    expected_path = (
        Path(__file__).resolve().parents[2]
        / "client"
        / "src"
        / "generated"
        / "api.ts"
    )
    assert OUTPUT_PATH == expected_path
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_typescript()
