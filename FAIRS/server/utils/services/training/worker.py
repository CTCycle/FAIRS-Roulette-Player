from __future__ import annotations

import asyncio
import functools
import multiprocessing
import os
import queue
import signal
import subprocess
import time
from typing import Any

from collections.abc import Callable

from FAIRS.server.utils.logger import logger
from FAIRS.server.utils.services.training.device import DeviceConfig
from FAIRS.server.utils.services.training.fitting import DQNTraining
from FAIRS.server.utils.services.training.models.qnet import FAIRSnet
from FAIRS.server.utils.services.training.serializer import DataSerializerExtension, ModelSerializer


###############################################################################
class QueueProgressReporter:
    def __init__(self, target_queue: Any) -> None:
        self.target_queue = target_queue

    # -------------------------------------------------------------------------
    def drain_queue(self) -> None:
        while True:
            try:
                self.target_queue.get_nowait()
            except queue.Empty:
                return
            except Exception:
                return

    # -------------------------------------------------------------------------
    def __call__(self, message: dict[str, Any]) -> None:
        try:
            if message.get("type") == "training_update":
                self.drain_queue()
            self.target_queue.put(message, block=False)
        except queue.Full:
            return
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to push training update: %s", exc)


###############################################################################
class WorkerChannels:
    def __init__(
        self,
        progress_queue: Any,
        result_queue: Any,
        stop_event: Any,
    ) -> None:
        self.progress_queue = progress_queue
        self.result_queue = result_queue
        self.stop_event = stop_event

    # -------------------------------------------------------------------------
    def is_interrupted(self) -> bool:
        return bool(self.stop_event.is_set())


###############################################################################
class ProcessWorker:
    def __init__(
        self,
        progress_queue_size: int = 256,
        result_queue_size: int = 8,
    ) -> None:
        self.ctx = multiprocessing.get_context("spawn")
        self.progress_queue = self.ctx.Queue(maxsize=progress_queue_size)
        self.result_queue = self.ctx.Queue(maxsize=result_queue_size)
        self.stop_event = self.ctx.Event()
        self.process: multiprocessing.Process | None = None

    # -------------------------------------------------------------------------
    def start(
        self,
        target: Callable[..., None],
        kwargs: dict[str, Any],
    ) -> None:
        if self.process is not None and self.process.is_alive():
            raise RuntimeError("Worker process is already running")
        self.process = self.ctx.Process(
            target=process_target,
            kwargs={
                "target": target,
                "kwargs": kwargs,
                "worker": self.as_child(),
            },
            daemon=False,
        )
        self.process.start()

    # -------------------------------------------------------------------------
    def stop(self) -> None:
        self.stop_event.set()

    # -------------------------------------------------------------------------
    def interrupt(self) -> None:
        self.stop_event.set()

    # -------------------------------------------------------------------------
    def is_interrupted(self) -> bool:
        return bool(self.stop_event.is_set())

    # -------------------------------------------------------------------------
    def is_alive(self) -> bool:
        return bool(self.process is not None and self.process.is_alive())

    # -------------------------------------------------------------------------
    def join(self, timeout: float | None = None) -> None:
        if self.process is None:
            return
        self.process.join(timeout=timeout)

    # -------------------------------------------------------------------------
    def terminate(self) -> None:
        if self.process is None:
            return
        self.terminate_process_tree(self.process)

    # -------------------------------------------------------------------------
    def poll(self, timeout: float = 0.25) -> dict[str, Any] | None:
        try:
            message = self.progress_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        except (EOFError, OSError):
            return None
        if isinstance(message, dict):
            return message
        return None

    # -------------------------------------------------------------------------
    def drain_progress(self) -> None:
        while True:
            try:
                self.progress_queue.get_nowait()
            except queue.Empty:
                return
            except (EOFError, OSError):
                return

    # -------------------------------------------------------------------------
    def read_result(self) -> dict[str, Any] | None:
        try:
            payload = self.result_queue.get_nowait()
        except queue.Empty:
            return None
        except (EOFError, OSError):
            return None
        if isinstance(payload, dict):
            return payload
        return None

    # -------------------------------------------------------------------------
    def cleanup(self) -> None:
        self.progress_queue.close()
        self.result_queue.close()
        self.progress_queue.join_thread()
        self.result_queue.join_thread()

    # -------------------------------------------------------------------------
    def as_child(self) -> WorkerChannels:
        return WorkerChannels(
            progress_queue=self.progress_queue,
            result_queue=self.result_queue,
            stop_event=self.stop_event,
        )

    # -------------------------------------------------------------------------
    def terminate_process_tree(self, process: multiprocessing.Process) -> None:
        pid = process.pid
        if pid is None:
            return
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", f"taskkill /PID {pid} /T /F"],
                check=False,
                capture_output=True,
            )
            return
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(1)
            if process.is_alive():
                os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return

    # -------------------------------------------------------------------------
    @property
    def exitcode(self) -> int | None:
        if self.process is None:
            return None
        return self.process.exitcode


###############################################################################
def process_target(
    target: Callable[..., None],
    kwargs: dict[str, Any],
    worker: WorkerChannels,
) -> None:
    if os.name != "nt":
        os.setsid()
    target(worker=worker, **kwargs)


