from __future__ import annotations

import math
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status

from FAIRS.server.entities.training import ResumeConfig, TrainingConfig
from FAIRS.server.entities.jobs import JobCancelResponse, JobStartResponse, JobStatusResponse
from FAIRS.server.configurations import server_settings
from FAIRS.server.configurations.server import get_poll_interval_seconds
from FAIRS.server.common.constants import CHECKPOINT_PATH
from FAIRS.server.services.jobs import JobManager, job_manager
from FAIRS.server.common.utils.logger import logger
from FAIRS.server.common.utils.types import coerce_finite_float, coerce_finite_int
from FAIRS.server.learning.training.serializer import ModelSerializer
from FAIRS.server.learning.training.worker import (
    ProcessWorker,
    run_resume_training_process,
    run_training_process,
)


router = APIRouter(prefix="/training", tags=["training"])
TRAINING_STATUSES = {
    "idle",
    "exploration",
    "training",
    "completed",
    "error",
    "cancelled",
}
HISTORY_POINTS_PER_EPISODE = 20


def coerce_optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(candidate):
        return candidate
    return None


def sanitize_training_stats(stats: dict[str, Any]) -> dict[str, Any]:
    if not stats:
        return {}
    sanitized = {**stats}

    if "epoch" in stats:
        sanitized["epoch"] = coerce_finite_int(stats.get("epoch"), 0, minimum=0)
    if "total_epochs" in stats:
        sanitized["total_epochs"] = coerce_finite_int(
            stats.get("total_epochs"), 0, minimum=0
        )
    if "max_steps" in stats:
        sanitized["max_steps"] = coerce_finite_int(stats.get("max_steps"), 0, minimum=0)
    if "time_step" in stats:
        sanitized["time_step"] = coerce_finite_int(stats.get("time_step"), 0, minimum=0)

    for metric_key in (
        "loss",
        "rmse",
        "val_loss",
        "val_rmse",
        "reward",
        "val_reward",
        "total_reward",
        "capital",
        "capital_gain",
    ):
        if metric_key not in stats:
            continue
        sanitized[metric_key] = coerce_optional_finite_float(stats.get(metric_key))

    status_value = stats.get("status")
    if isinstance(status_value, str) and status_value in TRAINING_STATUSES:
        sanitized["status"] = status_value
    elif "status" in sanitized:
        sanitized.pop("status")
    return sanitized


