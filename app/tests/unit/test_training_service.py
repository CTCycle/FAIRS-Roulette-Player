from __future__ import annotations

from unittest.mock import Mock

import pytest

from server.domain.training import ResumeConfig, TrainingConfig
from server.services.training import TrainingService


def build_service() -> tuple[TrainingService, Mock, Mock]:
    job_manager = Mock()
    job_manager.is_job_running.return_value = False
    job_manager.start_job.return_value = "job123"
    checkpoint_service = Mock()
    checkpoint_service.list_checkpoints.return_value = []
    checkpoint_service.resolve_existing_checkpoint.return_value = ("cp1", "path/cp1")
    checkpoint_service.model_serializer.load_training_configuration.return_value = (
        {"max_steps_episode": 100, "initial_capital": 100},
        {"total_episodes": 2, "history": {"episode": [1, 2], "time_step": [1, 2]}},
    )
    service = TrainingService(job_manager=job_manager, checkpoint_service=checkpoint_service)
    return service, job_manager, checkpoint_service


def test_start_training_starts_job_and_returns_contract() -> None:
    service, job_manager, _ = build_service()
    payload = service.start_training(TrainingConfig(use_data_generator=True))
    assert payload["status"] == "started"
    assert payload["job_id"] == "job123"
    job_manager.start_job.assert_called_once()


def test_start_training_requires_dataset_without_generator() -> None:
    service, _, _ = build_service()
    with pytest.raises(ValueError, match="dataset_id is required"):
        service.start_training(TrainingConfig(use_data_generator=False, dataset_id=None))


def test_resume_training_starts_resume_job() -> None:
    service, job_manager, _ = build_service()
    payload = service.resume_training(ResumeConfig(checkpoint="cp1", additional_episodes=1))
    assert payload["status"] == "started"
    assert payload["job_type"] == "training"
    job_manager.start_job.assert_called_once()


def test_stop_sets_cancellation_on_current_job() -> None:
    service, job_manager, _ = build_service()
    service.training_state.is_training = True
    service.training_state.current_job_id = "job123"
    payload = service.stop()
    assert payload["status"] == "stopping"
    job_manager.cancel_job.assert_called_once_with("job123")


def test_get_and_delete_job_contracts() -> None:
    service, job_manager, _ = build_service()
    job_manager.get_job_status.return_value = {
        "job_id": "job123",
        "job_type": "training",
        "status": "running",
        "progress": 42.0,
        "result": None,
        "error": None,
        "created_at": 0.0,
        "completed_at": None,
    }
    job = service.get_job("job123")
    cancel = service.delete_job("job123")
    assert job["job_id"] == "job123"
    assert cancel["job_id"] == "job123"
