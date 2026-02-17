from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from keras import Model
from keras.utils import set_random_seed

from FAIRS.server.common.constants import PAD_VALUE
from FAIRS.server.learning.betting.hold import StrategyHold
from FAIRS.server.learning.betting.sizer import BetSizer
from FAIRS.server.learning.betting.types import (
    BET_OUTCOME_NEUTRAL,
    STRATEGY_KEEP,
    normalize_strategy_id,
    strategy_name,
)
from FAIRS.server.repositories.serialization.data import DataSerializer
from FAIRS.server.learning.training.environment import BetsAndRewards


###############################################################################
class RoulettePlayer:
    def __init__(
        self,
        model: Model,
        configuration: dict[str, Any],
        session_id: str,
        dataset_id: int,
        dataset_source: str | None = None,
        strategy_model: Model | None = None,
    ) -> None:
        set_random_seed(configuration.get("seed", 42))

        self.session_id = session_id
        self.dataset_id = dataset_id
        self.perceptive_size = int(configuration.get("perceptive_field_size", 64))
        self.initial_capital = int(configuration.get("game_capital", 100))
        self.bet_amount = int(configuration.get("game_bet", 1))
        self.dynamic_betting_enabled = bool(
            configuration.get("dynamic_betting_enabled", False)
        )
        self.bet_strategy_model_enabled = bool(
            configuration.get("bet_strategy_model_enabled", False)
        )
        self.auto_apply_bet_suggestions = bool(
            configuration.get("auto_apply_bet_suggestions", False)
        )
        self.fixed_strategy_id = normalize_strategy_id(
            configuration.get("bet_strategy_fixed_id", STRATEGY_KEEP),
            STRATEGY_KEEP,
        )

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
        self.strategy_model = strategy_model
        self.configuration = configuration
        self.bet_sizer = BetSizer(
            {
                **configuration,
                "bet_amount": self.bet_amount,
                "initial_capital": self.initial_capital,
            }
        )
        self.strategy_hold = StrategyHold(
            hold_steps=int(configuration.get("strategy_hold_steps", 1)),
            fallback_strategy_id=self.fixed_strategy_id,
        )

        self.serializer = DataSerializer()
        self.context = self.serializer.load_dataset_outcomes(dataset_id)

    # -----------------------------------------------------------------------------
    def initialize_states(self) -> None:
        if self.context.empty or "outcome" not in self.context.columns:
            raise ValueError("Inference context is empty or missing outcome column.")
        outcomes = pd.to_numeric(self.context["outcome"], errors="coerce").dropna()
        if outcomes.empty:
            raise ValueError("Inference context contains no outcomes.")

        perceptive_candidates = outcomes.to_numpy(dtype=np.int32)
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
    def predict_strategy(self, current_state: np.ndarray, gain_input: np.ndarray) -> int:
        if (
            not self.dynamic_betting_enabled
            or not self.bet_strategy_model_enabled
            or self.strategy_model is None
        ):
            return self.fixed_strategy_id
        strategy_logits = self.strategy_model.predict(
            {"timeseries": current_state, "gain": gain_input},
            verbose=0,  # type: ignore
        )
        logits = np.asarray(strategy_logits).reshape(-1)
        if logits.size == 0:
            return self.fixed_strategy_id
        return int(np.argmax(logits))

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

        prediction: dict[str, Any] = {
            "action": self.next_action,
            "description": self.next_action_desc,
            "confidence": confidence,
        }

        if self.dynamic_betting_enabled:
            selected_strategy = self.predict_strategy(current_state, gain_input)
            resolved_strategy = self.strategy_hold.resolve(selected_strategy)
            suggested_bet = int(
                self.bet_sizer.apply(resolved_strategy, capital=self.current_capital)
            )
            if self.auto_apply_bet_suggestions:
                self.update_bet_amount(suggested_bet, reset_strategy_state=False)
            prediction["bet_strategy_id"] = int(resolved_strategy)
            prediction["bet_strategy_name"] = strategy_name(resolved_strategy)
            prediction["suggested_bet_amount"] = int(suggested_bet)
            prediction["current_bet_amount"] = int(self.bet_amount)

        return prediction

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
            if self.dynamic_betting_enabled:
                self.bet_sizer.set_last_outcome_from_reward(reward)

        return int(reward), int(self.current_capital)

    # -----------------------------------------------------------------------------
    def update_bet_amount(self, bet_amount: int, reset_strategy_state: bool = True) -> None:
        self.bet_amount = int(bet_amount)
        actions = BetsAndRewards({**self.configuration, "bet_amount": self.bet_amount})
        self.action_descriptions = actions.action_descriptions
        self.player = actions
        if self.dynamic_betting_enabled and reset_strategy_state:
            self.bet_sizer.set_base_bet(self.bet_amount, self.current_capital)
            self.bet_sizer.last_outcome = BET_OUTCOME_NEUTRAL
        self.fixed_strategy_id = normalize_strategy_id(
            self.configuration.get("bet_strategy_fixed_id", STRATEGY_KEEP),
            STRATEGY_KEEP,
        )