###############################################################################
class TrainingState:
    def __init__(self) -> None:
        self.is_training = False
        self.current_job_id: str | None = None
        self.worker: ProcessWorker | None = None
        self.max_steps = 0
        self.latest_stats: dict[str, Any] = {
            "epoch": 0,
            "total_epochs": 0,
            "max_steps": 0,
            "time_step": 0,
            "loss": None,
            "rmse": None,
            "val_loss": None,
            "val_rmse": None,
            "reward": 0,
            "val_reward": None,
            "total_reward": 0,
            "capital": 0,
            "capital_gain": 0.0,
            "status": "idle",
        }
        self.history_points: list[dict[str, Any]] = []
        self.max_history_points = 2000
        self.history_bucket_size = 1.0
        self.last_history_episode: int | None = None
        self.last_history_bucket: int | None = None
        self.latest_env: dict[str, Any] = {}

    # -------------------------------------------------------------------------
    def reset_for_new_session(
        self,
        total_epochs: int,
        max_steps: int,
        job_id: str,
    ) -> None:
        self.is_training = True
        self.current_job_id = job_id
        self.max_steps = max_steps
        self.latest_stats = {
            "epoch": 0,
            "total_epochs": total_epochs,
            "max_steps": max_steps,
            "time_step": 0,
            "loss": None,
            "rmse": None,
            "val_loss": None,
            "val_rmse": None,
            "reward": 0,
            "val_reward": None,
            "total_reward": 0,
            "capital": 0,
            "capital_gain": 0.0,
            "status": "exploration",
        }
        self.history_points = []
        self.history_bucket_size = (
            max_steps / float(HISTORY_POINTS_PER_EPISODE)
            if max_steps > 0
            else 1.0
        )
        self.last_history_episode = None
        self.last_history_bucket = None
        self.latest_env = {}

    # -------------------------------------------------------------------------
    def update_stats(self, stats: dict[str, Any]) -> None:
        sanitized = sanitize_training_stats(stats)
        self.latest_stats = {**self.latest_stats, **sanitized}
        self.add_history_point(self.latest_stats)

    # -------------------------------------------------------------------------
    def add_history_point(self, stats: dict[str, Any]) -> None:
        if stats.get("status") not in {"training", "exploration"}:
            return
        time_step = stats.get("time_step")
        loss = stats.get("loss")
        rmse = stats.get("rmse")
        epoch = stats.get("epoch")
        if not isinstance(time_step, int):
            return
        if not isinstance(loss, (int, float)) or not isinstance(rmse, (int, float)):
            return
        if not math.isfinite(float(loss)) or not math.isfinite(float(rmse)):
            return
        if not isinstance(epoch, int):
            return
        if epoch <= 0:
            return
        point = {
            "time_step": time_step,
            "loss": float(loss),
            "rmse": float(rmse),
            "val_loss": (
                coerce_optional_finite_float(stats.get("val_loss"))
            ),
            "val_rmse": (
                coerce_optional_finite_float(stats.get("val_rmse"))
            ),
            "epoch": epoch,
            "reward": coerce_finite_float(stats.get("reward"), 0.0),
            "total_reward": coerce_finite_float(stats.get("total_reward"), 0.0),
            "capital": coerce_finite_float(stats.get("capital"), 0.0),
            "capital_gain": coerce_finite_float(stats.get("capital_gain"), 0.0),
        }
        if self.history_points:
            previous = self.history_points[-1]
            previous_epoch = previous.get("epoch")
            previous_step = previous.get("time_step")
            if previous_epoch == point["epoch"] and previous_step == point["time_step"]:
                self.history_points[-1] = point
                return
            if (
                isinstance(previous_epoch, int)
                and isinstance(previous_step, int)
                and point["epoch"] < previous_epoch
            ):
                return
            if (
                isinstance(previous_epoch, int)
                and isinstance(previous_step, int)
                and point["epoch"] == previous_epoch
                and point["time_step"] < previous_step
            ):
                return

        self.history_points.append(point)

        if len(self.history_points) > self.max_history_points:
            self.history_points = self.history_points[-self.max_history_points :]

    # -------------------------------------------------------------------------
    def finish_session(self) -> None:
        self.is_training = False
        self.worker = None
        self.current_job_id = None


training_state = TrainingState()


###############################################################################
def calculate_progress(stats: dict[str, Any]) -> float:
    epoch = stats.get("epoch", 0)
    total_epochs = stats.get("total_epochs", 0)
    if not isinstance(epoch, (int, float)) or not isinstance(total_epochs, (int, float)):
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

    episode_offset = 1 if any(
        isinstance(value, int) and value <= 0 for value in episodes
    ) else 0
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
        epoch = coerce_finite_int(epoch, default=0, minimum=0) + episode_offset
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
def handle_training_progress(job_id: str, message: dict[str, Any]) -> None:
    if message.get("type") != "training_update":
        return

    stats = {key: value for key, value in message.items() if key != "type"}
    training_state.update_stats(stats)
    progress = calculate_progress(stats)

    job_manager.update_progress(job_id, progress)
    job_manager.update_result(
        job_id,
        {
            "latest_stats": training_state.latest_stats,
            "progress_percent": progress,
        },
    )


###############################################################################
def drain_worker_progress(job_id: str, worker: ProcessWorker) -> None:
    while True:
        message = worker.poll(timeout=0.0)
        if message is None:
            return
        handle_training_progress(job_id, message)


