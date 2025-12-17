from __future__ import annotations

from typing import Any, Literal

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from FAIRS.server.utils.constants import NUMBERS, PAD_VALUE, STATES
from FAIRS.server.utils.services.process import RouletteSeriesEncoder


###############################################################################
class BetsAndRewards:
    def __init__(self, configuration: dict[str, Any]) -> None:
        self.seed = configuration.get("train_seed", 42)
        self.bet_amount = configuration.get("bet_amount", 10)
        self.numbers = list(range(NUMBERS))
        mapper = RouletteSeriesEncoder()
        self.red_numbers = mapper.color_map["red"]
        self.black_numbers = mapper.color_map["black"]

        self.num_actions = 47
        self.action_descriptions = {i: f"Bet on number {i}" for i in range(37)}
        self.action_descriptions.update(
            {
                37: "Bet on Red",
                38: "Bet on Black",
                39: "Pass",
                40: "Bet on Odd",
                41: "Bet on Even",
                42: "Bet on Low (1-18)",
                43: "Bet on High (19-36)",
                44: "Bet on First Dozen (1-12)",
                45: "Bet on Second Dozen (13-24)",
                46: "Bet on Third Dozen (25-36)",
            }
        )

    # -------------------------------------------------------------------------
    def bet_on_number(
        self, action: int, next_extraction: int
    ) -> tuple[int, Literal[False]]:
        if action == next_extraction:
            reward = 35 * self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_red(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if next_extraction in self.red_numbers:
            reward = self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_black(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if next_extraction in self.black_numbers:
            reward = self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_odd(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if next_extraction != 0 and next_extraction % 2 == 1:
            reward = self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_even(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if next_extraction != 0 and next_extraction % 2 == 0:
            reward = self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_low(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if 1 <= next_extraction <= 18:
            reward = self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_high(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if 19 <= next_extraction <= (NUMBERS - 1):
            reward = self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_first_dozen(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if 1 <= next_extraction <= 12:
            reward = 2 * self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_second_dozen(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if 13 <= next_extraction <= 24:
            reward = 2 * self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def bet_on_third_dozen(self, next_extraction: int) -> tuple[int, Literal[False]]:
        if 25 <= next_extraction <= (NUMBERS - 1):
            reward = 2 * self.bet_amount
        else:
            reward = -self.bet_amount
        return reward, False

    # -------------------------------------------------------------------------
    def pass_turn(self) -> tuple[int, Literal[False]]:
        return 0, False

    # -------------------------------------------------------------------------
    def interact_and_get_rewards(
        self, action: int, next_extraction: int, capital: int
    ) -> tuple[int, int, Literal[False]]:
        done = False
        if 0 <= action <= 36:
            reward, done = self.bet_on_number(action, next_extraction)
        elif action == 37:
            reward, done = self.bet_on_red(next_extraction)
        elif action == 38:
            reward, done = self.bet_on_black(next_extraction)
        elif action == 39:
            reward, done = self.pass_turn()
        elif action == 40:
            reward, done = self.bet_on_odd(next_extraction)
        elif action == 41:
            reward, done = self.bet_on_even(next_extraction)
        elif action == 42:
            reward, done = self.bet_on_low(next_extraction)
        elif action == 43:
            reward, done = self.bet_on_high(next_extraction)
        elif action == 44:
            reward, done = self.bet_on_first_dozen(next_extraction)
        elif action == 45:
            reward, done = self.bet_on_second_dozen(next_extraction)
        elif action == 46:
            reward, done = self.bet_on_third_dozen(next_extraction)
        else:
            reward = 0

        capital += reward
        return reward, capital, done


###############################################################################
class RouletteEnvironment(gym.Env):
    def __init__(
        self, data: pd.DataFrame, configuration: dict[str, Any], checkpoint_path: str
    ) -> None:
        super(RouletteEnvironment, self).__init__()
        self.extractions = data["extraction"].values
        self.positions = data["position"].values
        self.colors = data["color_code"].values
        self.checkpoint_path = checkpoint_path

        self.perceptive_size = configuration.get("perceptive_field_size", 64)
        self.initial_capital = configuration.get("initial_capital", 1000)
        self.bet_amount = configuration.get("bet_amount", 10)
        self.max_steps = configuration.get("max_steps_episode", 2000)
        self.player = BetsAndRewards(configuration)

        self.black_numbers = self.player.black_numbers
        self.red_numbers = self.player.red_numbers

        self.numbers = list(range(NUMBERS))
        self.action_space = spaces.Discrete(STATES)
        self.observation_window = spaces.Box(
            low=0, high=36, shape=(self.perceptive_size,), dtype=np.int32
        )

        self.extraction_index = 0
        self.state = np.full(shape=self.perceptive_size, fill_value=PAD_VALUE)
        self.capital = self.initial_capital
        self.steps = 0
        self.reward = 0
        self.done = False

    # -------------------------------------------------------------------------
    def reset(self, start_over: bool = False, seed: int | None = None) -> np.ndarray:
        self.extraction_index = 0 if start_over else self.select_random_index()
        self.state = np.full(
            shape=self.perceptive_size, fill_value=PAD_VALUE, dtype=np.int32
        )
        self.capital = self.initial_capital
        self.steps = 0
        self.done = False
        return self.state

    # -------------------------------------------------------------------------
    def scale_rewards(self, rewards) -> np.ndarray:
        negative_scaled = (
            (rewards - (-self.bet_amount)) / (0 - (-self.bet_amount))
        ) * (0 - (-1)) + (-1)
        positive_scaled = ((rewards - 0) / (self.bet_amount * 35)) * (1 - 0) + 0
        scaled_rewards = np.where(rewards < 0, negative_scaled, positive_scaled)
        return scaled_rewards

    # -------------------------------------------------------------------------
    def select_random_index(self) -> int:
        end_cutoff = len(self.extractions) - self.perceptive_size
        random_index = np.random.randint(0, end_cutoff)
        return random_index

    # -------------------------------------------------------------------------
    def update_rewards(self, action, next_extraction) -> None:
        self.reward, self.capital, self.done = self.player.interact_and_get_rewards(
            action, next_extraction, self.capital
        )

    # -------------------------------------------------------------------------
    def step(self, action) -> tuple[np.ndarray, int, bool, Any]:
        if self.extraction_index >= len(self.extractions):
            self.extraction_index = self.select_random_index()

        next_extraction = np.int32(self.extractions[self.extraction_index])
        self.state = np.delete(self.state, 0)
        self.state = np.append(self.state, next_extraction)
        self.extraction_index += 1
        self.update_rewards(action, next_extraction)
        self.steps += 1

        if self.capital <= 0 or self.steps >= self.max_steps:
            self.done = True
        else:
            self.done = False

        return self.state, self.reward, self.done, next_extraction
