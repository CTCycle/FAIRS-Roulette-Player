from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.app.client.workers import check_thread_status, update_progress_callback
from FAIRS.app.utils.learning.callbacks import CallbacksWrapper
from FAIRS.app.utils.learning.training.agents import DQNAgent
from FAIRS.app.utils.learning.training.environment import RouletteEnvironment
from FAIRS.app.utils.logger import logger


# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
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
        self.configuration = configuration
        # initialize variables
        self.callbacks = CallbacksWrapper(configuration)
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

    # set device
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
    def train_with_reinforcement_learning(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        start_episode,
        episodes,
        state_size,
        checkpoint_path,
        **kwargs,
    ) -> Model:
        # if tensorboard is selected, an instance of the tb callback is built
        # the dashboard is set on the Q model and tensorboard is launched automatically
        tensorboard = None
        if self.configuration.get("use_tensorboard", False):
            tensorboard = self.callbacks.get_tensorboard_callback(
                checkpoint_path, model
            )
            tensorboard.on_train_begin()

        progress_callback = kwargs.get("progress_callback", None)
        worker = kwargs.get("worker", None)
        RTH_callback, GS_callback = None, None
        if self.configuration.get("plot_training_metrics", True):
            RTH_callback, GS_callback = self.callbacks.get_metrics_callbacks(
                checkpoint_path, progress_callback=progress_callback
            )

        # Training loop for each episode
        scores = None
        total_steps = 0
        for i, episode in enumerate(range(start_episode, episodes)):
            start_over = True if i == 0 else False
            state = environment.reset(start_over=start_over)
            state = np.reshape(state, shape=(1, state_size))
            total_reward = 0
            for time_step in range(environment.max_steps):
                gain = environment.capital / environment.initial_capital
                gain = np.reshape(gain, shape=(1, 1))
                # action is always performed using the Q-model
                action = self.agent.act(model, state, gain)
                next_state, reward, done, extraction = environment.step(action)
                total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])
                # compute next gain after environment updated capital
                next_gain = environment.capital / environment.initial_capital
                next_gain = np.reshape(next_gain, shape=(1, 1))

                # render environment
                if environment.render_environment:
                    png = environment.render(episode, time_step, action, extraction)
                    if png is not None and progress_callback:
                        try:
                            progress_callback(
                                {"kind": "render", "source": "env_render", "data": png}
                            )
                        except Exception:
                            pass

                # Remember experience
                self.agent.remember(
                    state, action, reward, gain, next_gain, next_state, done
                )
                state = next_state

                # Perform replay if the memory size is sufficient
                # use both the Q model and the target model
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

                # Update target network periodically
                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                if GS_callback and time_step % 100 == 0:
                    GS_callback.plot_game_statistics(self.session_stats)

                # call on_epoch_end method of selected callbacks
                if tensorboard and scores:
                    tensorboard.on_batch_end(batch=total_steps, logs=scores)

                check_thread_status(worker)

                total_steps += 1
                if done:
                    break

            # call on_epoch_end method of selected callbacks
            if tensorboard and scores:
                tensorboard.on_epoch_end(epoch=episode, logs=scores)

            if RTH_callback:
                RTH_callback.plot_loss_and_metrics(episode, self.session_stats)

            # check for worker thread status and update progress callback
            check_thread_status(worker)
            update_progress_callback(i + 1, episodes, progress_callback)

        if tensorboard:
            tensorboard.on_train_end()

        return model

    # -------------------------------------------------------------------------
    def train_model(
        self,
        model: Model,
        target_model: Model,
        data: pd.DataFrame,
        checkpoint_path: str,
        **kwargs,
    ) -> tuple[Model, dict[str, Any]]:
        environment = RouletteEnvironment(data, self.configuration, checkpoint_path)
        episodes = self.configuration.get("episodes", 10)
        start_episode = 0
        history = None

        # determine state size as the observation space size
        state_size = environment.observation_window.shape[0]
        logger.info(
            f"Size of the observation space (previous extractions): {state_size}"
        )
        model = self.train_with_reinforcement_learning(
            model,
            target_model,
            environment,
            start_episode,
            episodes,
            state_size,
            checkpoint_path,
            progress_callback=kwargs.get("progress_callback", None),
            worker=kwargs.get("worker", None),
        )

        # use the real time history callback data to retrieve current loss and metric values
        # this allows to correctly resume the training metrics plot if training from checkpoint
        history = {
            "history": self.session_stats,
            "val_history": None,
            "total_episodes": episodes,
        }

        # serialize training memory using pickle
        self.agent.dump_memory(checkpoint_path)

        return model, history

    # -------------------------------------------------------------------------
    def resume_training(
        self,
        model: Model,
        target_model: Model,
        data: pd.DataFrame,
        checkpoint_path: str,
        session: dict | None = None,
        additional_epochs: int = 10,
        **kwargs,
    ) -> tuple[Model, dict[str, Any]]:
        environment = RouletteEnvironment(data, self.configuration, checkpoint_path)
        from_episode = 0 if not session else session["epochs"]
        total_episodes = from_episode + additional_epochs

        # determine state size as the observation space size
        state_size = environment.observation_window.shape[0]
        logger.info(
            f"Size of the observation space (previous extractions): {state_size}"
        )
        model = self.train_with_reinforcement_learning(
            model,
            target_model,
            environment,
            from_episode,
            total_episodes,
            state_size,
            checkpoint_path,
        )

        # use the real time history callback data to retrieve current loss and metric values
        # this allows to correctly resume the training metrics plot if training from checkpoint
        history = {
            "history": self.session_stats,
            "val_history": None,
            "total_episodes": total_episodes,
        }

        # serialize training memory using pickle
        self.agent.dump_memory(checkpoint_path)

        return model, history
