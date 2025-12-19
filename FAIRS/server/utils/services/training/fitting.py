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
        # Load render settings from server config
        self.render_environment = server_settings.training.render_environment
        self.configuration = configuration

        self.agent = DQNAgent(configuration)
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

        # WebSocket update related
        self.ws_update_interval_ms = server_settings.training.websocket_update_interval_ms
        self.last_ws_update_time = 0.0
        self.is_cancelled = False



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
        self.session_stats["loss"].append(loss.item() if loss is not None else 0.0)
        self.session_stats["metrics"].append(
            metric.item() if metric is not None else 0.0
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
            "val_loss": self.session_stats["val_loss"][-1] if self.session_stats["val_loss"] else 0.0,
            "val_rmse": self.session_stats["val_rmse"][-1] if self.session_stats["val_rmse"] else 0.0,
            "reward": self.session_stats["reward"][-1],
            "val_reward": self.session_stats["img_reward"][-1] if self.session_stats["img_reward"] else 0.0,
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
        val_environment: RouletteEnvironment | None = None,
    ) -> Model:
        scores = None
        total_steps = 0

        async def run_validation(val_env: RouletteEnvironment, steps: int = 100) -> dict[str, float]:
            val_state = val_env.reset()
            val_state = np.reshape(val_state, shape=(1, state_size))
            val_total_reward = 0
            val_memory = deque(maxlen=steps + 10)
            
            for _ in range(steps):
                gain = val_env.capital / val_env.initial_capital
                gain = np.reshape(gain, shape=(1, 1))
                
                # Greedy action (epsilon=0 for validation usually, or low)
                # We'll use the act method but force epsilon=0 if we could, 
                # but DQNAgent doesn't expose epsilon override in act().
                # We can backup generic epsilon and restore it, or just rely on current epsilon.
                # Usually validation is done greedily.
                old_eps = self.agent.epsilon
                self.agent.epsilon = 0.0
                action = self.agent.act(model, val_state, gain)
                self.agent.epsilon = old_eps
                
                next_state, reward, done, extraction = val_env.step(action)
                val_total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])
                
                next_gain = val_env.capital / val_env.initial_capital
                next_gain = np.reshape(next_gain, shape=(1, 1))
                
                val_memory.append((val_state, action, reward, gain, next_gain, next_state, done))
                val_state = next_state
                
                if done:
                    val_state = val_env.reset()
                    val_state = np.reshape(val_state, shape=(1, state_size))

            # Evaluate batch
            val_metrics = self.agent.evaluate_batch(model, target_model, val_env, val_memory, self.batch_size)
            val_metrics["reward"] = val_total_reward / steps # Average reward per step
            return val_metrics

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
                    
                    # Run Validation periodically (e.g., every 100 steps)
                    val_scores = None
                    if val_environment and time_step % 100 == 0:
                        val_scores = await run_validation(val_environment, steps=50)

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
                        # logger.info(f"Loss: {scores['loss']} | RMSE: {scores['root_mean_squared_error']}")
                        pass

                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                # Send WebSocket updates (stats + environment) based on time interval
                if self.should_send_ws_update():
                    # Send stats update
                    if ws_callback:
                        stats = self.get_latest_stats(episode, episodes)
                        try:
                            await ws_callback(stats)
                        except Exception:
                            pass
                    
                    # Send environment render if enabled
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
            checkpoint_path,
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
