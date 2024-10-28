import random
import numpy as np
from collections import deque
import keras

from FAIRS.commons.constants import CONFIG, NUMBERS, COLORS
from FAIRS.commons.logger import logger



# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNAgent:
    def __init__(self, model : keras.Model, configuration):
        self.state_size = configuration["dataset"]["PERCEPTIVE_SIZE"]
        self.action_size = NUMBERS + COLORS - 1        
        self.gamma = configuration['agent']['DISCOUNT_RATE'] 
        self.epsilon = configuration['agent']['EXPLORATION_RATE']              
        self.epsilon_decay = configuration['agent']['EXPLORATION_RATE_DECAY'] 
        self.epsilon_min = configuration['agent']['MIN_EXPLORATION_RATE'] 
        self.memory_size = configuration['agent']['MAX_MEMORY'] 
        self.memory = deque(maxlen=self.memory_size)  
        self.model = model
    
    #--------------------------------------------------------------------------
    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)  
        q_values = self.model.predict(state)
        best_q = np.argmax(q_values) 

        return best_q 

    #--------------------------------------------------------------------------
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    # calculate the discounted future reward, using discount factor to determine 
    # how much future rewards are taken into account. Each Q-value represents the 
    # expected future reward if the agent takes that action from the given state. 
    # The highest predicted value represents the action that the agent believes 
    # will lead to the highest reward in the future.
    #--------------------------------------------------------------------------
    def replay(self, batch_size, callback_list):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:                
                target = reward + self.gamma * np.max(self.model.predict(next_state)[0])
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=1, callbacks=callback_list)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


