from __future__ import annotations

import inspect
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from server.common.utils.logger import logger
from server.common.utils.trainingstats import (
    coerce_optional_finite_float,
    sanitize_training_stats,
)
from server.common.utils.types import coerce_finite_float, coerce_finite_int

TRAINING_STATUSES = {
    "idle",
    "exploration",
    "training",
    "stopping",
    "completed",
    "error",
    "cancelled",
}
ACTIVE_RUN_STATUSES = {"pending", "running", "stopping"}
HISTORY_POINTS_PER_EPISODE = 20


###############################################################################
def default_training_stats(
    total_epochs: int = 0,
    max_steps: int = 0,
    status: str = "idle",
) -> dict[str, Any]:
    return {
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
        "current_bet_amount": None,
        "current_strategy_id": None,
        "epsilon": None,
        "experience_count": 0,
        "replay_buffer_size": 0,
        "status": status,
    }


###############################################################################
@dataclass
class TrainingRun:
    job_id: str
    job_type: str
    status: str = "pending"
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=monotonic)
    completed_at: float | None = None
    stop_requested: bool = False
    latest_stats: dict[str, Any] = field(default_factory=default_training_stats)
    history_points: list[dict[str, Any]] = field(default_factory=list)
    latest_env: dict[str, Any] = field(default_factory=dict)
    max_history_points: int = 2000
    history_bucket_size: float = 1.0
    last_history_episode: int | None = None
    last_history_bucket: int | None = None
    worker: Any | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # -------------------------------------------------------------------------
    def update(self, **kwargs: Any) -> None:
        with self.lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    # -------------------------------------------------------------------------
    def update_status(self, status: str, **kwargs: Any) -> None:
        self.update(status=status, **kwargs)

    # -------------------------------------------------------------------------
    def reset_training_state(
        self,
        total_epochs: int,
        max_steps: int,
    ) -> None:
        with self.lock:
            self.latest_stats = default_training_stats(
                total_epochs,
                max_steps,
                "exploration",
            )
            self.history_points = []
            self.history_bucket_size = (
                max_steps / float(HISTORY_POINTS_PER_EPISODE) if max_steps > 0 else 1.0
            )
            self.last_history_episode = None
            self.last_history_bucket = None
            self.latest_env = {}

    # -------------------------------------------------------------------------
    def restore_history(
        self,
        history_points: list[dict[str, Any]],
        from_epoch: int,
    ) -> None:
        with self.lock:
            self.history_points = history_points[-self.max_history_points :]
            self.latest_stats["epoch"] = from_epoch

    # -------------------------------------------------------------------------
    def update_stats(self, stats: dict[str, Any]) -> None:
        sanitized = sanitize_training_stats(
            stats,
            allowed_statuses=TRAINING_STATUSES,
        )
        with self.lock:
            self.latest_stats = {**self.latest_stats, **sanitized}
            self._add_history_point(self.latest_stats)

    # -------------------------------------------------------------------------
    def _add_history_point(self, stats: dict[str, Any]) -> None:
        if stats.get("status") not in {"training", "exploration"}:
            return
        time_step = stats.get("time_step")
        loss = coerce_optional_finite_float(stats.get("loss"))
        rmse = coerce_optional_finite_float(stats.get("rmse"))
        epoch = stats.get("epoch")
        if not isinstance(time_step, int) or not isinstance(epoch, int) or epoch <= 0:
            return
        point = {
            "time_step": time_step,
            "loss": loss if loss is not None else 0.0,
            "rmse": rmse if rmse is not None else 0.0,
            "val_loss": coerce_optional_finite_float(stats.get("val_loss")),
            "val_rmse": coerce_optional_finite_float(stats.get("val_rmse")),
            "val_reward": coerce_optional_finite_float(stats.get("val_reward")),
            "epsilon": coerce_optional_finite_float(stats.get("epsilon")),
            "experience_count": coerce_finite_int(
                stats.get("experience_count"), 0, minimum=0
            ),
            "replay_buffer_size": coerce_finite_int(
                stats.get("replay_buffer_size"), 0, minimum=0
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
            if isinstance(previous_epoch, int) and isinstance(previous_step, int):
                if point["epoch"] < previous_epoch:
                    return
                if (
                    point["epoch"] == previous_epoch
                    and point["time_step"] < previous_step
                ):
                    return

        self.history_points.append(point)
        if len(self.history_points) > self.max_history_points:
            self.history_points = self.history_points[-self.max_history_points :]

    # -------------------------------------------------------------------------
    def job_snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "job_id": self.job_id,
                "job_type": self.job_type,
                "status": self.status,
                "progress": self.progress,
                "result": self.result,
                "error": self.error,
                "created_at": self.created_at,
                "completed_at": self.completed_at,
            }


###############################################################################
class TrainingRunManager:
    """Own training jobs, process handles, progress, and the status projection."""

    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self.runs: dict[str, TrainingRun] = {}
        self.threads: dict[str, threading.Thread] = {}
        self.lock = threading.RLock()
        self.last_training_run: TrainingRun | None = None
        self._shutdown_started = False
        self._shutdown_complete = False

    # -------------------------------------------------------------------------
    def start_job(
        self,
        job_type: str,
        runner: Callable[..., dict[str, Any]],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        initializer: Callable[[TrainingRun], None] | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())[:8]
        run = TrainingRun(job_id=job_id, job_type=job_type)
        runner_kwargs = kwargs.copy() if kwargs else {}
        if self.runner_accepts_job_id(runner):
            runner_kwargs["job_id"] = job_id

        with self.lock:
            if self._shutdown_started:
                raise RuntimeError("Training manager is shutting down.")
            if any(existing.status in ACTIVE_RUN_STATUSES for existing in self.runs.values()):
                raise RuntimeError("Training is already in progress.")
            self.runs[job_id] = run
            self.last_training_run = run

        thread = threading.Thread(
            target=self.run_job,
            args=(job_id, runner, args, runner_kwargs),
            daemon=True,
            name=f"fairs-training-{job_id}",
        )
        with self.lock:
            self.threads[job_id] = thread

        if initializer is not None:
            try:
                initializer(run)
            except Exception:
                with self.lock:
                    self.runs.pop(job_id, None)
                    self.threads.pop(job_id, None)
                    if self.last_training_run is run:
                        self.last_training_run = next(iter(self.runs.values()), None)
                raise

        with self.lock:
            if self._shutdown_started:
                self.runs.pop(job_id, None)
                self.threads.pop(job_id, None)
                if self.last_training_run is run:
                    self.last_training_run = next(iter(self.runs.values()), None)
                raise RuntimeError("Training manager is shutting down.")
            run.update_status("running")
            self._prune_terminal_runs_locked()
            thread.start()
        logger.info("Started training run %s (type=%s)", job_id, job_type)
        return job_id

    # -------------------------------------------------------------------------
    def reset_training_state(
        self, job_id: str, total_epochs: int, max_steps: int
    ) -> None:
        run = self._get_run(job_id)
        if run is not None:
            run.reset_training_state(total_epochs, max_steps)

    # -------------------------------------------------------------------------
    def restore_training_history(
        self,
        job_id: str,
        history_points: list[dict[str, Any]],
        from_epoch: int,
    ) -> None:
        run = self._get_run(job_id)
        if run is not None:
            run.restore_history(history_points, from_epoch)

    # -------------------------------------------------------------------------
    def update_training_stats(self, job_id: str, stats: dict[str, Any]) -> None:
        run = self._get_run(job_id)
        if run is not None:
            with run.lock:
                stop_requested = run.stop_requested
            if stop_requested and stats.get("status") in {"exploration", "training"}:
                stats = {
                    **stats,
                    "status": "stopping",
                    "message": "Training stop requested",
                }
            run.update_stats(stats)

    # -------------------------------------------------------------------------
    def training_status(self, polling_interval: float) -> dict[str, Any]:
        with self.lock:
            run = self.last_training_run
        if run is None:
            return {
                "job_id": None,
                "is_training": False,
                "latest_stats": default_training_stats(),
                "history": [],
                "latest_env": {},
                "poll_interval": polling_interval,
            }
        with run.lock:
            active = run.status in ACTIVE_RUN_STATUSES
            return {
                "job_id": run.job_id if active else None,
                "is_training": active,
                "latest_stats": dict(run.latest_stats),
                "history": list(run.history_points),
                "latest_env": dict(run.latest_env),
                "poll_interval": polling_interval,
            }

    # -------------------------------------------------------------------------
    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        run = self._get_run(job_id)
        return None if run is None else run.job_snapshot()

    # -------------------------------------------------------------------------
    def cancel_job(self, job_id: str) -> bool:
        return self.request_stop(job_id)

    # -------------------------------------------------------------------------
    def request_stop(self, job_id: str) -> bool:
        run = self._get_run(job_id)
        if run is None:
            return False
        with run.lock:
            if run.status not in ACTIVE_RUN_STATUSES:
                return False
            run.stop_requested = True
            run.status = "stopping"
            run.latest_stats = {
                **run.latest_stats,
                "status": "stopping",
                "message": "Training stop requested",
            }
            worker = run.worker
        if worker is not None:
            worker.stop()
        logger.info("Stop requested for training run %s", job_id)
        return True

    # -------------------------------------------------------------------------
    def is_job_running(self, job_type: str | None = None) -> bool:
        with self.lock:
            runs = list(self.runs.values())
        return any(
            run.status in ACTIVE_RUN_STATUSES
            and (job_type is None or run.job_type == job_type)
            for run in runs
        )

    # -------------------------------------------------------------------------
    def should_stop(self, job_id: str) -> bool:
        run = self._get_run(job_id)
        return True if run is None else run.stop_requested

    # -------------------------------------------------------------------------
    def update_progress(self, job_id: str, progress: float) -> None:
        run = self._get_run(job_id)
        if run is not None:
            with run.lock:
                run.progress = min(100.0, max(0.0, progress))

    # -------------------------------------------------------------------------
    def update_result(self, job_id: str, patch: dict[str, Any]) -> None:
        run = self._get_run(job_id)
        if run is not None:
            with run.lock:
                run.result = {**(run.result or {}), **patch}

    # -------------------------------------------------------------------------
    def set_worker(self, job_id: str, worker: Any | None) -> None:
        run = self._get_run(job_id)
        if run is not None:
            with self.lock:
                shutdown_started = self._shutdown_started
            with run.lock:
                run.worker = worker
                should_stop = worker is not None and (
                    shutdown_started or run.stop_requested
                )
            if should_stop:
                try:
                    worker.stop()
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Failed to signal late-created training worker %s", job_id
                    )

    # -------------------------------------------------------------------------
    def get_worker(self, job_id: str) -> Any | None:
        run = self._get_run(job_id)
        if run is None:
            return None
        with run.lock:
            return run.worker

    # -------------------------------------------------------------------------
    def run_job(
        self,
        job_id: str,
        runner: Callable[..., dict[str, Any]],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        run = self._get_run(job_id)
        if run is None:
            return
        try:
            result = runner(*args, **kwargs)
            with run.lock:
                stopped = run.stop_requested
            if stopped:
                run.update_status("cancelled", completed_at=monotonic())
            else:
                run.update(
                    status="completed",
                    result={**(run.result or {}), **(result or {})} or None,
                    progress=100.0,
                    completed_at=monotonic(),
                )
                logger.info("Training run %s completed successfully", job_id)
        except Exception as exc:  # noqa: BLE001
            with run.lock:
                stopped = run.stop_requested
            if stopped:
                run.update_status("cancelled", completed_at=monotonic())
                logger.info("Training run %s cancelled during execution", job_id)
                return
            error_msg = str(exc).split("\n")[0][:200]
            run.update(status="failed", error=error_msg, completed_at=monotonic())
            logger.error("Training run %s failed: %s", job_id, error_msg)
            logger.debug("Training run %s error details", job_id, exc_info=True)
        finally:
            with self.lock:
                current_thread = self.threads.get(job_id)
                if (
                    current_thread is threading.current_thread()
                    and self.last_training_run is not run
                ):
                    self.threads.pop(job_id, None)
                self._prune_terminal_runs_locked()

    # -------------------------------------------------------------------------
    def _get_run(self, job_id: str) -> TrainingRun | None:
        with self.lock:
            return self.runs.get(job_id)

    # -------------------------------------------------------------------------
    def _prune_terminal_runs_locked(self) -> None:
        retained = self.last_training_run
        for job_id, run in list(self.runs.items()):
            if run is retained:
                continue
            with run.lock:
                terminal = run.status not in ACTIVE_RUN_STATUSES
            thread = self.threads.get(job_id)
            if terminal and (thread is None or not thread.is_alive()):
                self.runs.pop(job_id, None)
                self.threads.pop(job_id, None)

    # -------------------------------------------------------------------------
    def shutdown(self, timeout_seconds: float = 10.0) -> bool:
        """Stop all runs and wait for their job threads and workers to exit."""
        with self.lock:
            if self._shutdown_complete:
                return True
            self._shutdown_started = True
            runs = list(self.runs.values())

        for run in runs:
            with run.lock:
                if run.status in ACTIVE_RUN_STATUSES:
                    run.stop_requested = True
                    run.status = "stopping"
                    run.latest_stats = {
                        **run.latest_stats,
                        "status": "stopping",
                        "message": "Application shutdown requested",
                    }
                worker = run.worker
            if worker is not None:
                try:
                    worker.stop()
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to signal training worker %s", run.job_id)

        deadline = monotonic() + max(0.1, timeout_seconds)
        with self.lock:
            threads = list(self.threads.values())
        for thread in threads:
            remaining = max(0.0, deadline - monotonic())
            if remaining <= 0:
                break
            thread.join(timeout=remaining)

        for run in runs:
            worker = self.get_worker(run.job_id)
            if worker is None:
                continue
            try:
                if worker.is_alive():
                    worker.terminate()
                    join_worker = getattr(worker, "join", None)
                    if callable(join_worker):
                        join_worker(timeout=min(1.0, max(0.1, timeout_seconds)))
            except Exception:  # noqa: BLE001
                logger.exception("Failed to terminate training worker %s", run.job_id)

        force_join_deadline = monotonic() + min(1.0, max(0.1, timeout_seconds))
        for thread in threads:
            if thread.is_alive():
                remaining = max(0.0, force_join_deadline - monotonic())
                thread.join(timeout=remaining)

        with self.lock:
            alive_threads = [thread.name for thread in self.threads.values() if thread.is_alive()]
            alive_workers = []
            for run in self.runs.values():
                worker = run.worker
                if worker is not None:
                    try:
                        if worker.is_alive():
                            alive_workers.append(run.job_id)
                    except Exception:  # noqa: BLE001
                        alive_workers.append(run.job_id)
            self._prune_terminal_runs_locked()
            complete = not alive_threads and not alive_workers
            self._shutdown_complete = complete

        if not complete:
            logger.error(
                "Training shutdown deadline exceeded; threads=%s workers=%s",
                alive_threads,
                alive_workers,
            )
        return complete

    # -------------------------------------------------------------------------
    @staticmethod
    def runner_accepts_job_id(runner: Callable[..., dict[str, Any]]) -> bool:
        try:
            signature = inspect.signature(runner)
        except (TypeError, ValueError):
            return False
        return (
            any(
                parameter.kind == parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
            or "job_id" in signature.parameters
        )


__all__ = [
    "HISTORY_POINTS_PER_EPISODE",
    "TrainingRunManager",
    "default_training_stats",
]
