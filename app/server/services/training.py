from __future__ import annotations

from functools import partial
import time
from pathlib import Path
from typing import Any

from server.common.checkpoints import normalize_checkpoint_identifier
from server.common.utils.trainingstats import (
    coerce_optional_finite_float,
)
from server.common.utils.types import coerce_finite_float, coerce_finite_int
from server.contracts.configuration import DatabaseSettings
from server.contracts.training import ResumeConfig, TrainingConfig
from server.services.training_worker import (
    ProcessWorker,
    run_resume_training_process,
    run_training_process,
)
from server.services.checkpoints import CheckpointService
from server.services.training_data import load_training_series
from server.services.training_run import TrainingRun, TrainingRunManager


###############################################################################
def calculate_progress(stats: dict[str, Any]) -> float:
    epoch = stats.get("epoch", 0)
    total_epochs = stats.get("total_epochs", 0)
    if not isinstance(epoch, (int, float)) or not isinstance(
        total_epochs, (int, float)
    ):
        return 0.0
    if total_epochs <= 0:
        return 0.0
    progress = (float(epoch) / float(total_epochs)) * 100.0
    return min(100.0, max(0.0, progress))


###############################################################################
def build_history_points(
    session: dict[str, Any],
    initial_capital: float | None = None,
) -> list[dict[str, Any]]:
    history = session.get("history", {}) if isinstance(session, dict) else {}
    episodes = history.get("episode", [])
    time_steps = history.get("time_step", [])
    losses = history.get("loss", [])
    metrics = history.get("metrics", [])
    val_losses = history.get("val_loss", [])
    val_rmses = history.get("val_rmse", [])
    rewards = history.get("reward", [])
    total_rewards = history.get("total_reward", [])
    capitals = history.get("capital", [])

    results: list[dict[str, Any]] = []
    for index in range(len(time_steps)):
        capital_value = coerce_finite_float(
            capitals[index] if index < len(capitals) else 0.0,
            default=0.0,
        )
        capital_gain = (
            capital_value - float(initial_capital)
            if initial_capital is not None
            else 0.0
        )
        epoch = episodes[index] if index < len(episodes) else 0
        epoch = coerce_finite_int(epoch, default=0, minimum=0)
        point = {
            "time_step": coerce_finite_int(
                time_steps[index] if index < len(time_steps) else 0,
                default=0,
                minimum=0,
            ),
            "loss": coerce_finite_float(
                losses[index] if index < len(losses) else 0.0,
                default=0.0,
            ),
            "rmse": coerce_finite_float(
                metrics[index] if index < len(metrics) else 0.0,
                default=0.0,
            ),
            "val_loss": coerce_optional_finite_float(
                val_losses[index] if index < len(val_losses) else None,
            ),
            "val_rmse": coerce_optional_finite_float(
                val_rmses[index] if index < len(val_rmses) else None,
            ),
            "epoch": epoch,
            "reward": coerce_finite_float(
                rewards[index] if index < len(rewards) else 0.0,
                default=0.0,
            ),
            "total_reward": coerce_finite_float(
                total_rewards[index] if index < len(total_rewards) else 0.0,
                default=0.0,
            ),
            "capital": capital_value,
            "capital_gain": capital_gain,
        }
        if isinstance(epoch, int) and epoch > 0:
            results.append(point)
    return results


