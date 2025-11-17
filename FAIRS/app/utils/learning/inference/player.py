from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.app.utils.constants import PAD_VALUE
from FAIRS.app.utils.learning.training.environment import BetsAndRewards
from FAIRS.app.utils.repository.serializer import DataSerializer


###############################################################################
class RoulettePlayer:
    def __init__(self, model: Model, configuration: dict[str, Any]) -> None:
        set_random_seed(configuration.get("seed", 42))
        self.perceptive_size = configuration.get("perceptive_field_size", 64)
        self.initial_capital = configuration.get("game_capital", 100)
        self.bet_amount = configuration.get("game_bet", 1)

        # define dictionary of action descriptions from the environment support class
        actions = BetsAndRewards(configuration)
        self.action_descriptions = actions.action_descriptions

        # capital gain is not fully implemented as input of the pipeline
        self.current_capital = self.initial_capital
        self.last_state: np.ndarray | None = None
        self.gain: Any | None = None
        self.last_action: int | None = None
        self.player = BetsAndRewards(configuration)

        self.model = model
        self.configuration = configuration

        # Load the data you will use to seed the perceptive field.
        # The player expects raw extractions in [0, 36] as ints.
        self.serializer = DataSerializer()
        self.dataset = self.serializer.load_inference_dataset()
        self.updated_dataset: pd.DataFrame | None = None
        self.true_extraction: Any | None = None
        self.next_action_desc: Any | None = None

    # -------------------------------------------------------------------------
    def initialize_states(self) -> None:
        input_data = self.dataset["extraction"].to_numpy(dtype=np.int32).reshape(-1, 1)
        if not self.last_state:
            self.last_state = np.full(
                shape=self.perceptive_size, fill_value=PAD_VALUE, dtype=np.int32
            )

        perceptive_candidates = np.asarray(input_data)[:, 0]
        perceptive_candidates = perceptive_candidates.astype(np.int32, copy=False)
        if perceptive_candidates.size >= self.perceptive_size:
            self.last_state = perceptive_candidates[-self.perceptive_size :]
        else:
            if self.last_state:
                self.last_state[-perceptive_candidates.size :] = perceptive_candidates

    # -------------------------------------------------------------------------
    def predict_next(self) -> dict[str, Any]:
        if not self.last_state:
            self.initialize_states()

        current_state = (
            self.last_state.reshape(1, self.perceptive_size)
            if self.last_state
            else None
        )
        # compute gain context and predict with both inputs
        gain_value = (
            (self.current_capital / self.initial_capital)
            if self.initial_capital
            else 1.0
        )
        gain_input = np.reshape(gain_value, (1, 1)).astype(np.float32)
        action_logits = self.model.predict(
            {"timeseries": current_state, "gain": gain_input}, verbose="0"
        )
        self.next_action = int(np.argmax(action_logits, axis=1)[0])
        self.last_action = self.next_action
        self.next_action_desc = self.action_descriptions.get(
            self.next_action, f"action {self.next_action}"
        )

        return {"action": self.next_action, "description": self.next_action_desc}

    # -------------------------------------------------------------------------
    def update_with_true_extraction(self, real_number: int) -> None:
        if not isinstance(real_number, (int, np.integer)):
            raise ValueError("Real extraction must be an integer")
        if real_number < 0 or real_number > 36:
            raise ValueError("Real extraction must be in between 0 and 36")

        # roll window and append the new value
        self.true_extraction = real_number
        if self.last_state:
            self.last_state = np.append(self.last_state[1:], np.int32(real_number))

        # update capital based on the last action and the true extraction
        if self.last_action is not None:
            reward, new_capital, _ = self.player.interact_and_get_rewards(
                self.last_action, real_number, self.current_capital
            )
            self.current_capital = new_capital

    # -------------------------------------------------------------------------
    def save_prediction(self, checkpoint_name: str) -> None:
        new_id = int(self.dataset["id"].max()) + 1 if len(self.dataset) else 1
        true_extraction = int(self.true_extraction) if self.true_extraction else None
        row = {
            "id": new_id,
            "checkpoint": checkpoint_name,
            "extraction": true_extraction,
            "predicted_action": self.next_action_desc,
        }

        # persist new prediction in the database
        self.serializer.save_predicted_games(pd.DataFrame([row]))
