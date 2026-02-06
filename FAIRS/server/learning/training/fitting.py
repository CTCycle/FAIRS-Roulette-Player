from __future__ import annotations

import base64
import asyncio
import math
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.server.configurations import server_settings
from FAIRS.server.configurations.server import get_poll_interval_seconds
from FAIRS.server.utils.logger import logger
from FAIRS.server.utils.types import coerce_finite_float, coerce_finite_int
from FAIRS.server.learning.training.agents import DQNAgent
from FAIRS.server.learning.training.environment import RouletteEnvironment

HISTORY_POINTS_PER_EPISODE = 20


###############################################################################
def sanitize_training_stats(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        **stats,
        "epoch": coerce_finite_int(stats.get("epoch"), 0, minimum=0),
        "total_epochs": coerce_finite_int(stats.get("total_epochs"), 0, minimum=0),
        "max_steps": coerce_finite_int(stats.get("max_steps"), 0, minimum=0),
        "time_step": coerce_finite_int(stats.get("time_step"), 0, minimum=0),
        "loss": coerce_finite_float(stats.get("loss"), 0.0),
        "rmse": coerce_finite_float(stats.get("rmse"), 0.0),
        "val_loss": coerce_finite_float(stats.get("val_loss"), 0.0),
        "val_rmse": coerce_finite_float(stats.get("val_rmse"), 0.0),
        "reward": coerce_finite_float(stats.get("reward"), 0.0),
        "val_reward": coerce_finite_float(stats.get("val_reward"), 0.0),
        "total_reward": coerce_finite_float(stats.get("total_reward"), 0.0),
        "capital": coerce_finite_float(stats.get("capital"), 0.0),
        "capital_gain": coerce_finite_float(stats.get("capital_gain"), 0.0),
    }


###############################################################################
def has_non_finite_numbers(stats: dict[str, Any], keys: list[str]) -> bool:
    for key in keys:
        value = stats.get(key)
        if isinstance(value, bool):
            continue
        if not isinstance(value, (int, float)):
            return True
        if not math.isfinite(float(value)):
            return True
    return False


