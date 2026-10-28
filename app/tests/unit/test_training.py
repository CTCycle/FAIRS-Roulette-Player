# Copyright © 2023 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import pandas as pd
import pytest
import time
from server.contracts.training import TrainingConfig, ResumeConfig
from server.learning.training.fitting import DQNTraining
from pathlib import Path
from unittest.mock import Mock
from server.contracts.configuration import DeviceSettings, JobsSettings, RouletteSettings
from server.services.training_worker import process_target, run_training_process
from server.services import training as training_module
from server.services.training import TrainingService
from threading import Event
from server.services.training_run import TrainingRun, TrainingRunManager, default_training_stats
from server.common.roulette import ROULETTE_RUNTIME_ATTR, encode_roulette_series
from server.services.training_data import TrainingDataService
from pydantic import ValidationError


###############################################################################
def build_configuration(**overrides: object) -> dict[str, object]:
    configuration = TrainingConfig(use_data_generator=True).model_dump()
    configuration.update(
        {
            "training_seed": 7,
            "batch_size": 8,
            "model_update_frequency": 10,
            "replay_buffer_size": 20,
            "max_memory_size": 100,
            "perceptive_field_size": 8,
            "max_steps_episode": 100,
            "initial_capital": 100,
            "bet_amount": 1,
            "validation_size": 0.2,
        }
    )
    configuration.update(overrides)
    return configuration


###############################################################################
def test_training_and_resume_share_validation_environment_builder() -> None:
    trainer = DQNTraining(build_configuration())
    data = pd.DataFrame({"extraction": [index % 37 for index in range(100)]})

    training_environment, validation_environment, state_size = trainer._build_environments(
        data,
        "checkpoint",
    )

    assert state_size == 8
    assert len(training_environment.extractions) == 80
    assert validation_environment is not None
    assert len(validation_environment.extractions) == 20


###############################################################################
def test_validation_partition_must_support_perceptive_window() -> None:
    trainer = DQNTraining(
        build_configuration(perceptive_field_size=16, validation_size=0.1)
    )
    data = pd.DataFrame({"extraction": [index % 37 for index in range(100)]})

    with pytest.raises(ValueError, match="Validation partition"):
        trainer._build_environments(data, "checkpoint")


###############################################################################
def test_latest_stats_does_not_carry_sparse_validation_metrics_forward() -> None:
    trainer = DQNTraining(build_configuration())
    trainer.session_stats["val_loss"] = [0.4]
    trainer.session_stats["val_rmse"] = [0.5]
    trainer.session_stats["img_reward"] = [3.0]
    trainer.latest_metric_state.update(
        {"val_loss": None, "val_rmse": None, "val_reward": None}
    )

    latest_stats = trainer.get_latest_stats(0, 1, training_ready=True)

    assert latest_stats["val_loss"] is None
    assert latest_stats["val_rmse"] is None
    assert latest_stats["val_reward"] is None


###############################################################################
def build_service(
    polling_interval_seconds: float = 1.0,
) -> tuple[TrainingService, Mock, Mock]:
    training_run_manager = Mock()
    training_run_manager.is_job_running.return_value = False
    training_run_manager.start_job.return_value = "job123"
    dataset_repository = Mock()
    dataset_repository.get.return_value = {"dataset_kind": "training"}
    training_run_manager.training_status.return_value = {
        "job_id": "job123",
        "is_training": True,
        "latest_stats": {"total_epochs": 10},
        "history": [],
        "latest_env": {},
        "poll_interval": polling_interval_seconds,
    }
    checkpoint_service = Mock()
    checkpoint_service.list_checkpoints.return_value = []
    checkpoint_service.resolve_existing_checkpoint.return_value = ("cp1", "path/cp1")
    checkpoint_service.load_training_configuration.return_value = (
        {"max_steps_episode": 100, "initial_capital": 100},
        {"total_episodes": 2, "history": {"episode": [1, 2], "time_step": [1, 2]}},
    )
    service = TrainingService(
        training_run_manager=training_run_manager,
        checkpoint_service=checkpoint_service,
        dataset_repository=dataset_repository,
        polling_interval_seconds=polling_interval_seconds,
    )
    return service, training_run_manager, checkpoint_service


