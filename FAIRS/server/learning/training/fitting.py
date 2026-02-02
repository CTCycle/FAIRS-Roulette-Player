from __future__ import annotations

import base64
import asyncio
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.server.configurations import server_settings
from FAIRS.server.utils.logger import logger
from FAIRS.server.learning.training.agents import DQNAgent
from FAIRS.server.learning.training.environment import RouletteEnvironment


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
        # Load render settings from server config
        self.render_environment = server_settings.training.render_environment
        self.configuration = configuration

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
        self.polling_interval_ms = int(server_settings.training.polling_interval * 1000)
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
        loss = scores.get("loss", None)
        metric = scores.get("root_mean_squared_error", None)
        self.session_stats["episode"].append(episode)
        self.session_stats["time_step"].append(time_step)
        self.session_stats["loss"].append(float(loss) if loss is not None else 0.0)
        self.session_stats["metrics"].append(
            float(metric) if metric is not None else 0.0
        )
        self.session_stats["reward"].append(reward)
        self.session_stats["total_reward"].append(total_reward)
        self.session_stats["capital"].append(capital)

        if val_scores:
            self.session_stats["val_loss"].append(val_scores.get("loss", 0.0))
            self.session_stats["val_rmse"].append(val_scores.get("root_mean_squared_error", 0.0))
            self.session_stats["img_reward"].append(val_scores.get("reward", 0.0))
        else:
            # Carry forward last value or 0.0
            last_val_loss = self.session_stats["val_loss"][-1] if self.session_stats["val_loss"] else 0.0
            last_val_rmse = self.session_stats["val_rmse"][-1] if self.session_stats["val_rmse"] else 0.0
            last_val_reward = self.session_stats["img_reward"][-1] if self.session_stats["img_reward"] else 0.0
            self.session_stats["val_loss"].append(last_val_loss)
            self.session_stats["val_rmse"].append(last_val_rmse)
            self.session_stats["img_reward"].append(last_val_reward)

    # -------------------------------------------------------------------------
    def get_latest_stats(self, episode: int, total_episodes: int) -> dict[str, Any]:
        initial_capital = self.configuration.get("initial_capital", 0.0)
        initial_capital_value = (
            float(initial_capital) if isinstance(initial_capital, (int, float)) else 0.0
        )
        if not self.session_stats["loss"]:
            return {
                "epoch": episode + 1,
                "total_epochs": total_episodes,
                "time_step": 0,
                "loss": 0.0,
                "rmse": 0.0,
                "reward": 0,
                "total_reward": 0,
                "capital": 0,
                "capital_gain": 0.0,
                "status": "training",
            }
        capital_value = self.session_stats["capital"][-1]
        return {
            "epoch": episode + 1,
            "total_epochs": total_episodes,
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
            "status": "training",
        }

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

            next_state, reward, done, extraction = val_env.step(action)
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
        scores = None
        total_steps = 0

        for i, episode in enumerate(range(start_episode, episodes)):
            if self.should_stop():
                logger.info("Training cancelled by user")
                break

            start_over = True if i == 0 else False
            state = environment.reset(start_over=start_over)
            state = np.reshape(state, shape=(1, state_size))
            total_reward = 0

            for time_step in range(environment.max_steps):
                if self.should_stop():
                    break

                gain = environment.capital / environment.initial_capital
                gain = np.reshape(gain, shape=(1, 1))

                action = self.agent.act(model, state, gain)
                next_state, reward, done, extraction = environment.step(action)
                total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])

                next_gain = environment.capital / environment.initial_capital
                next_gain = np.reshape(next_gain, shape=(1, 1))

                self.agent.remember(
                    state, action, reward, gain, next_gain, next_state, done
                )
                state = next_state

                if len(self.agent.memory) > self.replay_size:
                    scores = self.agent.replay(
                        model, target_model, environment, self.batch_size
                    )
                    
                    # Run Validation periodically (e.g., every 100 steps)
                    val_scores = None
                    if val_environment and time_step % 100 == 0:
                        val_scores = self._run_validation(
                            model, target_model, val_environment, state_size, steps=50
                        )

                    self.update_session_stats(
                        scores,
                        val_scores,
                        episode,
                        time_step,
                        reward,
                        total_reward,
                        environment.capital,
                    )

                    if time_step % 50 == 0:
                        loss_value = float(scores.get("loss", 0.0))
                        rmse_value = float(scores.get("root_mean_squared_error", 0.0))

                        val_summary = ""
                        if val_scores:
                            val_loss = float(val_scores.get("loss", 0.0))
                            val_rmse = float(val_scores.get("root_mean_squared_error", 0.0))
                            val_summary = (
                                f" | Val Loss: {val_loss:.6f} | Val RMSE: {val_rmse:.6f}"
                            )

                        logger.info(
                            "Step %s | Loss: %.6f | RMSE: %.6f%s",
                            time_step,
                            loss_value,
                            rmse_value,
                            val_summary,
                        )

                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                # Send progress updates (stats + environment) based on time interval
                if self.should_send_ws_update():
                    # Send stats update
                    if ws_callback:
                        stats = self.get_latest_stats(episode, episodes)
                        try:
                            ws_callback(stats)
                        except Exception:
                            pass
                    
                    # Send environment render if enabled
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

                total_steps += 1
                if done:
                    break

                # Yield control to event loop periodically
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
