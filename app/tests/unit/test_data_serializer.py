from __future__ import annotations

from unittest.mock import Mock

from server.repositories.serialization.data import DataSerializer

###############################################################################
def test_delete_dataset_delegates_to_cascade_repository() -> None:
    datasets = Mock()
    serializer = DataSerializer(datasets=datasets, inference=Mock())

    serializer.delete_dataset(7)

    datasets.delete.assert_called_once_with(7)

###############################################################################
def test_clear_inference_session_steps_delegates_to_repository() -> None:
    inference = Mock()
    serializer = DataSerializer(datasets=Mock(), inference=inference)

    serializer.clear_inference_session_steps("session_1")

    inference.clear_steps.assert_called_once_with("session_1")

###############################################################################
def test_delete_inference_session_delegates_to_repository() -> None:
    inference = Mock()
    serializer = DataSerializer(datasets=Mock(), inference=inference)

    serializer.delete_inference_session("session_2")

    inference.delete_session.assert_called_once_with("session_2")