###############################################################################
def test_start_training_starts_job_and_returns_contract() -> None:
    service, training_run_manager, _ = build_service()
    payload = service.start_training(TrainingConfig(use_data_generator=True))
    assert payload["status"] == "started"
    assert payload["job_id"] == "job123"
    training_run_manager.start_job.assert_called_once()


###############################################################################
def test_start_training_requires_dataset_without_generator() -> None:
    service, _, _ = build_service()
    with pytest.raises(ValueError, match="dataset_id is required"):
        service.start_training(
            TrainingConfig(use_data_generator=False, dataset_id=None)
        )


###############################################################################
def test_start_training_rejects_missing_dataset_before_creating_job() -> None:
    service, training_run_manager, _ = build_service()
    service.dataset_repository.get.return_value = None

    with pytest.raises(FileNotFoundError, match="Training dataset '987654321'"):
        service.start_training(
            TrainingConfig(dataset_id=987654321, use_data_generator=False)
        )

    service.dataset_repository.get.assert_called_once_with(987654321)
    training_run_manager.start_job.assert_not_called()


###############################################################################
def test_start_training_rejects_non_training_dataset_before_creating_job() -> None:
    service, training_run_manager, _ = build_service()
    service.dataset_repository.get.return_value = {"dataset_kind": "inference"}

    with pytest.raises(ValueError, match="is not a training dataset"):
        service.start_training(
            TrainingConfig(dataset_id=987654321, use_data_generator=False)
        )

    service.dataset_repository.get.assert_called_once_with(987654321)
    training_run_manager.start_job.assert_not_called()


###############################################################################
def test_validation_rejects_existing_checkpoint_before_creating_job() -> None:
    service, training_run_manager, checkpoint_service = build_service()
    checkpoint_service.list_checkpoints.return_value = ["already_saved"]
    config = TrainingConfig(
        use_data_generator=True,
        checkpoint_name="already_saved",
    )

    with pytest.raises(FileExistsError, match="Checkpoint already exists"):
        service.validate_training_configuration(config)

    with pytest.raises(FileExistsError, match="Checkpoint already exists"):
        service.start_training(config)

    training_run_manager.start_job.assert_not_called()


###############################################################################
def test_training_responses_use_injected_polling_interval() -> None:
    service, _, _ = build_service(polling_interval_seconds=2.5)

    started = service.start_training(TrainingConfig(use_data_generator=True))

    assert started["poll_interval"] == 2.5
    assert service.get_status()["poll_interval"] == 2.5


###############################################################################
def test_start_training_preflights_runtime_jit(monkeypatch) -> None:
    service, training_run_manager, _ = build_service()
    service.apply_runtime_settings(
        JobsSettings(polling_interval=1.0),
        DeviceSettings(jit_compile=True, jit_backend="eager"),
    )
    validator = Mock(side_effect=ValueError("JIT runtime unavailable"))
    monkeypatch.setattr(training_module, "validate_jit_runtime", validator)

    with pytest.raises(ValueError, match="JIT runtime unavailable"):
        service.start_training(TrainingConfig(use_data_generator=True))

    validator.assert_called_once_with(True, "eager")
    training_run_manager.start_job.assert_not_called()


###############################################################################
def test_resume_training_starts_resume_job() -> None:
    service, training_run_manager, _ = build_service()
    payload = service.resume_training(
        ResumeConfig(checkpoint="cp1", additional_episodes=1)
    )
    assert payload["status"] == "started"
    assert payload["job_type"] == "training"
    training_run_manager.start_job.assert_called_once()


###############################################################################
def test_resume_training_rejects_an_active_training_job_before_checkpoint_load() -> None:
    service, training_run_manager, checkpoint_service = build_service()
    training_run_manager.is_job_running.return_value = True

    with pytest.raises(RuntimeError, match="Training is already in progress"):
        service.resume_training(
            ResumeConfig(checkpoint="cp1", additional_episodes=1)
        )

    checkpoint_service.resolve_existing_checkpoint.assert_not_called()
    training_run_manager.start_job.assert_not_called()


###############################################################################
def test_stop_sets_cancellation_on_current_job() -> None:
    service, training_run_manager, _ = build_service()
    payload = service.stop()
    assert payload["status"] == "stopping"
    training_run_manager.cancel_job.assert_called_once_with("job123")