###############################################################################
def monitor_training_process(
    job_id: str,
    worker: ProcessWorker,
    stop_timeout_seconds: float,
) -> dict[str, Any]:
    stop_requested_at: float | None = None

    while worker.is_alive():
        if job_manager.should_stop(job_id) and not worker.is_interrupted():
            worker.stop()
            stop_requested_at = time.monotonic()
        if stop_requested_at is not None:
            elapsed = time.monotonic() - stop_requested_at
            if elapsed >= stop_timeout_seconds:
                worker.terminate()
                break
        message = worker.poll(timeout=0.25)
        if message is not None:
            handle_training_progress(job_id, message)
            drain_worker_progress(job_id, worker)

    worker.join(timeout=5)
    drain_worker_progress(job_id, worker)

    result_payload = worker.read_result()
    if result_payload is None:
        if worker.exitcode not in (0, None) and not job_manager.should_stop(job_id):
            raise RuntimeError(
                f"Training process exited with code {worker.exitcode}"
            )
        return {}
    if "error" in result_payload and result_payload["error"]:
        raise RuntimeError(str(result_payload["error"]))
    if "result" in result_payload:
        return result_payload["result"] or {}
    return {}


###############################################################################
def run_training_job(
    configuration: dict[str, Any],
    job_id: str,
) -> dict[str, Any]:
    worker = ProcessWorker()
    training_state.worker = worker
    try:
        worker.start(
            target=run_training_process,
            kwargs={"configuration": configuration},
        )

        result = monitor_training_process(
            job_id,
            worker,
            stop_timeout_seconds=5.0,
        )
        if job_manager.should_stop(job_id):
            training_state.update_stats(
                {"status": "cancelled", "message": "Training cancelled"}
            )
        else:
            final_epoch = training_state.latest_stats.get("total_epochs", 0)
            training_state.update_stats(
                {
                    "status": "completed",
                    "message": "Training completed",
                    "epoch": final_epoch,
                }
            )
        return result
    except Exception as exc:
        training_state.update_stats({"status": "error", "message": str(exc)})
        raise
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)
        worker.cleanup()
        training_state.finish_session()


###############################################################################
def run_resume_training_job(
    checkpoint: str,
    additional_episodes: int,
    job_id: str,
) -> dict[str, Any]:
    worker = ProcessWorker()
    training_state.worker = worker
    try:
        worker.start(
            target=run_resume_training_process,
            kwargs={
                "checkpoint": checkpoint,
                "additional_episodes": additional_episodes,
            },
        )

        result = monitor_training_process(
            job_id,
            worker,
            stop_timeout_seconds=5.0,
        )
        if job_manager.should_stop(job_id):
            training_state.update_stats(
                {"status": "cancelled", "message": "Training cancelled"}
            )
        else:
            final_epoch = training_state.latest_stats.get("total_epochs", 0)
            training_state.update_stats(
                {
                    "status": "completed",
                    "message": "Resume training completed",
                    "epoch": final_epoch,
                }
            )
        return result
    except Exception as exc:
        training_state.update_stats({"status": "error", "message": str(exc)})
        raise
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)
        worker.cleanup()
        training_state.finish_session()


