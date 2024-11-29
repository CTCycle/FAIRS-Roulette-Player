import os
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import matplotlib
matplotlib.use('TkAgg') 
import matplotlib.pyplot as plt

from FAIRS.commons.utils.process.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG, STATES, NUMBERS
from FAIRS.commons.logger import logger



    
# [ROULETTE RL ENVIRONMENT]
###############################################################################
class RouletteEnvironment(gym.Env):

    def __init__(self, data : np.array, configuration):
        super(RouletteEnvironment, self).__init__()       

        self.timeseries = data[:, 0]
        self.positions = data[:, 1]
        self.colors = data[:, 2]

        mapper = RouletteMapper()          
        self.perceptive_size = configuration["dataset"]["PERCEPTIVE_SIZE"]
        
        self.initial_capital = configuration["environment"]["INITIAL_CAPITAL"]
        self.bet_amount = configuration["environment"]["BET_AMOUNT"]
        self.max_steps = configuration["environment"]["MAX_STEPS"] 
        self.render_environment = configuration["environment"]["RENDERING"]
        
        self.numbers = list(range(NUMBERS)) 
        self.red_numbers = mapper.color_map['red']
        self.black_numbers = mapper.color_map['black']        
        
        # Actions: 0 (Red), 1 (Black), 2-37 for betting on a specific number
        self.action_space = spaces.Discrete(STATES)
        # Observation space is the last WINDOW_SIZE numbers that appeared on the wheel
        self.observation_space = spaces.Box(low=0, high=36, shape=(self.perceptive_size,), dtype=np.int32)
        
        # Initialize state, capital, steps, and reward  
        self.extraction_index = 0 
        self.state = np.full(shape=self.perceptive_size, fill_value=-1)                       
        self.capital = self.initial_capital
        self.steps = 0
        self.reward = 0
        self.done = False
        
        if self.render_environment:
            plt.ion()  # Turn on interactive mode
            self.fig, self.ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
            self.fig.canvas.manager.set_window_title('Roulette Wheel')  # Set window title
            plt.show(block=False)  # Display the window once

            # Store references to text objects for updating
            self.title_text = self.ax.set_title("Roulette Wheel - Current Spin")
            self.capital_text = self.fig.text(0.5, 0.05, "", ha="center", fontsize=12)
            self.extraction_text = self.fig.text(0.5, 0.01, "", ha="center", fontsize=10)
        
    # Reset the state of the environment to an initial state
    #--------------------------------------------------------------------------
    def reset(self):        
        self.extraction_index = 0
        self.state = np.full(shape=self.perceptive_size, fill_value=-1, dtype=np.int32)                  
        self.capital = self.initial_capital
        self.steps = 0
        self.done = False

        return self.state

    # Perform the action (0: Bet on Red, 1: Bet on Black, 2: Bet on Specific Number)
    #--------------------------------------------------------------------------
    def step(self, action):
        
        next_extraction = np.int32(self.timeseries[self.extraction_index])        
        self.state = np.delete(self.state, 0)
        self.state = np.append(self.state, next_extraction)
        self.extraction_index += 1

        # Calculate reward based on the action
        if 0 <= action <= 36:  # Bet on Specific Number            
            if action == next_extraction:
                self.reward = 35 * self.bet_amount 
                self.capital += 35 * self.bet_amount
            else:
                self.reward = -self.bet_amount  
                self.capital -= self.bet_amount 

        elif action == 37:  # Bet on Red
            if next_extraction in self.red_numbers:
                self.reward = self.bet_amount  
                self.capital += self.bet_amount
            else:
                self.reward = -self.bet_amount  
                self.capital -= self.bet_amount 

        elif action == 38:  # Bet on Black
            if next_extraction in self.black_numbers:
                self.reward = self.bet_amount 
                self.capital += self.bet_amount
            else:
                self.reward = -self.bet_amount  
                self.capital -= self.bet_amount

        elif action == 39: # pass the turn  
                self.reward = 0  
                self.capital -= 0       

        self.steps += 1

        # Check if the episode should end
        if self.capital <= 0 or self.steps >= self.max_steps:
            self.done = True
        else:
            self.done = False

        return self.state, self.reward, self.done, {"capital": self.capital}
    

    # Render the environment to the screen 
    #--------------------------------------------------------------------------
    def render(self):

        self.ax.clear()

        # Roulette layout: assigning colors to each number
        colors = ['green'] + ['red', 'black'] * 18
        labels = list(range(NUMBERS))

        theta = np.linspace(0, 2 * np.pi, NUMBERS, endpoint=False)
        width = 2 * np.pi / NUMBERS

        # Create bars
        bars = self.ax.bar(theta, np.ones(NUMBERS), width=width, color=colors, edgecolor='white', align='edge')

        # Highlight the last extracted number
        extracted_number = 0 if np.all(self.state == -1) else self.state[-1]
        bars[extracted_number].set_facecolor('yellow')  # Highlight the extracted number
        bars[extracted_number].set_alpha(0.7)           # Increase opacity for emphasis

        # Adjust the position of the labels to be on the outer edge
        for i, (label, angle) in enumerate(zip(labels, theta)):
            angle_label = angle + width / 2
            x = angle_label
            y = 1.05  # Position radius just outside the wheel
            angle_deg = np.degrees(angle_label)
            if angle_deg >= 270:
                angle_deg -= 360  # Normalize angle between -90 and 270 degrees
            # Text rotation
            rotation = angle_deg
            self.ax.text(x, y, str(label),
                         rotation=rotation, rotation_mode='anchor',
                         ha='center', va='center', color='black', fontsize=8,
                         clip_on=False)

        # Remove the grid and axis labels
        self.ax.grid(False)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        # Set the radius limit to include the labels
        self.ax.set_ylim(0, 1.15)

        # Update title and texts without creating new ones
        self.title_text.set_text("Roulette Wheel - Current Spin")
        self.capital_text.set_text(f"Current capital: {self.capital} | Reward: {self.reward}")
        self.extraction_text.set_text(f"Last extracted number: {extracted_number}")

        # Draw the updated plot
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()        