from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.server.common.constants import PAD_VALUE
from FAIRS.server.repositories.serialization.serializer import DataSerializer
from FAIRS.server.learning.training.environment import BetsAndRewards


###############################################################################
class RoulettePlayer:
    def __init__(
        self,
        model: Model,
        configuration: dict[str, Any],
        session_id: str,
        dataset_name: str,
        dataset_source: str | None = None,
    ) -> None:
        set_random_seed(configuration.get("seed", 42))

        self.session_id = session_id
        self.dataset_name = dataset_name
        self.perceptive_size = int(configuration.get("perceptive_field_size", 64))
        self.initial_capital = int(configuration.get("game_capital", 100))
        self.bet_amount = int(configuration.get("game_bet", 1))

        actions = BetsAndRewards({**configuration, "bet_amount": self.bet_amount})
        self.action_descriptions = actions.action_descriptions

        self.current_capital = self.initial_capital
        self.last_state: np.ndarray | None = None
        self.last_action: int | None = None
        self.next_action: int | None = None
        self.next_action_desc: str | None = None
        self.true_extraction: int | None = None

        self.player = BetsAndRewards({**configuration, "bet_amount": self.bet_amount})
        self.model = model
        self.configuration = configuration

        self.serializer = DataSerializer()
        if dataset_source == "uploaded":
            self.context = self.serializer.load_inference_context(dataset_name)
        elif dataset_source == "source":
            self.context = self.serializer.load_roulette_dataset(dataset_name)
        else:
            self.context = self.serializer.load_inference_context(dataset_name)
            if self.context.empty:
                self.context = self.serializer.load_roulette_dataset(dataset_name)

    # -----------------------------------------------------------------------------
    def initialize_states(self) -> None:
        if self.context.empty or "extraction" not in self.context.columns:
            raise ValueError("Inference context is empty or missing extraction column.")
        extractions = pd.to_numeric(self.context["extraction"], errors="coerce").dropna()
        if extractions.empty:
            raise ValueError("Inference context contains no extractions.")

        perceptive_candidates = extractions.to_numpy(dtype=np.int32)
        state = np.full(
            shape=(self.perceptive_size,),
            fill_value=PAD_VALUE,
            dtype=np.int32,
        )
        if perceptive_candidates.size < self.perceptive_size:
            raise ValueError(
                "Inference context must contain at least the perceptive field size."
            )
        state = perceptive_candidates[-self.perceptive_size :]
        self.last_state = state

    # -----------------------------------------------------------------------------
    def softmax(self, values: np.ndarray) -> np.ndarray:
        shifted = values - np.max(values)
        exp_values = np.exp(shifted)
        denom = float(np.sum(exp_values))
        if denom <= 0:
            return np.full_like(exp_values, fill_value=1.0 / float(exp_values.size))
        return exp_values / denom

    # -----------------------------------------------------------------------------
    def predict_next(self) -> dict[str, Any]:
        if self.last_state is None:
            self.initialize_states()
        assert self.last_state is not None

        current_state = self.last_state.reshape(1, self.perceptive_size)
        gain_value = (
            float(self.current_capital) / float(self.initial_capital)
            if self.initial_capital
            else 1.0
        )
        gain_input = np.asarray([[gain_value]], dtype=np.float32)

        action_logits = self.model.predict(
            {"timeseries": current_state, "gain": gain_input},
            verbose=0,  # type: ignore
        )
        logits = np.asarray(action_logits).reshape(-1)
        if logits.size == 0:
            raise ValueError("Model returned empty logits.")

        self.next_action = int(np.argmax(logits))
        self.last_action = self.next_action
        self.next_action_desc = self.action_descriptions.get(
            self.next_action, f"action {self.next_action}"
        )

        probabilities = self.softmax(logits)
        confidence = float(probabilities[self.next_action])

        return {
            "action": self.next_action,
            "description": self.next_action_desc,
            "confidence": confidence,
        }

    # -----------------------------------------------------------------------------
    def update_with_true_extraction(self, real_number: int) -> tuple[int, int]:
        if not isinstance(real_number, (int, np.integer)):
            raise ValueError("Real extraction must be an integer")
        if real_number < 0 or real_number > 36:
            raise ValueError("Real extraction must be in between 0 and 36")
        if self.last_state is None:
            self.initialize_states()
        assert self.last_state is not None

        self.true_extraction = int(real_number)
        self.last_state = np.append(self.last_state[1:], np.int32(real_number))

        reward = 0
        if self.last_action is not None:
            reward, new_capital, _ = self.player.interact_and_get_rewards(
                self.last_action, real_number, int(self.current_capital)
            )
            self.current_capital = int(new_capital)

        return int(reward), int(self.current_capital)

    # -----------------------------------------------------------------------------
    def update_bet_amount(self, bet_amount: int) -> None:
        self.bet_amount = int(bet_amount)
        actions = BetsAndRewards({**self.configuration, "bet_amount": self.bet_amount})
        self.action_descriptions = actions.action_descriptions
        self.player = actions