###############################################################################
def test_get_and_delete_job_contracts() -> None:
    service, training_run_manager, _ = build_service()
    training_run_manager.get_job_status.return_value = {
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
        def read_result(self) -> dict[str, object]:
            return {
                "result": {
                    "final_loss": 1.25,
                    "final_rmse": 1.11803398875,
                }
            }

        # -------------------------------------------------------------------------
        def poll(self, timeout: float = 0.0) -> None:  # noqa: ARG002
            return None

        # -------------------------------------------------------------------------
        def cleanup(self) -> None:
            return None

    monkeypatch.setattr(training_module, "ProcessWorker", FakeWorker)
    training_run_manager = Mock()
    training_run_manager.should_stop.return_value = False
    training_run_manager.training_status.return_value = {
        "latest_stats": {"total_epochs": 0},
    }
    service = TrainingService(
        training_run_manager=training_run_manager,
        checkpoint_service=Mock(),
        dataset_repository=Mock(),
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
        "roulette_settings": service.roulette_settings,
    }
    training_run_manager.update_training_stats.assert_called_once_with(
        "job123",
        {
            "status": "completed",
            "message": "Training completed",
            "epoch": 0,
            "loss": 1.25,
            "rmse": 1.11803398875,
        },
    )


###############################################################################
def test_training_process_bootstraps_runtime_before_running_target(monkeypatch) -> None:
    from server import bootstrap as bootstrap_module

    calls: list[tuple[str, object]] = []
    worker = object()

    def bootstrap() -> None:
        calls.append(("bootstrap", None))

    def target(*, worker: object, marker: str) -> None:
        calls.append(("target", (worker, marker)))

    monkeypatch.setattr(bootstrap_module, "bootstrap_runtime", bootstrap)

    process_target(target, {"marker": "isolated"}, worker)

    assert calls == [
        ("bootstrap", None),
        ("target", (worker, "isolated")),
    ]


###############################################################################
def test_default_training_stats_match_the_frontend_status_contract() -> None:
    stats = default_training_stats()

    assert stats["status"] == "idle"
    assert stats["current_bet_amount"] is None
    assert stats["current_strategy_id"] is None
    assert stats["epsilon"] is None
    assert stats["experience_count"] == 0
    assert stats["replay_buffer_size"] == 0


###############################################################################
def test_training_run_projects_dqn_warmup_telemetry_into_history() -> None:
    run = TrainingRun(job_id="job123", job_type="training")
    run.reset_training_state(total_epochs=2, max_steps=100)

    run.update_stats(
        {
            "status": "exploration",
            "epoch": 1,
            "time_step": 12,
            "epsilon": 0.75,
            "experience_count": 13,
            "replay_buffer_size": 100,
            "reward": 1,
            "total_reward": 4,
            "capital": 104,
            "capital_gain": 4,
            "loss": None,
            "rmse": None,
            "val_loss": None,
            "val_rmse": None,
            "val_reward": None,
        }
    )

    assert run.latest_stats["epsilon"] == 0.75
    assert run.history_points[-1]["experience_count"] == 13
    assert run.history_points[-1]["replay_buffer_size"] == 100


###############################################################################
def test_training_history_stays_bounded_and_keeps_newest_observations() -> None:
    run = TrainingRun(job_id="bounded", job_type="training")
    run.reset_training_state(total_epochs=1, max_steps=3000)
    update_durations: list[float] = []

    for time_step in range(1, run.max_history_points + 2):
        started_at = time.perf_counter()
        run.update_stats(
            {
                "status": "training",
                "epoch": 1,
                "time_step": time_step,
                "loss": float(time_step),
                "rmse": 0.5,
            }
        )
        update_durations.append(time.perf_counter() - started_at)
        assert len(run.history_points) <= run.max_history_points

    assert len(run.history_points) == 2000
    assert run.history_points[0]["time_step"] == 2
    assert run.history_points[-1]["time_step"] == 2001
    print(
        "VAL22 telemetry bound: "
        f"updates={len(update_durations)}, retained={len(run.history_points)}, "
        f"total={sum(update_durations):.4f}s, "
        f"mean_per_update={sum(update_durations) / len(update_durations):.6f}s, "
        f"max={max(update_durations):.6f}s, timeout=none (unit in-process path)"
    )


###############################################################################
def test_training_run_manager_owns_the_completed_run_projection() -> None:
    manager = TrainingRunManager()
    runner_started = Event()

    def runner(*, job_id: str) -> dict[str, str]:
        assert job_id
        runner_started.set()
        return {"checkpoint_path": "checkpoint"}

    def initialize(run: TrainingRun) -> None:
        run.reset_training_state(total_epochs=2, max_steps=100)

    job_id = manager.start_job("training", runner, initializer=initialize)
    assert runner_started.wait(timeout=2)
    manager.threads[job_id].join(timeout=2)

    job = manager.get_job_status(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["result"] == {"checkpoint_path": "checkpoint"}
    status = manager.training_status(1.0)
    assert status["is_training"] is False
    assert status["latest_stats"]["total_epochs"] == 2
    assert status["latest_stats"]["max_steps"] == 100


###############################################################################
def test_manager_rejects_a_second_start_while_the_first_run_is_stopping() -> None:
    manager = TrainingRunManager()
    runner_started = Event()
    release_runner = Event()

    def runner(*, job_id: str) -> dict[str, str]:
        assert job_id
        runner_started.set()
        release_runner.wait(timeout=2)
        return {}

    job_id = manager.start_job("training", runner)
    assert runner_started.wait(timeout=2)
    assert manager.request_stop(job_id) is True
    assert manager.get_job_status(job_id)["status"] == "stopping"

    with pytest.raises(RuntimeError, match="already in progress"):
        manager.start_job("training", runner)

    release_runner.set()
    manager.threads[job_id].join(timeout=2)
    assert manager.get_job_status(job_id)["status"] == "cancelled"
    assert manager.shutdown(timeout_seconds=1.0) is True


###############################################################################
def test_manager_shutdown_force_terminates_an_unresponsive_worker() -> None:
    manager = TrainingRunManager()
    runner_started = Event()


    ###############################################################################
    class FakeWorker:

        # -------------------------------------------------------------------------
        def __init__(self) -> None:
            self.alive = True
            self.stop_calls = 0
            self.terminate_calls = 0

        # -------------------------------------------------------------------------
        def stop(self) -> None:
            self.stop_calls += 1

        # -------------------------------------------------------------------------
        def is_alive(self) -> bool:
            return self.alive

        # -------------------------------------------------------------------------
        def terminate(self) -> None:
            self.terminate_calls += 1
            self.alive = False

    worker = FakeWorker()

    def runner(*, job_id: str) -> dict[str, str]:
        manager.set_worker(job_id, worker)
        runner_started.set()
        while worker.is_alive():
            time.sleep(0.005)
        return {}

    job_id = manager.start_job("training", runner)
    assert runner_started.wait(timeout=2)

    assert manager.shutdown(timeout_seconds=0.05) is True
    assert worker.stop_calls == 1
    assert worker.terminate_calls == 1
    assert manager.get_job_status(job_id)["status"] == "cancelled"


###############################################################################
def test_terminal_jobs_release_thread_and_worker_references() -> None:
    manager = TrainingRunManager()


    ###############################################################################
    class Worker:

        # -------------------------------------------------------------------------
        def __init__(self) -> None:
            self.stopped = False

        # -------------------------------------------------------------------------
        def stop(self) -> None:
            self.stopped = True

        # -------------------------------------------------------------------------
        def is_alive(self) -> bool:
            return False

    previous_job_id: str | None = None
    cycle_durations: list[float] = []
    for _cycle in range(4):
        started_at = time.perf_counter()
        runner_started = Event()
        release_runner = Event()
        worker = Worker()

        def runner(*, job_id: str) -> dict[str, str]:
            manager.set_worker(job_id, worker)
            runner_started.set()
            assert release_runner.wait(timeout=2)
            return {}

        job_id = manager.start_job("training", runner)
        thread = manager.threads[job_id]
        assert runner_started.wait(timeout=2)
        release_runner.set()
        thread.join(timeout=2)

        assert not thread.is_alive()
        assert manager.get_job_status(job_id)["status"] == "completed"
        assert not manager.is_job_running()
        if previous_job_id is not None:
            assert previous_job_id not in manager.threads
            assert manager.get_worker(previous_job_id) is None
        previous_job_id = job_id
        cycle_durations.append(time.perf_counter() - started_at)

    assert manager.shutdown(timeout_seconds=1.0) is True
    assert manager.shutdown(timeout_seconds=1.0) is True
    assert manager.threads == {}
    assert previous_job_id is not None
    assert manager.get_worker(previous_job_id) is None
    print(
        "VAL22 training manager cleanup: "
        f"cycles={len(cycle_durations)}, total={sum(cycle_durations):.4f}s, "
        f"per_cycle={[round(value, 4) for value in cycle_durations]}, "
        f"max={max(cycle_durations):.4f}s, timeout=worker join 2s; shutdown 1s"
    )


###############################################################################
def test_generated_training_series_matches_environment_contract() -> None:
    service = TrainingDataService(database_settings=None)

    dataset, synthetic = service.get_training_series(
        {
            "use_data_generator": True,
            "num_generated_samples": 100,
            "perceptive_field_size": 8,
            "max_steps_episode": 100,
            "seed": 42,
        }
    )

    assert synthetic is True
    assert len(dataset) == 100
    assert "extraction" in dataset.columns
    assert "wheel_position" in dataset.columns
    assert "color_code" in dataset.columns
    assert "outcome" not in dataset.columns
    assert dataset["extraction"].between(0, 36).all()


###############################################################################
def test_generated_training_series_respects_runtime_number_pool() -> None:
    service = TrainingDataService(database_settings=None)
    roulette_settings = RouletteSettings(
        minimum_number=0,
        maximum_number=8,
        exclude_zero=True,
        invert_colors=True,
        show_number_labels=False,
    )

    dataset, synthetic = service.get_training_series(
        {
            "use_data_generator": True,
            "num_generated_samples": 500,
            "perceptive_field_size": 8,
            "max_steps_episode": 100,
            "seed": 42,
        },
        roulette_settings,
    )

    assert synthetic is True
    assert dataset["extraction"].between(1, 8).all()
    assert 0 not in set(dataset["extraction"].tolist())
    assert dataset.attrs[ROULETTE_RUNTIME_ATTR] == {
        "minimum_number": 0,
        "maximum_number": 8,
        "exclude_zero": True,
        "invert_colors": True,
        "show_number_labels": False,
    }


###############################################################################
def test_roulette_encoding_isolated_from_input_frame() -> None:
    source = pd.DataFrame({"outcome": [0, 1, 32]})

    encoded = encode_roulette_series(source)

    assert list(source.columns) == ["outcome"]
    assert encoded["color_code"].notna().all()
    assert encoded["wheel_position"].notna().all()


###############################################################################
def test_training_subsample_preserves_contiguous_sequence_order() -> None:
    source = pd.DataFrame({"outcome": list(range(20))})

    sampled = TrainingDataService._sample_contiguous_window(source, 0.5, seed=7)
    repeated = TrainingDataService._sample_contiguous_window(source, 0.5, seed=7)

    assert len(sampled) == 10
    assert sampled["outcome"].diff().dropna().eq(1).all()
    pd.testing.assert_frame_equal(sampled, repeated)


###############################################################################
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"exploration_rate": 0.1, "minimum_exploration_rate": 0.2},
            "minimum_exploration_rate must not exceed exploration_rate",
        ),
        (
            {"max_memory_size": 500, "replay_buffer_size": 600},
            "replay_buffer_size must not exceed max_memory_size",
        ),
        (
            {"batch_size": 256, "replay_buffer_size": 128},
            "batch_size must not exceed replay_buffer_size",
        ),
        (
            {"dynamic_betting_enabled": False, "bet_strategy_model_enabled": True},
            "bet_strategy_model_enabled requires dynamic_betting_enabled",
        ),
        (
            {
                "dynamic_betting_enabled": True,
                "bet_unit": 20,
                "bet_max": 10,
            },
            "bet_max must be greater than or equal to bet_unit",
        ),
    ],
)
def test_training_config_rejects_inconsistent_dqn_relationships(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        TrainingConfig(use_data_generator=True, **overrides)
