from __future__ import annotations

import os
import subprocess
import time
import webbrowser
from collections.abc import Callable
from io import BytesIO
from typing import Any

import matplotlib.pyplot as plt
from keras import Model
from keras.callbacks import Callback, ModelCheckpoint, TensorBoard

from FAIRS.app.client.workers import ProcessWorker, ThreadWorker, WorkerInterrupted
from FAIRS.app.utils.logger import logger


# [CALLBACK FOR UI PROGRESS BAR]
###############################################################################
class ProgressBarCallback(Callback):
    def __init__(
        self, progress_callback: Any, total_epochs: int, from_epoch: int = 0
    ) -> None:
        super().__init__()
        self.progress_callback = progress_callback
        self.total_epochs = total_epochs
        self.from_epoch = from_epoch

    # -------------------------------------------------------------------------
    def on_epoch_end(self, epoch, logs: dict | None = None) -> None:
        processed_epochs = epoch - self.from_epoch + 1
        additional_epochs = max(1, self.total_epochs - self.from_epoch)
        percent = int(100 * processed_epochs / additional_epochs)
        if self.progress_callback is not None:
            self.progress_callback(percent)


# [CALLBACK FOR TRAIN INTERRUPTION]
###############################################################################
class LearningInterruptCallback(Callback):
    def __init__(self, worker: ThreadWorker | ProcessWorker | None = None) -> None:
        super().__init__()
        self.model: Model
        self.worker = worker

    # -------------------------------------------------------------------------
    def on_batch_end(self, batch, logs: dict | None = None) -> None:
        if self.worker is not None and self.worker.is_interrupted():
            self.model.stop_training = True
            raise WorkerInterrupted()

    # -------------------------------------------------------------------------
    def on_validation_batch_end(self, batch, logs: dict | None = None) -> None:
        if self.worker is not None and self.worker.is_interrupted():
            raise WorkerInterrupted()


