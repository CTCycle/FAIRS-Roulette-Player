from __future__ import annotations

from threading import Event
import time

import pytest

from server.services.training_run import (
    TrainingRun,
    TrainingRunManager,
    default_training_stats,
)


###############################################################################
def test_default_training_stats_match_the_frontend_status_contract() -> None:
    stats = default_training_stats()

    assert stats["status"] == "idle"
    assert stats["current_bet_amount"] is None
    assert stats["current_strategy_id"] is None


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

    class FakeWorker:
        def __init__(self) -> None:
            self.alive = True
            self.stop_calls = 0
            self.terminate_calls = 0

        def stop(self) -> None:
            self.stop_calls += 1

        def is_alive(self) -> bool:
            return self.alive

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
