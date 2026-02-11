from __future__ import annotations

import os
import pickle
import random
from collections import deque
from typing import Any

import numpy as np
from keras import Model

from FAIRS.server.common.constants import PAD_VALUE, STATES
from FAIRS.server.learning.training.environment import RouletteEnvironment


###############################################################################
class DQNAgent:
    def __init__(
        self, configuration: dict[str, Any], memory: Any | None = None
    ) -> None:
        self.rng = np.random.default_rng(seed=configuration.get("seed", 42))
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
        random_threshold = self.rng.random()
        if np.all(state == PAD_VALUE) or random_threshold <= self.epsilon:
            random_action = np.int32(self.rng.integers(0, self.action_size))
            return random_action
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

    # -------------------------------------------------------------------------
    def replay(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        batch_size,
    ) -> dict[str, Any]:
        batch_size = min(batch_size, self.replay_size)
        minibatch = random.sample(self.memory, batch_size)

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

        targets = model.predict({"timeseries": states, "gain": gains}, verbose=0)  # type: ignore

        next_action_selection = model.predict(
            {"timeseries": next_states, "gain": next_gains},
            verbose=0,  # type: ignore
        )
        best_next_actions = np.argmax(next_action_selection, axis=1)

        q_futures_target = target_model.predict(
            {"timeseries": next_states, "gain": next_gains},
            verbose=0,  # type: ignore
        )
        q_future_selected = q_futures_target[np.arange(batch_size), best_next_actions]

        scaled_rewards = environment.scale_rewards(rewards)
        updated_targets = scaled_rewards + (1 - dones) * self.gamma * q_future_selected

        batch_indices = np.arange(batch_size, dtype=np.int32)
        targets[batch_indices, actions] = updated_targets

        logs = model.train_on_batch(
            {"timeseries": states, "gain": gains}, targets, return_dict=True
        )

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return logs

    # -------------------------------------------------------------------------
    def is_training_ready(self) -> bool:
        return len(self.memory) > self.replay_size

    # -------------------------------------------------------------------------
    def evaluate_batch(
        self,
        model: Model,
        target_model: Model,
        environment: RouletteEnvironment,
        memory_buffer: deque,
        batch_size: int,
    ) -> dict[str, Any]:
        """
        Evaluates the model on a batch of transitions without updating weights.
        Returns loss and metric values.
        """
        if len(memory_buffer) < batch_size:
            return {"loss": 0.0, "root_mean_squared_error": 0.0}

        minibatch = random.sample(memory_buffer, batch_size)

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

        targets = model.predict({"timeseries": states, "gain": gains}, verbose=0)  # type: ignore

        next_action_selection = model.predict(
            {"timeseries": next_states, "gain": next_gains},
            verbose=0,  # type: ignore
        )
        best_next_actions = np.argmax(next_action_selection, axis=1)

        q_futures_target = target_model.predict(
            {"timeseries": next_states, "gain": next_gains},
            verbose=0,  # type: ignore
        )
        q_future_selected = q_futures_target[np.arange(batch_size), best_next_actions]

        scaled_rewards = environment.scale_rewards(rewards)
        updated_targets = scaled_rewards + (1 - dones) * self.gamma * q_future_selected

        batch_indices = np.arange(batch_size, dtype=np.int32)
        targets[batch_indices, actions] = updated_targets

        # Evaluate manually using model.evaluate or by running a single forward pass and calculating loss
        # Here we use evaluate()
        results = model.evaluate(
            {"timeseries": states, "gain": gains},
            targets,
            verbose=0,
            return_dict=True,  # type: ignore
        )

        return results
