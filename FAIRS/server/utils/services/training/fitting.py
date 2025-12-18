from __future__ import annotations

import base64
import asyncio
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.server.utils.configurations import server_settings
from FAIRS.server.utils.logger import logger
from FAIRS.server.utils.services.training.agents import DQNAgent
from FAIRS.server.utils.services.training.environment import RouletteEnvironment


###############################################################################
class DQNTraining:
    def __init__(self, configuration: dict[str, Any]) -> None:
        set_random_seed(configuration.get("training_seed", 42))
        self.batch_size = configuration.get("batch_size", 32)
        self.update_frequency = configuration.get("model_update_frequency", 10)
        self.replay_size = configuration.get("replay_buffer_size", 1000)
        self.selected_device = configuration.get("device", "cpu")
        self.device_id = configuration.get("device_id", 0)
        self.mixed_precision = configuration.get("mixed_precision", False)
        self.render_environment = configuration.get("render_environment", False)
        self.render_update_frequency = configuration.get("render_update_frequency", 50)
        self.configuration = configuration

        self.agent = DQNAgent(configuration)
        self.session_stats = {
            "episode": [],
            "time_step": [],
            "loss": [],
            "metrics": [],
            "reward": [],
            "total_reward": [],
            "capital": [],
        }

        # WebSocket update related
        self.ws_update_interval_ms = server_settings.training.websocket_update_interval_ms
        self.last_ws_update_time = 0.0
        self.is_cancelled = False

    # -------------------------------------------------------------------------
    def update_render_settings(self, render_environment: bool, render_update_frequency: int) -> None:
        self.render_environment = render_environment
        self.render_update_frequency = render_update_frequency

    # -------------------------------------------------------------------------
    async def maybe_send_environment_update(
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
        if time_step % self.render_update_frequency != 0:
            return

        try:
            image_bytes = environment.render_frame(episode, time_step, action, extraction)
            await ws_env_callback({
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
        self.session_stats["loss"].append(loss.item() if loss is not None else 0.0)
        self.session_stats["metrics"].append(
            metric.item() if metric is not None else 0.0
        )
        self.session_stats["reward"].append(reward)
        self.session_stats["total_reward"].append(total_reward)
        self.session_stats["capital"].append(capital)

    # -------------------------------------------------------------------------
    def get_latest_stats(self, episode: int, total_episodes: int) -> dict[str, Any]:
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
                "status": "training",
            }
        return {
            "epoch": episode + 1,
            "total_epochs": total_episodes,
            "time_step": self.session_stats["time_step"][-1],
            "loss": self.session_stats["loss"][-1],
            "rmse": self.session_stats["metrics"][-1],
            "reward": self.session_stats["reward"][-1],
            "total_reward": self.session_stats["total_reward"][-1],
            "capital": self.session_stats["capital"][-1],
            "status": "training",
        }

    # -------------------------------------------------------------------------
    def should_send_ws_update(self) -> bool:
        current_time = time.time() * 1000
        if current_time - self.last_ws_update_time >= self.ws_update_interval_ms:
            self.last_ws_update_time = current_time
            return True
        return False

    # -------------------------------------------------------------------------
    def cancel_training(self) -> None:
        self.is_cancelled = True

    # -------------------------------------------------------------------------
    async def train_with_reinforcement_learning(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        start_episode: int,
        episodes: int,
        state_size: int,
        checkpoint_path: str,
        ws_callback: Callable[[dict[str, Any]], Any] | None = None,
        ws_env_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> Model:
        scores = None
        total_steps = 0

        for i, episode in enumerate(range(start_episode, episodes)):
            if self.is_cancelled:
                logger.info("Training cancelled by user")
                break

            start_over = True if i == 0 else False
            state = environment.reset(start_over=start_over)
            state = np.reshape(state, shape=(1, state_size))
            total_reward = 0

            for time_step in range(environment.max_steps):
                if self.is_cancelled:
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
                    self.update_session_stats(
                        scores,
                        episode,
                        time_step,
                        reward,
                        total_reward,
                        environment.capital,
                    )

                    if time_step % 50 == 0:
                        logger.info(
                            f"Loss: {scores['loss']} | RMSE: {scores['root_mean_squared_error']}"
                        )
                        logger.info(
                            f"Episode {episode + 1}/{episodes} - Time steps: {time_step} - Capital: {environment.capital} - Total Reward: {total_reward}"
                        )

                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                await self.maybe_send_environment_update(
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

                # Send WebSocket update at configured interval
                if ws_callback and self.should_send_ws_update():
                    stats = self.get_latest_stats(episode, episodes)
                    try:
                        await ws_callback(stats)
                    except Exception:
                        pass

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
        model = await self.train_with_reinforcement_learning(
            model,
            target_model,
            environment,
            start_episode,
            episodes,
            state_size,
            checkpoint_path,
            ws_callback=ws_callback,
            ws_env_callback=ws_env_callback,
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
            checkpoint_path,
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
