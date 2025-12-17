from __future__ import annotations

import os
import pickle
import random
from collections import deque
from typing import Any

import numpy as np
from keras import Model

from FAIRS.app.utils.constants import PAD_VALUE, STATES
from FAIRS.app.utils.learning.training.environment import RouletteEnvironment


# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNAgent:
    def __init__(
        self, configuration: dict[str, Any], memory: Any | None = None
    ) -> None:
        self.action_size = STATES
        self.state_size = configuration.get("perceptive_field_size", 64)
        self.gamma = configuration.get("discount_rate", 0.5)
        self.epsilon = configuration.get("exploration_rate", 0.75)
        self.epsilon_decay = configuration.get("exploration_rate_decay", 0.995)
        self.epsilon_min = configuration.get("minimum_exploration_rate", 0.1)
        self.memory_size = configuration.get("max_memory_size", 10000)
        self.replay_size = configuration.get("replay_buffer_size", 1000)
        self.memory = deque(maxlen=self.memory_size) if memory is None else memory

    # -------------------------------------------------------------------------
    def dump_memory(self, path) -> None:
        memory_path = os.path.join(path, "configuration", "replay_memory.pkl")
        with open(memory_path, "wb") as f:
            pickle.dump(self.memory, f)

    # -------------------------------------------------------------------------
    def load_memory(self, path) -> None:
        memory_path = os.path.join(path, "configuration", "replay_memory.pkl")
        with open(memory_path, "rb") as f:
            self.memory = pickle.load(f)

    # -------------------------------------------------------------------------
    def act(self, model: Model, state: Any, gain: float | Any) -> np.int32:
        # generate a random number between 0 and 1 for exploration purposes.
        # if this number is equal or smaller to exploration rate, the agent will
        # pick a random roulette choice. It will do the same if the perceived field is empty
        random_threshold = np.random.rand()
        if np.all(state == PAD_VALUE) or random_threshold <= self.epsilon:
            # random action selection would not pick "quit the game"
            random_action = np.int32(random.randrange(self.action_size))
            return random_action
        # if the random value is above the exploration rate, the action will
        # be predicted by the current model snapshot
        q_values = model.predict({"timeseries": state, "gain": gain}, verbose=0)  # type: ignore
        best_q = np.int32(np.argmax(q_values))

        return best_q

    # -------------------------------------------------------------------------
    def remember(
        self,
        state: np.ndarray,
        action: np.int32,
        reward: int,
        gain: Any,
        next_gain: Any,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.memory.append((state, action, reward, gain, next_gain, next_state, done))

    # calculate the discounted future reward, using discount factor to determine
    # how much future rewards are taken into account. Each Q-value represents the
    # expected future reward if the agent takes that action from the given state.
    # The highest predicted value represents the action that the agent believes
    # will lead to the highest reward in the future.
    # -------------------------------------------------------------------------
    def replay(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        batch_size,
    ) -> dict[str, Any]:
        # this prevents an error if the batch size is larger than the replay buffer size
        batch_size = min(batch_size, self.replay_size)
        minibatch = random.sample(self.memory, batch_size)

        # minibatch is composed of multiple tuples, each containing:
        # state, action, reward, next state and status
        # arrays of shape (batch size, item shape) are created, state and next state shape = (1, perceptive field)
        # therefor their single dimension must be squeezed out while creating the stacked array
        states = np.array(
            [np.squeeze(s) for s, a, r, c, nc, ns, d in minibatch], dtype=np.int32
        )
        actions = np.array([a for s, a, r, c, nc, ns, d in minibatch], dtype=np.int32)
        rewards = np.array([r for s, a, r, c, nc, ns, d in minibatch], dtype=np.float32)
        gains = np.array(
            [np.squeeze(c) for s, a, r, c, nc, ns, d in minibatch], dtype=np.float32
        )
        next_gains = np.array(
            [np.squeeze(nc) for s, a, r, c, nc, ns, d in minibatch], dtype=np.float32
        )
        next_states = np.array(
            [np.squeeze(ns) for s, a, r, c, nc, ns, d in minibatch], dtype=np.int32
        )
        dones = np.array([d for s, a, r, c, nc, ns, d in minibatch], dtype=np.int32)

        # Predict current Q-values
        targets = model.predict({"timeseries": states, "gain": gains}, verbose=0)  # type: ignore

        # Double DQN next action selection via the online model
        # 1. Get Q-values for next states from the online model
        next_action_selection = model.predict(
            {"timeseries": next_states, "gain": next_gains}, verbose=0
        )  # type: ignore
        best_next_actions = np.argmax(next_action_selection, axis=1)

        # 2. Evaluate those actions using the target model
        Q_futures_target = target_model.predict(
            {"timeseries": next_states, "gain": next_gains}, verbose=0
        )  # type: ignore
        Q_future_selected = Q_futures_target[np.arange(batch_size), best_next_actions]

        # Scale rewards if your environment uses scaled rewards
        scaled_rewards = environment.scale_rewards(rewards)

        # Compute updated targets using Double DQN logic
        updated_targets = scaled_rewards + (1 - dones) * self.gamma * Q_future_selected

        # Update targets for the taken actions
        batch_indices = np.arange(batch_size, dtype=np.int32)
        targets[batch_indices, actions] = updated_targets

        # Fit the model on the entire batch using train on batch method
        logs = model.train_on_batch(
            {"timeseries": states, "gain": gains}, targets, return_dict=True
        )

        # Update epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return logs
