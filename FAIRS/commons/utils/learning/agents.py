import random
import numpy as np
from collections import deque
import keras

from FAIRS.commons.constants import CONFIG, STATES
from FAIRS.commons.logger import logger



# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNAgent:
    def __init__(self, configuration):
        self.state_size = configuration["dataset"]["PERCEPTIVE_SIZE"]
        self.action_size = STATES        
        self.gamma = configuration['agent']['DISCOUNT_RATE'] 
        self.epsilon = configuration['agent']['EXPLORATION_RATE']              
        self.epsilon_decay = configuration['agent']['EXPLORATION_RATE_DECAY'] 
        self.epsilon_min = configuration['agent']['MIN_EXPLORATION_RATE'] 
        self.memory_size = configuration['agent']['MAX_MEMORY'] 
        self.memory = deque(maxlen=self.memory_size)          
    
    #--------------------------------------------------------------------------
    def act(self, model : keras.Model, state):
        # generate a random number between 0 and 1 for exploration purposes.
        # if this number is equal or smaller to exploration rate, the agent will
        # pick a random roulette choice. It will do the same if the perceived field is empty
        random_threshold = np.random.rand()
        if np.all(state == -1) or random_threshold <= self.epsilon:
            random_action = np.int32(random.randrange(self.action_size))
            return random_action
        # if the random value is above the exploration rate, the action will
        # be predicted by the current model snapshot
        q_values = model.predict(state)
        best_q = np.int32(np.argmax(q_values))

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
    def replay(self, model : keras.Model, batch_size, callback_list):

        minibatch = random.sample(self.memory, batch_size)        
        for state, action, reward, next_state, done in minibatch:            
            target = model.predict(state)
            target[0][action] = reward
            if not done:                
                Q_future = np.max(model.predict(next_state)[0])
                target[0][action] = reward + self.gamma * Q_future          

            model.fit(state, target, epochs=1, verbose=1, callbacks=callback_list)
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay


