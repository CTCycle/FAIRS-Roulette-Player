import numpy as np
import gymnasium as gym
from gymnasium import spaces
import keras
import tensorflow as tf

from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger

    
# [ROULETTE RL ENVIRONMENT]
###############################################################################
class RouletteEnvironment(gym.Env):

    def __init__(self, configuration):
        super(RouletteEnvironment, self).__init__()

        mapper = RouletteMapper()          
        self.window_size = configuration["dataset"]["WINDOW_SIZE"]
        self.initial_capital = configuration["environment"]["INITIAL_CAPITAL"]
        self.bet_amount = configuration["environment"]["BET_AMOUNT"]
        self.max_steps = configuration["environment"]["MAX_STEPS"] 
        
        self.numbers = list(range(STATES)) 
        self.red_numbers = mapper.color_map['red']
        self.black_numbers = mapper.color_map['black']
        
        # Actions: 0 (Red), 1 (Black), 2-37 for betting on a specific number
        self.action_space = spaces.Discrete(STATES + COLORS - 1)

        # Observation space is the last WINDOW_SIZE numbers that appeared on the wheel
        self.observation_space = spaces.Box(low=0, high=36, shape=(self.window_size,), dtype=np.int32)
        
        # Initialize state, capital, steps, and reward
        self.state = [np.random.randint(0, 37) for _ in range(self.window_size)]
        self.capital = self.initial_capital
        self.steps = 0
        self.reward = 0
        self.done = False
    
    # Reset the state of the environment to an initial state
    #--------------------------------------------------------------------------
    def reset(self):
        self.state = [np.random.randint(0, 37) for _ in range(self.window_size)]
        self.capital = self.initial_capital
        self.steps = 0
        self.done = False
        return np.array(self.state)

    # Perform the action (0: Bet on Red, 1: Bet on Black, 2: Bet on Specific Number)
    #--------------------------------------------------------------------------
    def step(self, action):
        next_extraction = np.random.randint(0, 37)
        self.state.pop(0)
        self.state.append(next_extraction)

        # Calculate reward based on the action
        if action == 0:  # Bet on Red
            if next_extraction in self.red_numbers:
                self.reward = self.bet_amount  # Win, gain bet amount
                self.capital += self.bet_amount
            else:
                self.reward = -self.bet_amount  # Lose, lose bet amount
                self.capital -= self.bet_amount
        elif action == 1:  # Bet on Black
            if next_extraction in self.black_numbers:
                self.reward = self.bet_amount  # Win
                self.capital += self.bet_amount
            else:
                self.reward = -self.bet_amount  # Lose
                self.capital -= self.bet_amount
        elif 2 <= action <= 37:  # Bet on Specific Number
            bet_number = action - 2
            if bet_number == next_extraction:
                self.reward = 35 * self.bet_amount  # Win 35 times the bet amount
                self.capital += 35 * self.bet_amount
            else:
                self.reward = -self.bet_amount  # Lose
                self.capital -= self.bet_amount

        self.steps += 1

        # Check if the episode should end
        if self.capital <= 0 or self.steps >= self.max_steps:
            self.done = True
        else:
            self.done = False

        return np.array(self.state), self.reward, self.done, {"capital": self.capital}
    

    # Render the environment to the screen 
    #--------------------------------------------------------------------------
    def render(self, mode='human'):
        print(f"Current state: {self.state}, Last extracted: {self.state[-1]}")
        print(f"Current capital: {self.capital}, Reward: {self.reward}")