###############################################################################
class TrainingEndpoint:
    JOB_TYPE = "training"
    CHECKPOINT_EMPTY_MESSAGE = "Checkpoint name cannot be empty"

    def __init__(
        self,
        router: APIRouter,
        job_manager: JobManager,
        training_state: TrainingState,
    ) -> None:
        self.router = router
        self.job_manager = job_manager
        self.training_state = training_state
        self.model_serializer = ModelSerializer()

    # -------------------------------------------------------------------------
    def start_training(self, config: TrainingConfig) -> dict[str, Any]:
        if self.job_manager.is_job_running(self.JOB_TYPE):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training is already in progress.",
            )

        base_config = TrainingConfig.model_validate({}).model_dump()
        overrides = config.model_dump(exclude_unset=True)
        configuration = {**base_config, **overrides}
        checkpoint_name = configuration.get("checkpoint_name")
        if isinstance(checkpoint_name, str):
            trimmed_checkpoint_name = checkpoint_name.strip()
            configuration["checkpoint_name"] = trimmed_checkpoint_name or None
        else:
            configuration["checkpoint_name"] = None

        if configuration["checkpoint_name"]:
            checkpoint_path = os.path.join(CHECKPOINT_PATH, configuration["checkpoint_name"])
            if os.path.exists(checkpoint_path):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Checkpoint already exists: {configuration['checkpoint_name']}",
                )

        job_id = self.job_manager.start_job(
            job_type=self.JOB_TYPE,
            runner=run_training_job,
            kwargs={"configuration": configuration},
        )

        total_epochs = int(configuration.get("episodes", 10))
        max_steps = int(configuration.get("max_steps_episode", 2000))
        self.training_state.reset_for_new_session(total_epochs, max_steps, job_id)

        self.job_manager.update_result(
            job_id,
            {
                "latest_stats": self.training_state.latest_stats,
                "history": self.training_state.history_points,
            },
        )

        poll_interval = get_poll_interval_seconds(server_settings)

        return {
            "status": "started",
            "message": "Training started successfully",
            "job_id": job_id,
            "job_type": self.JOB_TYPE,
            "poll_interval": poll_interval,
        }

    # -------------------------------------------------------------------------
    def resume_training(self, config: ResumeConfig) -> dict[str, Any]:
        if self.job_manager.is_job_running(self.JOB_TYPE):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training is already in progress.",
            )

        checkpoint = config.checkpoint.strip()
        if not checkpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.CHECKPOINT_EMPTY_MESSAGE,
            )

        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint)
        if not os.path.isdir(checkpoint_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint not found: {checkpoint}",
            )

        try:
            configuration, session = self.model_serializer.load_training_configuration(checkpoint_path)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load checkpoint metadata: {exc}",
            ) from exc

        from_epoch = int(session.get("total_episodes", 0))
        initial_capital = configuration.get("initial_capital")
        initial_capital_value = (
            float(initial_capital) if isinstance(initial_capital, (int, float)) else None
        )
        restored_points = build_history_points(session, initial_capital_value)

        job_id = self.job_manager.start_job(
            job_type=self.JOB_TYPE,
            runner=run_resume_training_job,
            kwargs={
                "checkpoint": checkpoint,
                "additional_episodes": config.additional_episodes,
            },
        )

        total_epochs = from_epoch + int(config.additional_episodes)
        max_steps = int(configuration.get("max_steps_episode", 2000))
        self.training_state.reset_for_new_session(total_epochs, max_steps, job_id)
        self.training_state.history_points = restored_points
        self.training_state.latest_stats["epoch"] = from_epoch

        self.job_manager.update_result(
            job_id,
            {
                "latest_stats": self.training_state.latest_stats,
                "history": self.training_state.history_points,
            },
        )

        poll_interval = get_poll_interval_seconds(server_settings)

        return {
            "status": "started",
            "message": f"Resuming training from {checkpoint}",
            "job_id": job_id,
            "job_type": self.JOB_TYPE,
            "poll_interval": poll_interval,
        }

    # -------------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        poll_interval = get_poll_interval_seconds(server_settings)
        return {
            "job_id": self.training_state.current_job_id,
            "is_training": self.training_state.is_training,
            "latest_stats": self.training_state.latest_stats,
            "history": self.training_state.history_points,
            "latest_env": self.training_state.latest_env,
            "poll_interval": poll_interval,
        }

    # -------------------------------------------------------------------------
    def stop_training(self) -> dict[str, Any]:
        if not self.training_state.is_training:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No training is in progress.",
            )

        if self.training_state.worker is not None:
            self.training_state.worker.stop()

        if self.training_state.current_job_id:
            self.job_manager.cancel_job(self.training_state.current_job_id)

        return {"status": "stopping", "message": "Training stop requested"}

    # -------------------------------------------------------------------------
    def get_checkpoints(self) -> list[str]:
        return self.model_serializer.scan_checkpoints_folder()

    # -------------------------------------------------------------------------
    def get_checkpoint_metadata(self, checkpoint: str) -> dict[str, Any]:
        if not checkpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.CHECKPOINT_EMPTY_MESSAGE,
            )

        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint)
        if not os.path.isdir(checkpoint_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint not found: {checkpoint}",
            )

        try:
            configuration, session = self.model_serializer.load_training_configuration(
                checkpoint_path
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load checkpoint metadata: {exc}",
            ) from exc

        history = session.get("history", {}) if isinstance(session, dict) else {}

        def get_last_value(values: Any) -> float | None:
            if isinstance(values, list) and values:
                last_value = values[-1]
                if isinstance(last_value, (int, float)):
                    return float(last_value)
            return None

        summary = {
            "dataset_name": configuration.get("dataset_name") or "",
            "sample_size": configuration.get("sample_size"),
            "seed": configuration.get("seed"),
            "episodes": configuration.get("episodes") or session.get("total_episodes"),
            "batch_size": configuration.get("batch_size"),
            "learning_rate": configuration.get("learning_rate"),
            "perceptive_field_size": configuration.get("perceptive_field_size"),
            "neurons": configuration.get("QNet_neurons"),
            "embedding_dimensions": configuration.get("embedding_dimensions"),
            "exploration_rate": configuration.get("exploration_rate"),
            "exploration_rate_decay": configuration.get("exploration_rate_decay"),
            "discount_rate": configuration.get("discount_rate"),
            "model_update_frequency": configuration.get("model_update_frequency"),
            "bet_amount": configuration.get("bet_amount"),
            "initial_capital": configuration.get("initial_capital"),
            "final_loss": get_last_value(history.get("loss")),
            "final_rmse": get_last_value(history.get("metrics")),
            "final_val_loss": get_last_value(history.get("val_loss")),
            "final_val_rmse": get_last_value(history.get("val_rmse")),
        }

        return {"checkpoint": checkpoint, "summary": summary}

    # -------------------------------------------------------------------------
    def delete_checkpoint(self, checkpoint: str) -> dict[str, Any]:
        if not checkpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=self.CHECKPOINT_EMPTY_MESSAGE,
            )

        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint)
        if not os.path.isdir(checkpoint_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint not found: {checkpoint}",
            )

        try:
            import shutil
            shutil.rmtree(checkpoint_path)
            return {"status": "success", "message": f"Checkpoint {checkpoint} deleted"}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete checkpoint: {exc}",
            ) from exc

    # -------------------------------------------------------------------------
    def get_training_job_status(self, job_id: str) -> JobStatusResponse:
        job_status = self.job_manager.get_job_status(job_id)
        if job_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}",
            )
        poll_interval = get_poll_interval_seconds(server_settings)
        return JobStatusResponse(**job_status, poll_interval=poll_interval)

    # -------------------------------------------------------------------------
    def cancel_training_job(self, job_id: str) -> JobCancelResponse:
        job_status = self.job_manager.get_job_status(job_id)
        if job_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}",
            )

        if self.training_state.worker is not None:
            self.training_state.worker.stop()

        success = self.job_manager.cancel_job(job_id)

        if success:
            logger.info("Training stop requested for job %s", job_id)

        return JobCancelResponse(
            job_id=job_id,
            success=success,
            message="Cancellation requested" if success else "Job cannot be cancelled",
        )

    # -------------------------------------------------------------------------
    def add_routes(self) -> None:
        self.router.add_api_route(
            "/start",
            self.start_training,
            methods=["POST"],
            response_model=JobStartResponse,
            status_code=status.HTTP_202_ACCEPTED,
        )
        self.router.add_api_route(
            "/resume",
            self.resume_training,
            methods=["POST"],
            response_model=JobStartResponse,
            status_code=status.HTTP_202_ACCEPTED,
        )
        self.router.add_api_route(
            "/status",
            self.get_status,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/stop",
            self.stop_training,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/checkpoints",
            self.get_checkpoints,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/checkpoints/{checkpoint}/metadata",
            self.get_checkpoint_metadata,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/checkpoints/{checkpoint}",
            self.delete_checkpoint,
            methods=["DELETE"],
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/jobs/{job_id}",
            self.get_training_job_status,
            methods=["GET"],
            response_model=JobStatusResponse,
            status_code=status.HTTP_200_OK,
        )
        self.router.add_api_route(
            "/jobs/{job_id}",
            self.cancel_training_job,
            methods=["DELETE"],
            response_model=JobCancelResponse,
            status_code=status.HTTP_200_OK,
        )


###############################################################################
training_endpoint = TrainingEndpoint(
    router=router,
    job_manager=job_manager,
    training_state=training_state,
)
training_endpoint.add_routes()