###############################################################################
async def queue_training_update(
    stats: dict[str, Any],
    reporter: QueueProgressReporter,
) -> None:
    payload = {"type": "training_update", **stats}
    reporter(payload)


###############################################################################
async def run_training_async(
    configuration: dict[str, Any],
    reporter: QueueProgressReporter,
    stop_event: Any,
) -> tuple[Any, dict[str, Any], str]:
    data_serializer = DataSerializerExtension()
    dataset, synthetic = data_serializer.get_training_series(configuration)
    if synthetic:
        logger.info("Synthetic roulette series generated (%s extractions)", len(dataset))
    else:
        logger.info("Roulette series has been loaded (%s extractions)", len(dataset))

    logger.info("Setting device for training operations")
    device = DeviceConfig(configuration)
    device.set_device()

    model_serializer = ModelSerializer()
    checkpoint_path = model_serializer.create_checkpoint_folder()

    logger.info("Building FAIRS reinforcement learning model")
    learner = FAIRSnet(configuration)
    q_model = learner.get_model(model_summary=True)
    target_model = learner.get_model(model_summary=False)

    trainer = DQNTraining(configuration, stop_event=stop_event)
    progress_callback = functools.partial(queue_training_update, reporter=reporter)

    model, history = await trainer.train_model(
        q_model,
        target_model,
        dataset,
        checkpoint_path,
        ws_callback=progress_callback,
        ws_env_callback=None,
    )

    return model, history, checkpoint_path


###############################################################################
async def run_resume_training_async(
    checkpoint: str,
    additional_episodes: int,
    reporter: QueueProgressReporter,
    stop_event: Any,
) -> tuple[Any, dict[str, Any], dict[str, Any], str]:
    model_serializer = ModelSerializer()
    model, train_config, session, checkpoint_path = model_serializer.load_checkpoint(
        checkpoint
    )
    train_config["additional_episodes"] = additional_episodes

    data_serializer = DataSerializerExtension()
    dataset, synthetic = data_serializer.get_training_series(train_config)
    if synthetic:
        logger.info("Synthetic roulette series generated (%s extractions)", len(dataset))
    else:
        logger.info("Roulette series has been loaded (%s extractions)", len(dataset))

    logger.info("Setting device for training operations")
    device = DeviceConfig(train_config)
    device.set_device()

    trainer = DQNTraining(train_config, session=session, stop_event=stop_event)
    progress_callback = functools.partial(queue_training_update, reporter=reporter)

    model, history = await trainer.resume_training(
        model,
        model,
        dataset,
        checkpoint_path,
        session,
        additional_episodes,
        ws_callback=progress_callback,
        ws_env_callback=None,
    )

    return model, history, train_config, checkpoint_path


###############################################################################
def run_training_process(
    configuration: dict[str, Any],
    worker: Any,
) -> None:
    progress_queue = worker.progress_queue
    result_queue = worker.result_queue
    stop_event = worker.stop_event
    reporter = QueueProgressReporter(progress_queue)

    try:
        if stop_event.is_set():
            result_queue.put({"result": {}})
            return

        model, history, checkpoint_path = asyncio.run(
            run_training_async(configuration, reporter, stop_event)
        )

        model_serializer = ModelSerializer()
        model_serializer.save_pretrained_model(model, checkpoint_path)
        model_serializer.save_training_configuration(
            checkpoint_path, history, configuration
        )

        history_payload = history.get("history", {}) if isinstance(history, dict) else {}
        result_queue.put(
            {
                "result": {
                    "checkpoint_path": checkpoint_path,
                    "final_loss": history_payload.get("loss", [0])[-1]
                    if history_payload.get("loss")
                    else 0.0,
                    "final_rmse": history_payload.get("metrics", [0])[-1]
                    if history_payload.get("metrics")
                    else 0.0,
                }
            }
        )
    except Exception as exc:  # noqa: BLE001
        result_queue.put({"error": str(exc)})


###############################################################################
def run_resume_training_process(
    checkpoint: str,
    additional_episodes: int,
    worker: Any,
) -> None:
    progress_queue = worker.progress_queue
    result_queue = worker.result_queue
    stop_event = worker.stop_event
    reporter = QueueProgressReporter(progress_queue)

    try:
        if stop_event.is_set():
            result_queue.put({"result": {}})
            return

        model, history, train_config, checkpoint_path = asyncio.run(
            run_resume_training_async(
                checkpoint, additional_episodes, reporter, stop_event
            )
        )

        model_serializer = ModelSerializer()
        model_serializer.save_pretrained_model(model, checkpoint_path)
        model_serializer.save_training_configuration(
            checkpoint_path, history, train_config
        )

        history_payload = history.get("history", {}) if isinstance(history, dict) else {}
        result_queue.put(
            {
                "result": {
                    "checkpoint_path": checkpoint_path,
                    "final_loss": history_payload.get("loss", [0])[-1]
                    if history_payload.get("loss")
                    else 0.0,
                    "final_rmse": history_payload.get("metrics", [0])[-1]
                    if history_payload.get("metrics")
                    else 0.0,
                }
            }
        )
    except Exception as exc:  # noqa: BLE001
        result_queue.put({"error": str(exc)})
