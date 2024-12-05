import random
import numpy as np
from collections import deque
import keras

from FAIRS.commons.utils.learning.environment import RouletteEnvironment
from FAIRS.commons.constants import CONFIG, STATES
from FAIRS.commons.logger import logger



# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNAgent:
    def __init__(self, configuration):
        self.state_size = configuration["model"]["PERCEPTIVE_FIELD"]
        self.action_size = STATES        
        self.gamma = configuration['agent']['DISCOUNT_RATE'] 
        self.epsilon = configuration['agent']['EXPLORATION_RATE']              
        self.epsilon_decay = configuration['agent']['EXPLORATION_RATE_DECAY'] 
        self.epsilon_min = configuration['agent']['MIN_EXPLORATION_RATE'] 
        self.memory_size = configuration['agent']['MAX_MEMORY'] 
        self.replay_size = configuration['agent']['REPLAY_BUFFER']   
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
        q_values = model.predict(state, verbose=0)
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
    def replay(self, model : keras.Model, target_model : keras.Model, environment : RouletteEnvironment, batch_size):

        # this prevents an error if the batch size is larger than the replay buffer size
        batch_size = min(batch_size, self.replay_size)
        minibatch = random.sample(self.memory, batch_size)

        # minibatch is composed of multiple tuples, each containing state, action, reqard, next state and status
        # arrays of shape (batch size, item shape) are created. Both state and next state have shape (1, perceptive field)
        # therefor their single dimension must be squeezed out while creating the stacked array
        states = np.array([np.squeeze(state) for state, action, reward, next_state, done in minibatch], dtype=np.int32)
        actions = np.array([action for state, action, reward, next_state, done in minibatch], dtype=np.int32)
        rewards = np.array([reward for state, action, reward, next_state, done in minibatch], dtype=np.float32)
        next_states = np.array([np.squeeze(next_state) for state, action, reward, next_state, done in minibatch], dtype=np.int32)
        dones = np.array([done for state, action, reward, next_state, done in minibatch], dtype=np.int32)

        # Predict Q-values for current states and next states
        targets = model.predict(states, verbose=0)
        Q_futures = target_model.predict(next_states, verbose=0)
        Q_future_max = np.max(Q_futures, axis=1)

        # Compute updated target values
        scaled_rewards = environment.scale_rewards(rewards)
        updated_targets = scaled_rewards + self.gamma * Q_future_max * (1 - dones)

        # Update targets for the taken actions
        batch_indices = np.arange(batch_size, dtype=np.int32)
        targets[batch_indices, actions] = updated_targets

        # Fit the model on the entire batch using train on batch method
        logs = model.train_on_batch(states, targets, return_dict=True)         

        # Update epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return logs


