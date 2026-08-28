from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from server.contracts.training import ResumeConfig, TrainingConfig
from server.services.training_worker import run_training_process
from server.services import training as training_module
from server.services.training import TrainingService

###############################################################################
def build_service(
    polling_interval_seconds: float = 1.0,
) -> tuple[TrainingService, Mock, Mock]:
    job_manager = Mock()
    job_manager.is_job_running.return_value = False
    job_manager.start_job.return_value = "job123"
    checkpoint_service = Mock()
    checkpoint_service.list_checkpoints.return_value = []
    checkpoint_service.resolve_existing_checkpoint.return_value = ("cp1", "path/cp1")
    checkpoint_service.load_training_configuration.return_value = (
        {"max_steps_episode": 100, "initial_capital": 100},
        {"total_episodes": 2, "history": {"episode": [1, 2], "time_step": [1, 2]}},
    )
    service = TrainingService(
        job_manager=job_manager,
        checkpoint_service=checkpoint_service,
        polling_interval_seconds=polling_interval_seconds,
    )
    return service, job_manager, checkpoint_service

###############################################################################
def test_start_training_starts_job_and_returns_contract() -> None:
    service, job_manager, _ = build_service()
    payload = service.start_training(TrainingConfig(use_data_generator=True))
    assert payload["status"] == "started"
    assert payload["job_id"] == "job123"
    job_manager.start_job.assert_called_once()

###############################################################################
def test_start_training_requires_dataset_without_generator() -> None:
    service, _, _ = build_service()
    with pytest.raises(ValueError, match="dataset_id is required"):
        service.start_training(
            TrainingConfig(use_data_generator=False, dataset_id=None)
        )

###############################################################################
def test_training_responses_use_injected_polling_interval() -> None:
    service, _, _ = build_service(polling_interval_seconds=2.5)

    started = service.start_training(TrainingConfig(use_data_generator=True))

    assert started["poll_interval"] == 2.5
    assert service.get_status()["poll_interval"] == 2.5

###############################################################################
def test_resume_training_starts_resume_job() -> None:
    service, job_manager, _ = build_service()
    payload = service.resume_training(
        ResumeConfig(checkpoint="cp1", additional_episodes=1)
    )
    assert payload["status"] == "started"
    assert payload["job_type"] == "training"
    job_manager.start_job.assert_called_once()

###############################################################################
def test_stop_sets_cancellation_on_current_job() -> None:
    service, job_manager, _ = build_service()
    service.training_state.is_training = True
    service.training_state.current_job_id = "job123"
    payload = service.stop()
    assert payload["status"] == "stopping"
    job_manager.cancel_job.assert_called_once_with("job123")

###############################################################################
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

###############################################################################
def test_training_worker_receives_explicit_runtime_dependencies(monkeypatch) -> None:
    started: dict[str, object] = {}

    ###############################################################################
    class FakeWorker:

        # -------------------------------------------------------------------------
        def start(self, target, kwargs) -> None:
            started["target"] = target
            started["kwargs"] = kwargs

        # -------------------------------------------------------------------------
        def is_alive(self) -> bool:
            return False

        # -------------------------------------------------------------------------
        @property
        def exitcode(self) -> None:
            return None

        # -------------------------------------------------------------------------
        def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
            return None

        # -------------------------------------------------------------------------
        def read_result(self) -> None:
            return None

        # -------------------------------------------------------------------------
        def poll(self, timeout: float = 0.0) -> None:  # noqa: ARG002
            return None

        # -------------------------------------------------------------------------
        def cleanup(self) -> None:
            return None

    monkeypatch.setattr(training_module, "ProcessWorker", FakeWorker)
    job_manager = Mock()
    job_manager.should_stop.return_value = False
    service = TrainingService(
        job_manager=job_manager,
        checkpoint_service=Mock(),
        database_settings=object(),
        database_path=Path("isolated.db"),
        polling_interval_seconds=2.5,
        jit_compile=True,
        jit_backend="eager",
    )

    service.run_training_job({}, "job123")

    assert started["target"] is run_training_process
    assert started["kwargs"] == {
        "configuration": {},
        "training_data_loader": training_module.load_training_series,
        "database_settings": service.database_settings,
        "database_path": Path("isolated.db"),
        "polling_interval_seconds": 2.5,
        "jit_compile": True,
        "jit_backend": "eager",
    }