# [CALLBACK FOR REAL TIME TRAINING MONITORING]
###############################################################################
class RealTimeHistory:
    def __init__(
        self,
        plot_path: str,
        past_logs: dict | None = None,
        progress_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.fig_path = os.path.join(plot_path, "training_history.jpeg")
        self.total_epochs = 0 if past_logs is None else past_logs.get("episodes", 0)
        self.history = {"history": {}, "episodes": self.total_epochs}
        self.progress_callback = progress_callback

    # -------------------------------------------------------------------------
    def plot_loss_and_metrics(self, episode: int, logs: dict | None = None) -> None:
        if not logs or not logs.get("episode", []):
            return

        for key, value in logs.items():
            if key not in self.history["history"]:
                self.history["history"][key] = []
            self.history["history"][key].append(value[-1])
        self.history["episodes"] = episode + 1
        self.generate_plots()

    # -------------------------------------------------------------------------
    def generate_plots(self) -> None:
        loss = self.history["history"].get("loss", [])
        metric = self.history["history"].get("metrics", [])
        fig, axes = plt.subplots(2, 1, figsize=(16, 10))
        if loss:
            axes[0].plot(loss, label="train")
        axes[0].set_title("Loss")
        axes[0].set_xlabel("Episode")
        axes[0].legend(loc="best", fontsize=10)
        if metric:
            axes[1].plot(metric, label="train")
        axes[1].set_title("Metrics")
        axes[1].set_xlabel("Episode")
        axes[1].legend(loc="best", fontsize=10)
        plt.tight_layout()

        buffer = BytesIO()
        fig.savefig(buffer, bbox_inches="tight", format="jpeg", dpi=300)
        data = buffer.getvalue()
        with open(self.fig_path, "wb") as target:
            target.write(data)
        if self.progress_callback:
            self.progress_callback(
                {
                    "kind": "render",
                    "source": "train_metrics",
                    "stream": "history",
                    "data": data,
                }
            )
        plt.close(fig)


###############################################################################
###############################################################################
class GameStatsCallback:
    def __init__(
        self,
        plot_path: str,
        iterations: list[Any] | None = None,
        capitals: list[Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], Any] | None = None,
        **kwargs,
    ) -> None:
        self.plot_path = os.path.join(plot_path, "game_statistics.jpeg")
        os.makedirs(plot_path, exist_ok=True)
        self.iterations = [] if iterations is None else iterations
        self.capitals = [] if capitals is None else capitals
        self.last_episode = None
        self.episode_end_indices = []
        self.global_step = 0
        self.episode_count = 0
        self.progress_callback = progress_callback

    # -------------------------------------------------------------------------
    def plot_game_statistics(self, logs: dict | None = None) -> None:
        if not logs or not logs.get("episode", []):
            return

        current_episode = logs.get("episode", [None])[-1]
        if self.last_episode is not None and self.last_episode != current_episode:
            self.episode_end_indices.append(self.global_step)
            self.episode_count += 1

        self.global_step += 1
        if self.global_step > 0:
            self.capitals.append(logs.get("capital", [None])[-1])
            self.iterations.append(self.global_step)
            self.generate_plot(self.global_step)

        self.last_episode = current_episode

    # -------------------------------------------------------------------------
    def generate_plot(self, current_step: int) -> None:
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_xlabel("Iterations (Time Steps)")
        ax.set_ylabel("Value")
        series = ax.plot(
            self.iterations,
            self.capitals,
            color="blue",
            label="Current Capital",
            alpha=0.8,
        )
        vline_handles = []
        if self.episode_end_indices:
            first_marker = True
            for index in self.episode_end_indices:
                label = "Episode End" if first_marker else ""
                vline = ax.axvline(
                    x=index, color="grey", linestyle="--", alpha=0.6, label=label
                )
                if first_marker:
                    vline_handles.append(vline)
                    first_marker = False
        lines = series + vline_handles
        labels = [str(lin.get_label()) for lin in lines]
        ax.legend(lines, labels, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
        fig.suptitle(f"Training Progress: Capital (At step {current_step})")
        fig.tight_layout(rect=(0, 0.1, 1, 0.95))

        buffer = BytesIO()
        fig.savefig(buffer, bbox_inches="tight", format="jpeg", dpi=300)
        data = buffer.getvalue()
        with open(self.plot_path, "wb") as target:
            target.write(data)
        if self.progress_callback:
            self.progress_callback(
                {
                    "kind": "render",
                    "source": "train_metrics",
                    "stream": "game_stats",
                    "data": data,
                }
            )
        plt.close(fig)


###############################################################################
class CallbacksWrapper:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.configuration = configuration

    # -------------------------------------------------------------------------
    def get_metrics_callbacks(
        self,
        checkpoint_path: str,
        history: dict | None = None,
        progress_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> tuple[RealTimeHistory, GameStatsCallback]:
        RTH_callback = RealTimeHistory(
            checkpoint_path, past_logs=history, progress_callback=progress_callback
        )
        GS_callback = GameStatsCallback(
            checkpoint_path, progress_callback=progress_callback
        )

        return RTH_callback, GS_callback

    # -------------------------------------------------------------------------
    def get_tensorboard_callback(
        self, checkpoint_path: str, model: Model
    ) -> TensorBoard:
        logger.debug("Using tensorboard during training")
        log_path = os.path.join(checkpoint_path, "tensorboard")
        tb_callback = TensorBoard(
            log_dir=log_path,
            update_freq=20,  # type: ignore
            histogram_freq=1,
        )
        tb_callback.set_model(model)
        start_tensorboard_subprocess(log_path)

        return tb_callback

    # -------------------------------------------------------------------------
    def checkpoints_saving(self, checkpoint_path: str) -> ModelCheckpoint:
        checkpoint_filepath = os.path.join(checkpoint_path, "model_checkpoint.keras")
        chkp_save = ModelCheckpoint(
            filepath=checkpoint_filepath,
            save_weights_only=True,
            monitor="loss",
            save_best_only=True,
            mode="auto",
            verbose=1,
        )

        return chkp_save


###############################################################################
def start_tensorboard_subprocess(log_dir: str) -> None:
    tensorboard_command = ["tensorboard", "--logdir", log_dir, "--port", "6006"]
    subprocess.Popen(
        tensorboard_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(4)
    webbrowser.open("http://localhost:6006")
