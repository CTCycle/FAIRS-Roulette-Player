import os
import random
import numpy as np
from collections import deque
import keras
import torch
from torch.amp import GradScaler
import tensorflow as tf

from FAIRS.commons.utils.learning.models import FAIRSnet
from FAIRS.commons.utils.learning.environment import RouletteEnvironment
from FAIRS.commons.utils.learning.callbacks import RealTimeHistory, LoggingCallback
from FAIRS.commons.utils.dataloader.serializer import ModelSerializer
from FAIRS.commons.constants import CONFIG, STATES, COLORS
from FAIRS.commons.logger import logger



# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNAgent:
    def __init__(self, model, configuration):
        self.state_size = configuration["dataset"]["PERCEPTIVE_SIZE"]
        self.action_size = STATES + COLORS + 1
        self.memory = deque(maxlen=2000)
        self.gamma = configuration['agent']['DISCOUNT_RATE'] 
        self.epsilon = configuration['agent']['EXPLORATION_RATE']  
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.model = model
    
    #--------------------------------------------------------------------------
    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)  
        q_values = self.model.predict(state)
        return keras.ops.argmax(q_values[0])  

    #--------------------------------------------------------------------------
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    #--------------------------------------------------------------------------
    def replay(self, batch_size):
        minibatch = np.random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = reward + self.gamma * np.argmax(self.model.predict(next_state)[0])
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNTraining:

    def __init__(self, configuration):        
              
        self.serializer = ModelSerializer()
        self.batch_size = configuration['training']['BATCH_SIZE']       
        self.configuration = configuration 
        
        # set seed for random operations
        keras.utils.set_random_seed(configuration["SEED"])  
        self.selected_device = configuration["device"]["DEVICE"]
        self.device_id = configuration["device"]["DEVICE_ID"]
        self.mixed_precision = self.configuration["device"]["MIXED_PRECISION"]              

    # set device
    #--------------------------------------------------------------------------
    def set_device(self):
        if self.selected_device == 'GPU':
            if not torch.cuda.is_available():
                logger.info('No GPU found. Falling back to CPU')
                self.device = torch.device('cpu')
            else:
                self.device = torch.device(f'cuda:{self.device_id}')
                torch.cuda.set_device(self.device)  
                logger.info('GPU is set as active device')            
                if self.mixed_precision:
                    keras.mixed_precision.set_global_policy("mixed_float16")
                    logger.info('Mixed precision policy is active during training')                   
        else:
            self.device = torch.device('cpu')
            logger.info('CPU is set as active device')  


    #--------------------------------------------------------------------------
    def train_model(self, model, data, checkpoint_path, from_checkpoint=False):

        environment = RouletteEnvironment(data, self.configuration)   
        agent = DQNAgent(model, self.configuration)

        # perform different initialization duties based on state of session:
        # training from scratch vs resumed training
        # calculate number of epochs taking into account possible training resumption
        if not from_checkpoint:            
            epochs = self.configuration['training']['EPOCHS'] 
            episodes = self.configuration['training']['EPISODES']
            from_epoch = 0
            start_episode = 0
            history = None
        else:
            _, history = self.serializer.load_session_configuration(checkpoint_path)                     
            epochs = history['total_epochs'] + CONFIG['training']['ADDITIONAL_EPOCHS'] 
            from_epoch = history['total_epochs']
            start_episode = from_epoch        

        # Initialize environment and agent's states
        state_size = environment.observation_space.shape[0]
        action_size = environment.action_space.n

        # Setup callbacks
        RTH_callback = RealTimeHistory(checkpoint_path, past_logs=history)
        logger_callback = LoggingCallback()
        callbacks_list = [RTH_callback, logger_callback]

        if CONFIG['training']['USE_TENSORBOARD']:
            log_dir = os.path.join(checkpoint_path, 'tensorboard')
            callbacks_list.append(keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1))

        # Training loop for each episode
        for episode in range(start_episode, episodes):
            state = environment.reset()
            state = np.reshape(state, [1, state_size])
            total_reward = 0

            for time_step in range(environment.max_steps):
                action = agent.act(state)
                next_state, reward, done, info = environment.step(action)
                total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])

                # Remember experience
                agent.remember(state, action, reward, next_state, done)
                state = next_state

                # Perform replay if the memory size is sufficient
                if len(agent.memory) > self.batch_size:
                    agent.replay(self.batch_size)

                if done:
                    logger.info(f"Episode {episode+1}/{episodes} - Time steps: {time_step+1} - Capital: {info['capital']} - Total Reward: {total_reward}")
                    break

            # Save progress at checkpoints (you can define a frequency or save every episode)
            if episode % self.configuration['training']['SAVE_FREQUENCY'] == 0:
                logger.info(f"Saving model at episode {episode}")
                self.serializer.save_pretrained_model(agent.model, checkpoint_path)
                history = {'history': RTH_callback.history, 'val_history': RTH_callback.val_history, 'total_epochs': episode}
                self.serializer.save_session_configuration(checkpoint_path, history, self.configuration)

        # Save the final model at the end of training
        self.serializer.save_pretrained_model(agent.model, checkpoint_path)
        history = {'history': RTH_callback.history, 'val_history': RTH_callback.val_history, 'total_epochs': episodes}
        self.serializer.save_session_configuration(checkpoint_path, history, self.configuration)


