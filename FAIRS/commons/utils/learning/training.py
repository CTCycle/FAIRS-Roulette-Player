import os
import numpy as np
import keras
import torch

from FAIRS.commons.utils.learning.callbacks import callbacks_handler
from FAIRS.commons.utils.learning.environment import RouletteEnvironment
from FAIRS.commons.utils.learning.agents import DQNAgent
from FAIRS.commons.utils.learning.callbacks import RealTimeHistory
from FAIRS.commons.utils.dataloader.serializer import ModelSerializer
from FAIRS.commons.constants import CONFIG, NUMBERS, COLORS
from FAIRS.commons.logger import logger


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
    def reinforcement_learning_routine(self, agent : DQNAgent, environment : RouletteEnvironment, 
                                       start_episode, episodes, state_size, RTH_callback : RealTimeHistory,
                                       callback_list, checkpoint_path):

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
                    agent.replay(self.batch_size, callback_list)

                if done:
                    logger.info(f"Episode {episode+1}/{episodes} - Time steps: {time_step+1} - Capital: {info['capital']} - Total Reward: {total_reward}")
                    break

            # Save progress at checkpoints (you can define a frequency or save every episode)
            if self.configuration['training']['SAVE_CHECKPOINT']:
                logger.info(f"Saving model at episode {episode}")
                self.serializer.save_pretrained_model(agent.model, checkpoint_path)
                history = {'history': RTH_callback.history, 'val_history': RTH_callback.val_history, 'total_epochs': episode}
                self.serializer.save_session_configuration(checkpoint_path, history, self.configuration)

        return agent, history 
 


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

        # Initialize environment and agent's NUMBERS
        state_size = environment.observation_space.shape[0]
        action_size = environment.action_space.n
        
        # add all callbacks to the callback list
        RTH_callback, callbacks_list = callbacks_handler(self.configuration, checkpoint_path, history)      

        # run reinforcement learning routing        
        agent, history = self.reinforcement_learning_routine(agent, environment, start_episode, episodes,
                                                             state_size, RTH_callback, callbacks_list,
                                                             checkpoint_path)

        # Save the final model at the end of training
        self.serializer.save_pretrained_model(agent.model, checkpoint_path)
        history = {'history': RTH_callback.history, 'val_history': RTH_callback.val_history, 'total_epochs': episodes}
        self.serializer.save_session_configuration(checkpoint_path, history, self.configuration)