###############################################################################
class TrainingService:
    JOB_TYPE = "training"

    # -------------------------------------------------------------------------
    def __init__(
        self,
        training_run_manager: TrainingRunManager,
        checkpoint_service: CheckpointService,
        database_settings: DatabaseSettings | None = None,
        database_path: str | Path | None = None,
        polling_interval_seconds: float = 1.0,
        jit_compile: bool = False,
        jit_backend: str = "inductor",
    ) -> None:
        self.training_run_manager = training_run_manager
        self.checkpoint_service = checkpoint_service
        self.database_settings = database_settings
        self.database_path = database_path
        self.polling_interval_seconds = polling_interval_seconds
        self.jit_compile = jit_compile
        self.jit_backend = jit_backend

    # -------------------------------------------------------------------------
    def _handle_training_progress(self, job_id: str, message: dict[str, Any]) -> None:
        if message.get("type") != "training_update":
            return
        stats = {key: value for key, value in message.items() if key != "type"}
        self.training_run_manager.update_training_stats(job_id, stats)
        progress = calculate_progress(stats)
        self.training_run_manager.update_progress(job_id, progress)
        current_status = self.training_run_manager.training_status(
            self.polling_interval_seconds
        )
        self.training_run_manager.update_result(
            job_id,
            {
                "latest_stats": current_status["latest_stats"],
                "progress_percent": progress,
            },
        )

    # -------------------------------------------------------------------------
    def _drain_worker_progress(self, job_id: str, worker: ProcessWorker) -> None:
        while True:
            message = worker.poll(timeout=0.0)
            if message is None:
                return
            self._handle_training_progress(job_id, message)

    # -------------------------------------------------------------------------
    def _monitor_training_process(
        self,
        job_id: str,
        worker: ProcessWorker,
        stop_timeout_seconds: float,
    ) -> dict[str, Any]:
        stop_requested_at: float | None = None
        while worker.is_alive():
            if (
                self.training_run_manager.should_stop(job_id)
                and not worker.is_interrupted()
            ):
                worker.stop()
                stop_requested_at = time.monotonic()
            if stop_requested_at is not None:
                elapsed = time.monotonic() - stop_requested_at
                if elapsed >= stop_timeout_seconds:
                    worker.terminate()
                    break
            message = worker.poll(timeout=0.25)
            if message is not None:
                self._handle_training_progress(job_id, message)
                self._drain_worker_progress(job_id, worker)

        worker.join(timeout=5)
        self._drain_worker_progress(job_id, worker)

        result_payload = worker.read_result()
        if result_payload is None:
            if worker.exitcode not in (
                0,
                None,
            ) and not self.training_run_manager.should_stop(job_id):
                raise RuntimeError(
                    f"Training process exited with code {worker.exitcode}"
                )
            return {}
        if "error" in result_payload and result_payload["error"]:
            raise RuntimeError(str(result_payload["error"]))
        if "result" in result_payload:
            return result_payload["result"] or {}
        return {}

    # -------------------------------------------------------------------------
    def run_training_job(
        self, configuration: dict[str, Any], job_id: str
    ) -> dict[str, Any]:
        worker = ProcessWorker()
        self.training_run_manager.set_worker(job_id, worker)
        try:
            worker.start(
                target=run_training_process,
                kwargs={
                    "configuration": configuration,
                    "training_data_loader": load_training_series,
                    "database_settings": self.database_settings,
                    "database_path": self.database_path,
                    "polling_interval_seconds": self.polling_interval_seconds,
                    "jit_compile": self.jit_compile,
                    "jit_backend": self.jit_backend,
                },
            )
            result = self._monitor_training_process(
                job_id, worker, stop_timeout_seconds=5.0
            )
            if self.training_run_manager.should_stop(job_id):
                self.training_run_manager.update_training_stats(
                    job_id, {"status": "cancelled", "message": "Training cancelled"}
                )
            else:
                current_status = self.training_run_manager.training_status(
                    self.polling_interval_seconds
                )
                final_epoch = current_status["latest_stats"].get("total_epochs", 0)
                self.training_run_manager.update_training_stats(
                    job_id,
                    {
                        "status": "completed",
                        "message": "Training completed",
                        "epoch": final_epoch,
                    },
                )
            return result
        except Exception as exc:
            self.training_run_manager.update_training_stats(
                job_id, {"status": "error", "message": str(exc)}
            )
            raise
        finally:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
            worker.cleanup()
            self.training_run_manager.set_worker(job_id, None)

    # -------------------------------------------------------------------------
    def run_resume_training_job(
        self,
        checkpoint: str,
        additional_episodes: int,
        job_id: str,
    ) -> dict[str, Any]:
        worker = ProcessWorker()
        self.training_run_manager.set_worker(job_id, worker)
        try:
            worker.start(
                target=run_resume_training_process,
                kwargs={
                    "checkpoint": checkpoint,
                    "additional_episodes": additional_episodes,
                    "training_data_loader": load_training_series,
                    "database_settings": self.database_settings,
                    "database_path": self.database_path,
                    "polling_interval_seconds": self.polling_interval_seconds,
                },
            )
            result = self._monitor_training_process(
                job_id, worker, stop_timeout_seconds=5.0
            )
            if self.training_run_manager.should_stop(job_id):
                self.training_run_manager.update_training_stats(
                    job_id, {"status": "cancelled", "message": "Training cancelled"}
                )
            else:
                current_status = self.training_run_manager.training_status(
                    self.polling_interval_seconds
                )
                final_epoch = current_status["latest_stats"].get("total_epochs", 0)
                self.training_run_manager.update_training_stats(
                    job_id,
                    {
                        "status": "completed",
                        "message": "Resume training completed",
                        "epoch": final_epoch,
                    },
                )
            return result
        except Exception as exc:
            self.training_run_manager.update_training_stats(
                job_id, {"status": "error", "message": str(exc)}
            )
            raise
        finally:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
            worker.cleanup()
            self.training_run_manager.set_worker(job_id, None)

    # -------------------------------------------------------------------------
    def start_training(self, config: TrainingConfig) -> dict[str, Any]:
        if self.training_run_manager.is_job_running(self.JOB_TYPE):
            raise RuntimeError("Training is already in progress.")

        base_config = TrainingConfig.model_validate({}).model_dump()
        overrides = config.model_dump(exclude_unset=True)
        configuration = {**base_config, **overrides}

        checkpoint_name = configuration.get("checkpoint_name")
        if isinstance(checkpoint_name, str):
            trimmed_checkpoint_name = checkpoint_name.strip()
            if trimmed_checkpoint_name:
                normalized = normalize_checkpoint_identifier(trimmed_checkpoint_name)
                existing_checkpoints = set(self.checkpoint_service.list_checkpoints())
                if normalized in existing_checkpoints:
                    raise FileExistsError(f"Checkpoint already exists: {normalized}")
                configuration["checkpoint_name"] = normalized
            else:
                configuration["checkpoint_name"] = None
        else:
            configuration["checkpoint_name"] = None

        if not bool(
            configuration.get("use_data_generator", False)
        ) and not configuration.get("dataset_id"):
            raise ValueError("dataset_id is required when use_data_generator is false.")

        total_epochs = int(configuration.get("episodes", 10))
        max_steps = int(configuration.get("max_steps_episode", 2000))
        job_id = self.training_run_manager.start_job(
            job_type=self.JOB_TYPE,
            runner=self.run_training_job,
            kwargs={"configuration": configuration},
            initializer=partial(
                self._initialize_training_run,
                total_epochs=total_epochs,
                max_steps=max_steps,
            ),
        )

        status = self.training_run_manager.training_status(
            self.polling_interval_seconds
        )
        self.training_run_manager.update_result(
            job_id,
            {
                "latest_stats": status["latest_stats"],
                "history": status["history"],
            },
        )
        return {
            "status": "started",
            "message": "Training started successfully",
            "job_id": job_id,
            "job_type": self.JOB_TYPE,
            "poll_interval": self.polling_interval_seconds,
        }

    # -------------------------------------------------------------------------
    def resume_training(self, config: ResumeConfig) -> dict[str, Any]:
        if self.training_run_manager.is_job_running(self.JOB_TYPE):
            raise RuntimeError("Training is already in progress.")

        checkpoint, checkpoint_path = (
            self.checkpoint_service.resolve_existing_checkpoint(config.checkpoint)
        )
        configuration, session = self.checkpoint_service.load_training_configuration(
            checkpoint_path
        )

        from_epoch = int(session.get("total_episodes", 0))
        initial_capital = configuration.get("initial_capital")
        initial_capital_value = (
            float(initial_capital)
            if isinstance(initial_capital, (int, float))
            else None
        )
        restored_points = build_history_points(session, initial_capital_value)

        total_epochs = from_epoch + int(config.additional_episodes)
        max_steps = int(configuration.get("max_steps_episode", 2000))
        job_id = self.training_run_manager.start_job(
            job_type=self.JOB_TYPE,
            runner=self.run_resume_training_job,
            kwargs={
                "checkpoint": checkpoint,
                "additional_episodes": config.additional_episodes,
            },
            initializer=partial(
                self._initialize_training_run,
                total_epochs=total_epochs,
                max_steps=max_steps,
                history_points=restored_points,
                from_epoch=from_epoch,
            ),
        )

        status = self.training_run_manager.training_status(
            self.polling_interval_seconds
        )
        self.training_run_manager.update_result(
            job_id,
            {
                "latest_stats": status["latest_stats"],
                "history": status["history"],
            },
        )
        return {
            "status": "started",
            "message": f"Resuming training from {checkpoint}",
            "job_id": job_id,
            "job_type": self.JOB_TYPE,
            "poll_interval": self.polling_interval_seconds,
        }

    # -------------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        return self.training_run_manager.training_status(self.polling_interval_seconds)

    # -------------------------------------------------------------------------
    def stop(self) -> dict[str, Any]:
        status = self.get_status()
        if not status["is_training"] or not status["job_id"]:
            raise ValueError("No training is in progress.")
        job_id = status["job_id"]
        worker = self.training_run_manager.get_worker(job_id)
        if worker is not None:
            worker.stop()
        self.training_run_manager.cancel_job(job_id)
        return {"status": "stopping", "message": "Training stop requested"}

    # -------------------------------------------------------------------------
    def list_checkpoints(self) -> list[str]:
        return self.checkpoint_service.list_checkpoints()

    # -------------------------------------------------------------------------
    def get_checkpoint_metadata(self, checkpoint: str) -> dict[str, Any]:
        return self.checkpoint_service.get_metadata(checkpoint)

    # -------------------------------------------------------------------------
    def delete_checkpoint(self, checkpoint: str) -> dict[str, str]:
        self.checkpoint_service.delete_checkpoint(checkpoint)
        return {"status": "success", "message": f"Checkpoint {checkpoint} deleted"}

    # -------------------------------------------------------------------------
    def get_job(self, job_id: str) -> dict[str, Any]:
        job_status = self.training_run_manager.get_job_status(job_id)
        if job_status is None:
            raise KeyError(f"Job not found: {job_id}")
        return {
            **job_status,
            "poll_interval": self.polling_interval_seconds,
        }

    # -------------------------------------------------------------------------
    @staticmethod
    def _initialize_training_run(
        run: TrainingRun,
        *,
        total_epochs: int,
        max_steps: int,
        history_points: list[dict[str, Any]] | None = None,
        from_epoch: int = 0,
    ) -> None:
        run.reset_training_state(total_epochs, max_steps)
        if history_points is not None:
            run.restore_history(history_points, from_epoch)

    # -------------------------------------------------------------------------
    def delete_job(self, job_id: str) -> dict[str, Any]:
        job_status = self.training_run_manager.get_job_status(job_id)
        if job_status is None:
            raise KeyError(f"Job not found: {job_id}")
        worker = self.training_run_manager.get_worker(job_id)
        if worker is not None:
            worker.stop()
        success = self.training_run_manager.cancel_job(job_id)
        return {
            "job_id": job_id,
            "success": success,
            "message": "Cancellation requested"
            if success
            else "Job cannot be cancelled",
        }
