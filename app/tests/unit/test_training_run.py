from __future__ import annotations

from threading import Event

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