###############################################################################
class DQNTraining:
    def __init__(
        self,
        configuration: dict[str, Any],
        session: dict | None = None,
        stop_event: Any | None = None,
    ) -> None:
        set_random_seed(configuration.get("training_seed", 42))
        self.batch_size = configuration.get("batch_size", 32)
        self.update_frequency = configuration.get("model_update_frequency", 10)
        self.replay_size = configuration.get("replay_buffer_size", 1000)
        use_gpu = configuration.get("use_device_gpu", False)
        self.selected_device = "cuda" if use_gpu else "cpu"
        self.device_id = configuration.get("device_id", 0)
        self.mixed_precision = configuration.get("use_mixed_precision", False)
        self.render_environment = False
        self.configuration = configuration
        self.max_steps = int(configuration.get("max_steps_episode", 2000))
        self.history_bucket_size = (
            self.max_steps / float(HISTORY_POINTS_PER_EPISODE)
            if self.max_steps > 0
            else 1.0
        )
        self.last_history_episode: int | None = None
        self.last_history_bucket: int | None = None
        self.last_progress_episode: int | None = None
        self.last_progress_bucket: int | None = None

        self.agent = DQNAgent(configuration)

        # Restore session_stats from checkpoint if provided (for resume training)
        if session and "history" in session:
            prev_history = session["history"]
            self.session_stats = {
                "episode": list(prev_history.get("episode", [])),
                "time_step": list(prev_history.get("time_step", [])),
                "loss": list(prev_history.get("loss", [])),
                "metrics": list(prev_history.get("metrics", [])),
                "img_reward": list(prev_history.get("img_reward", [])),
                "val_loss": list(prev_history.get("val_loss", [])),
                "val_rmse": list(prev_history.get("val_rmse", [])),
                "reward": list(prev_history.get("reward", [])),
                "total_reward": list(prev_history.get("total_reward", [])),
                "capital": list(prev_history.get("capital", [])),
            }
        else:
            self.session_stats = {
                "episode": [],
                "time_step": [],
                "loss": [],
                "metrics": [],
                "img_reward": [],  # validation reward
                "val_loss": [],
                "val_rmse": [],
                "reward": [],
                "total_reward": [],
                "capital": [],
            }

        # Progress update related
        self.polling_interval_ms = int(get_poll_interval_seconds(server_settings) * 1000)
        self.last_ws_update_time = 0.0
        self.is_cancelled = False
        self.stop_event = stop_event

    # -------------------------------------------------------------------------
    def maybe_send_environment_update(
        self,
        ws_env_callback: Callable[[dict[str, Any]], Any] | None,
        environment: RouletteEnvironment,
        episode: int,
        time_step: int,
        action: int,
        extraction: int,
        reward: int | float,
        total_reward: int | float,
        capital: int | float,
    ) -> None:
        if not ws_env_callback or not self.render_environment:
            return

        try:
            image_bytes = environment.render_frame(episode, time_step, action, extraction)
            ws_env_callback({
                "episode": episode + 1,
                "time_step": time_step,
                "action": int(action),
                "extraction": int(extraction),
                "reward": reward,
                "total_reward": total_reward,
                "capital": capital,
                "image_base64": base64.b64encode(image_bytes).decode("ascii"),
                "image_mime": "image/png",
            })
        except Exception:
            pass

    # -------------------------------------------------------------------------
    def update_session_stats(
        self,
        scores: dict,
        val_scores: dict | None,
        episode: int,
        time_step: int,
        reward: int | float,
        total_reward: int | float,
        capital: int | float,
    ) -> None:
        bucket_size = self.history_bucket_size if self.history_bucket_size > 0 else 1.0
        bucket = int(time_step / bucket_size)
        if self.max_steps >= HISTORY_POINTS_PER_EPISODE:
            bucket = min(HISTORY_POINTS_PER_EPISODE - 1, bucket)
        if self.last_history_episode != episode:
            self.last_history_episode = episode
            self.last_history_bucket = None
        if self.last_history_bucket == bucket:
            return
        self.last_history_bucket = bucket

        loss = scores.get("loss", None)
        metric = scores.get("root_mean_squared_error", None)
        self.session_stats["episode"].append(episode + 1)
        self.session_stats["time_step"].append(coerce_finite_int(time_step))
        self.session_stats["loss"].append(coerce_finite_float(loss))
        self.session_stats["metrics"].append(coerce_finite_float(metric))
        self.session_stats["reward"].append(coerce_finite_float(reward))
        self.session_stats["total_reward"].append(coerce_finite_float(total_reward))
        self.session_stats["capital"].append(coerce_finite_float(capital))

        if val_scores:
            self.session_stats["val_loss"].append(coerce_finite_float(val_scores.get("loss", 0.0)))
            self.session_stats["val_rmse"].append(coerce_finite_float(val_scores.get("root_mean_squared_error", 0.0)))
            self.session_stats["img_reward"].append(coerce_finite_float(val_scores.get("reward", 0.0)))
        else:
            # Carry forward last value or 0.0
            last_val_loss = self.session_stats["val_loss"][-1] if self.session_stats["val_loss"] else 0.0
            last_val_rmse = self.session_stats["val_rmse"][-1] if self.session_stats["val_rmse"] else 0.0
            last_val_reward = self.session_stats["img_reward"][-1] if self.session_stats["img_reward"] else 0.0
            self.session_stats["val_loss"].append(last_val_loss)
            self.session_stats["val_rmse"].append(last_val_rmse)
            self.session_stats["img_reward"].append(last_val_reward)

    # -------------------------------------------------------------------------
    def get_latest_stats(
        self,
        episode: int,
        total_episodes: int,
        training_ready: bool,
    ) -> dict[str, Any]:
        initial_capital = self.configuration.get("initial_capital", 0.0)
        initial_capital_value = (
            float(initial_capital) if isinstance(initial_capital, (int, float)) else 0.0
        )
        max_steps = int(self.configuration.get("max_steps_episode", 2000))
        if not self.session_stats["loss"]:
            raw_stats = {
                "epoch": episode + 1,
                "total_epochs": total_episodes,
                "max_steps": max_steps,
                "time_step": 0,
                "loss": 0.0,
                "rmse": 0.0,
                "reward": 0,
                "total_reward": 0,
                "capital": 0,
                "capital_gain": 0.0,
                "status": "training" if training_ready else "exploration",
            }
            return sanitize_training_stats(raw_stats)
        capital_value = self.session_stats["capital"][-1]
        raw_stats = {
            "epoch": episode + 1,
            "total_epochs": total_episodes,
            "max_steps": max_steps,
            "time_step": self.session_stats["time_step"][-1],
            "loss": self.session_stats["loss"][-1],
            "rmse": self.session_stats["metrics"][-1],
            "val_loss": self.session_stats["val_loss"][-1] if self.session_stats["val_loss"] else 0.0,
            "val_rmse": self.session_stats["val_rmse"][-1] if self.session_stats["val_rmse"] else 0.0,
            "reward": self.session_stats["reward"][-1],
            "val_reward": self.session_stats["img_reward"][-1] if self.session_stats["img_reward"] else 0.0,
            "total_reward": self.session_stats["total_reward"][-1],
            "capital": capital_value,
            "capital_gain": float(capital_value) - initial_capital_value,
            "status": "training" if training_ready else "exploration",
        }
        if has_non_finite_numbers(raw_stats, [
            "time_step",
            "loss",
            "rmse",
            "val_loss",
            "val_rmse",
            "reward",
            "total_reward",
            "capital",
            "capital_gain",
        ]):
            logger.warning("Invalid training metrics detected; sanitizing update payload.")
        return sanitize_training_stats(raw_stats)

    # -------------------------------------------------------------------------
    def should_send_ws_update(self) -> bool:
        current_time = time.time() * 1000
        if current_time - self.last_ws_update_time >= self.polling_interval_ms:
            self.last_ws_update_time = current_time
            return True
        return False

    # -------------------------------------------------------------------------
    def cancel_training(self) -> None:
        self.is_cancelled = True

    # -------------------------------------------------------------------------
    def should_stop(self) -> bool:
        if self.is_cancelled:
            return True
        if self.stop_event is not None and self.stop_event.is_set():
            return True
        return False

    # -------------------------------------------------------------------------
    def _run_validation(
        self,
        model: Model,
        target_model: Model,
        val_env: RouletteEnvironment,
        state_size: int,
        steps: int = 100,
    ) -> dict[str, float]:
        val_state = val_env.reset()
        val_state = np.reshape(val_state, shape=(1, state_size))
        val_total_reward = 0
        val_memory = deque(maxlen=steps + 10)

        for _ in range(steps):
            gain = val_env.capital / val_env.initial_capital
            gain = np.reshape(gain, shape=(1, 1))

            # Greedy action
            old_eps = self.agent.epsilon
            self.agent.epsilon = 0.0
            action = self.agent.act(model, val_state, gain)
            self.agent.epsilon = old_eps

            next_state, reward, done, _ = val_env.step(action)
            val_total_reward += reward
            next_state = np.reshape(next_state, [1, state_size])

            next_gain = val_env.capital / val_env.initial_capital
            next_gain = np.reshape(next_gain, shape=(1, 1))

            val_memory.append(
                (val_state, action, reward, gain, next_gain, next_state, done)
            )
            val_state = next_state

            if done:
                val_state = val_env.reset()
                val_state = np.reshape(val_state, shape=(1, state_size))

        # Evaluate batch
        val_metrics = self.agent.evaluate_batch(
            model, target_model, val_env, val_memory, self.batch_size
        )
        val_metrics["reward"] = val_total_reward / steps  # Average reward per step
        return val_metrics

    # -------------------------------------------------------------------------
    def _log_training_progress(
        self, scores: dict, val_scores: dict | None, time_step: int
    ) -> None:
        loss_value = float(scores.get("loss", 0.0))
        rmse_value = float(scores.get("root_mean_squared_error", 0.0))

        val_summary = ""
        if val_scores:
            val_loss = float(val_scores.get("loss", 0.0))
            val_rmse = float(val_scores.get("root_mean_squared_error", 0.0))
            val_summary = f" | Val Loss: {val_loss:.6f} | Val RMSE: {val_rmse:.6f}"

        logger.info(
            "Step %s | Loss: %.6f | RMSE: %.6f%s",
            time_step,
            loss_value,
            rmse_value,
            val_summary,
        )

    # -------------------------------------------------------------------------
    def _handle_replay_and_logging(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        val_environment: RouletteEnvironment | None,
        episode: int,
        time_step: int,
        reward: int | float,
        total_reward: int | float,
        state_size: int,
    ) -> None:
        if not self.agent.is_training_ready():
            return

        scores = self.agent.replay(model, target_model, environment, self.batch_size)

        val_scores = None
        if val_environment and time_step % 100 == 0:
            val_scores = self._run_validation(
                model, target_model, val_environment, state_size, steps=50
            )

        self.update_session_stats(
            scores, val_scores, episode, time_step, reward, total_reward, environment.capital
        )

        if time_step % 50 == 0:
            self._log_training_progress(scores, val_scores, time_step)

    # -------------------------------------------------------------------------
    def _handle_ws_updates(
        self,
        ws_callback: Callable[[dict[str, Any]], Any] | None,
        ws_env_callback: Callable[[dict[str, Any]], Any] | None,
        environment: RouletteEnvironment,
        episode: int,
        episodes: int,
        time_step: int,
        action: int,
        extraction: int,
        reward: int | float,
        total_reward: int | float,
    ) -> None:
        bucket_size = self.history_bucket_size if self.history_bucket_size > 0 else 1.0
        bucket = int(time_step / bucket_size)
        if self.max_steps >= HISTORY_POINTS_PER_EPISODE:
            bucket = min(HISTORY_POINTS_PER_EPISODE - 1, bucket)
        if self.last_progress_episode != episode:
            self.last_progress_episode = episode
            self.last_progress_bucket = None
        if self.last_progress_bucket != bucket:
            self.last_progress_bucket = bucket
            if ws_callback:
                stats = self.get_latest_stats(
                    episode,
                    episodes,
                    training_ready=self.agent.is_training_ready(),
                )
                try:
                    ws_callback(stats)
                except Exception:
                    pass

        if self.should_send_ws_update():
            self.maybe_send_environment_update(
                ws_env_callback,
                environment,
                episode,
                time_step,
                int(action),
                int(extraction),
                reward,
                total_reward,
                environment.capital,
            )

    # -------------------------------------------------------------------------
    async def train_with_reinforcement_learning(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        start_episode: int,
        episodes: int,
        state_size: int,
        ws_callback: Callable[[dict[str, Any]], Any] | None = None,
        ws_env_callback: Callable[[dict[str, Any]], Any] | None = None,
        val_environment: RouletteEnvironment | None = None,
    ) -> Model:
        total_steps = 0

        for i, episode in enumerate(range(start_episode, episodes)):
            if self.should_stop():
                logger.info("Training cancelled by user")
                break

            state = environment.reset(start_over=(i == 0))
            state = np.reshape(state, shape=(1, state_size))
            total_reward = 0

            for time_step in range(environment.max_steps):
                if self.should_stop():
                    break

                gain = np.reshape(environment.capital / environment.initial_capital, (1, 1))
                action = self.agent.act(model, state, gain)
                next_state, reward, done, extraction = environment.step(action)

                total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])
                next_gain = np.reshape(environment.capital / environment.initial_capital, (1, 1))

                self.agent.remember(state, action, reward, gain, next_gain, next_state, done)
                state = next_state

                self._handle_replay_and_logging(
                    model, target_model, environment, val_environment,
                    episode, time_step, reward, total_reward, state_size
                )

                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                self._handle_ws_updates(
                    ws_callback, ws_env_callback, environment, episode,
                    episodes, time_step, action, extraction, reward, total_reward
                )

                total_steps += 1
                if done:
                    break

                if total_steps % 100 == 0:
                    await asyncio.sleep(0)

        return model

    # -------------------------------------------------------------------------
    async def train_model(
        self,
        model: Model,
        target_model: Model,
        data: pd.DataFrame,
        checkpoint_path: str,
        ws_callback: Callable[[dict[str, Any]], Any] | None = None,
        ws_env_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> tuple[Model, dict[str, Any]]:
        environment = RouletteEnvironment(data, self.configuration, checkpoint_path)
        episodes = self.configuration.get("episodes", 10)
        start_episode = 0

        state_size = environment.observation_window.shape[0]
        logger.info(
            f"Size of the observation space (previous extractions): {state_size}"
        )

        # Split data for validation
        validation_split = self.configuration.get("validation_size", 0.0)
        val_environment = None
        if validation_split > 0.0:
            split_idx = int(len(data) * (1 - validation_split))
            train_data = data.iloc[:split_idx]
            val_data = data.iloc[split_idx:]
            environment = RouletteEnvironment(train_data, self.configuration, checkpoint_path)
            val_environment = RouletteEnvironment(val_data, self.configuration, checkpoint_path)
            logger.info(f"Splitting data: Train ({len(train_data)}) | Validation ({len(val_data)})")

        model = await self.train_with_reinforcement_learning(
            model,
            target_model,
            environment,
            start_episode,
            episodes,
            state_size,
            ws_callback=ws_callback,
            ws_env_callback=ws_env_callback,
            val_environment=val_environment,
        )

        history = {
            "history": self.session_stats,
            "val_history": None,
            "total_episodes": episodes,
        }

        self.agent.dump_memory(checkpoint_path)

        return model, history

    # -------------------------------------------------------------------------
    async def resume_training(
        self,
        model: Model,
        target_model: Model,
        data: pd.DataFrame,
        checkpoint_path: str,
        session: dict | None = None,
        additional_epochs: int = 10,
        ws_callback: Callable[[dict[str, Any]], Any] | None = None,
        ws_env_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> tuple[Model, dict[str, Any]]:
        environment = RouletteEnvironment(data, self.configuration, checkpoint_path)
        from_episode = 0 if not session else session.get("total_episodes", 0)
        total_episodes = from_episode + additional_epochs

        state_size = environment.observation_window.shape[0]
        logger.info(
            f"Size of the observation space (previous extractions): {state_size}"
        )
        model = await self.train_with_reinforcement_learning(
            model,
            target_model,
            environment,
            from_episode,
            total_episodes,
            state_size,
            ws_callback=ws_callback,
            ws_env_callback=ws_env_callback,
        )

        history = {
            "history": self.session_stats,
            "val_history": None,
            "total_episodes": total_episodes,
        }

        self.agent.dump_memory(checkpoint_path)

        return model, history
