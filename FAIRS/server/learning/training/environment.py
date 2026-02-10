from __future__ import annotations

from io import BytesIO
import math
from typing import Any, Literal

import gymnasium as gym
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from gymnasium import spaces

from FAIRS.server.common.constants import NUMBERS, PAD_VALUE, STATES
from FAIRS.server.services.process import RouletteSeriesEncoder


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
class RouletteWheelRenderer:
    def __init__(self, red_numbers: list[int], black_numbers: list[int]) -> None:
        self.red_numbers = set(red_numbers)
        self.black_numbers = set(black_numbers)
        self.odd_numbers = set(range(1, NUMBERS, 2))
        self.even_numbers = set(range(2, NUMBERS, 2))
        self.low_numbers = set(range(1, 19))
        self.high_numbers = set(range(19, NUMBERS))
        self.first_dozen_numbers = set(range(1, 13))
        self.second_dozen_numbers = set(range(13, 25))
        self.third_dozen_numbers = set(range(25, NUMBERS))

        self.size = 720
        self.background_color = (15, 23, 42, 255)
        self.base_green = (0, 147, 60, 235)
        self.base_red = (227, 29, 43, 235)
        self.base_black = (26, 26, 26, 235)
        self.action_highlight = (124, 58, 237, 120)
        self.extraction_highlight = (250, 204, 21, 160)
        self.label_color = (255, 255, 255, 230)
        self.rim_color = (226, 232, 240, 160)

        self.font = ImageFont.load_default()

    # -------------------------------------------------------------------------
    def render(
        self,
        episode: int,
        time_step: int,
        action: int,
        extracted_number: int,
        capital: int | float,
        reward: int | float,
    ) -> bytes:
        image = Image.new("RGBA", (self.size, self.size), self.background_color)
        draw = ImageDraw.Draw(image)

        center_x = self.size / 2
        center_y = self.size / 2
        radius = int(self.size * 0.38)
        label_radius = int(self.size * 0.43)
        inner_radius = int(self.size * 0.16)
        rim_radius = radius + int(self.size * 0.015)

        bbox = (
            int(center_x - radius),
            int(center_y - radius),
            int(center_x + radius),
            int(center_y + radius),
        )
        rim_bbox = (
            int(center_x - rim_radius),
            int(center_y - rim_radius),
            int(center_x + rim_radius),
            int(center_y + rim_radius),
        )

        highlight_numbers = self.get_action_highlights(action)
        degrees_per_slice = 360.0 / float(NUMBERS)
        start_angle_offset = -90.0

        draw.ellipse(rim_bbox, outline=self.rim_color, width=3)

        for number in range(NUMBERS):
            start = start_angle_offset + number * degrees_per_slice
            end = start + degrees_per_slice
            base_color = self.get_number_color(number)
            draw.pieslice(bbox, start=start, end=end, fill=base_color)

            if number in highlight_numbers:
                draw.pieslice(bbox, start=start, end=end, fill=self.action_highlight)
            if number == extracted_number:
                draw.pieslice(bbox, start=start, end=end, fill=self.extraction_highlight)

            mid_angle = (start + end) / 2.0
            angle_rad = math.radians(mid_angle)
            label_x = center_x + label_radius * math.cos(angle_rad)
            label_y = center_y + label_radius * math.sin(angle_rad)
            label = str(number)
            left, top, right, bottom = draw.textbbox((0, 0), label, font=self.font)
            text_width = right - left
            text_height = bottom - top
            draw.text(
                (label_x - text_width / 2, label_y - text_height / 2),
                label,
                font=self.font,
                fill=self.label_color,
            )

        inner_bbox = (
            int(center_x - inner_radius),
            int(center_y - inner_radius),
            int(center_x + inner_radius),
            int(center_y + inner_radius),
        )
        draw.ellipse(inner_bbox, fill=self.background_color, outline=self.rim_color, width=2)

        header = f"Episode {episode + 1} • Step {time_step}"
        footer = f"Capital: {capital} • Reward: {reward} • Extracted: {extracted_number}"
        draw.text((20, 20), header, font=self.font, fill=self.label_color)
        draw.text((20, self.size - 30), footer, font=self.font, fill=self.label_color)

        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    # -------------------------------------------------------------------------
    def get_number_color(self, number: int) -> tuple[int, int, int, int]:
        if number == 0:
            return self.base_green
        if number in self.red_numbers:
            return self.base_red
        return self.base_black

    # -------------------------------------------------------------------------
    def get_action_highlights(self, action: int) -> set[int]:
        if 0 <= action <= 36:
            return {action}
        if action == 37:
            return set(self.red_numbers)
        if action == 38:
            return set(self.black_numbers)
        if action == 40:
            return set(self.odd_numbers)
        if action == 41:
            return set(self.even_numbers)
        if action == 42:
            return set(self.low_numbers)
        if action == 43:
            return set(self.high_numbers)
        if action == 44:
            return set(self.first_dozen_numbers)
        if action == 45:
            return set(self.second_dozen_numbers)
        if action == 46:
            return set(self.third_dozen_numbers)
        return set()


###############################################################################
class RouletteEnvironment(gym.Env):
    def __init__(
        self, data: pd.DataFrame, configuration: dict[str, Any], checkpoint_path: str
    ) -> None:
        super(RouletteEnvironment, self).__init__()
        self.extractions = data["extraction"].values
        self.positions = data["wheel_position"].values
        self.colors = data["color_code"].values
        self.checkpoint_path = checkpoint_path
        self._rng = np.random.default_rng(configuration.get("train_seed", 42))

        self.perceptive_size = configuration.get("perceptive_field_size", 64)
        self.initial_capital = configuration.get("initial_capital", 1000)
        self.bet_amount = configuration.get("bet_amount", 10)
        self.max_steps = configuration.get("max_steps_episode", 2000)
        self.player = BetsAndRewards(configuration)

        self.black_numbers = self.player.black_numbers
        self.red_numbers = self.player.red_numbers
        self.renderer = RouletteWheelRenderer(self.red_numbers, self.black_numbers)

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
    def render_frame(self, episode: int, time_step: int, action: int, extracted_number: int) -> bytes:
        return self.renderer.render(
            episode=episode,
            time_step=time_step,
            action=action,
            extracted_number=extracted_number,
            capital=self.capital,
            reward=self.reward,
        )

    # -------------------------------------------------------------------------
    def reset(self, start_over: bool = False, seed: int | None = None) -> np.ndarray:
        if seed is not None:
            self._rng = np.random.default_rng(seed)
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
        random_index = self._rng.integers(0, end_cutoff)
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
