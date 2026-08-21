from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from server.api.datasets import delete_roulette_dataset
from server.api.training import _map_training_exception
from server.services.checkpoints import CheckpointReferenceError

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
