import numpy as np
import gymnasium as gym
from gymnasium import spaces
import keras
import tensorflow as tf

from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger

    
# [ROULETTE RL ENVIRONMENT]
###############################################################################
class RouletteEnvironment(gym.Env):

    def __init__(self, configuration):
        super(RouletteEnvironment, self).__init__()
        self.all_states = STATES + COLORS - 1
        self.action_space = spaces.Discrete(self.all_states)  
        self.window_size = configuration["dataset"]["WINDOW_SIZE"] 
        self.observation_space = spaces.Box(low=0, high=STATES-1, shape=(self.window_size,), dtype=np.int32)  
        self.state = [np.random.randint(0, 36) for _ in range(5)] + + [np.random.choice([0, 1]), np.random.choice([0, 1])]
        self.reward = 0
    
    # Reset the state of the environment to an initial state
    #--------------------------------------------------------------------------
    def reset(self):
        
        self.state = [np.random.randint(0, 36) for _ in range(5)]
        return np.array(self.state)

    # Perform the action (0: Bet on Red, 1: Bet on Black, 2: Bet on Specific Number)
    #--------------------------------------------------------------------------
    def step(self, action):
        
        next_extraction = np.random.randint(0, 36)
        self.state.pop(0)
        self.state.append(next_extraction)

        # Determine if the bet was successful
        if action == 0:  # Bet on Red
            if next_extraction in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
                self.reward = 1
            else:
                self.reward = -1
        elif action == 1:  # Bet on Black
            if next_extraction in [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]:
                self.reward = 1
            else:
                self.reward = -1
        elif action == 2:  # Bet on Specific Number
            bet_number = np.random.randint(0, 36)  # Choosing a random number to bet on
            if bet_number == next_extraction:
                self.reward = 35
            else:
                self.reward = -1

        return np.array(self.state), self.reward, False, {}
    
    # Render the environment to the screen 
    #--------------------------------------------------------------------------
    def render(self):
        
        print(f"Current state: {self.state}")