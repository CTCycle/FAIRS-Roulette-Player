import numpy as np
import keras
import torch

from FAIRS.commons.utils.learning.callbacks import CallbacksWrapper
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
        self.update_frequency = configuration['training']['UPDATE_FREQUENCY'] 
        self.replay_size = configuration['agent']['REPLAY_BUFFER']     
        self.configuration = configuration 
        
        # set seed for random operations
        keras.utils.set_random_seed(configuration["SEED"])  
        self.selected_device = configuration["device"]["DEVICE"]
        self.device_id = configuration["device"]["DEVICE_ID"]
        self.mixed_precision = self.configuration["device"]["MIXED_PRECISION"]  

        # initialize variables
        self.session = []
        self.callback_wrapper = CallbacksWrapper(configuration)               
                    

    # set device
    #--------------------------------------------------------------------------
    def set_device(self):
        
        if self.selected_device == 'GPU':
            # fallback to CPU if no GPU is available
            if not torch.cuda.is_available():
                logger.info('No GPU found. Falling back to CPU')
                self.device = torch.device('cpu')
            else:
                self.device = torch.device(f'cuda:{self.device_id}')
                torch.cuda.set_device(self.device)  
                logger.info('GPU is set as active device')
                # set global policy as mixed precision if selected            
                if self.mixed_precision:
                    keras.mixed_precision.set_global_policy("mixed_float16")
                    logger.info('Mixed precision policy is active during training')                   
        else:
            self.device = torch.device('cpu')
            logger.info('CPU is set as active device') 

    # set device
    #--------------------------------------------------------------------------
    def update_session_stats(self, scores, episode, time_step, reward, total_reward):
        loss = scores.get('loss', None)
        metric = scores.get('mean_absolute_percentage_error', None)                   
        self.session.append({'episode': episode,
                            'time_step': time_step,
                            'loss': loss.item() if not None else 0,
                            'metrics': metric.item() if not None else 0,
                            'reward': reward,
                            'total_reward': total_reward})
        

    #--------------------------------------------------------------------------
    def reinforcement_learning_pipeline(self, model : keras.Model, target_model : keras.Model,
                                       agent : DQNAgent, environment : RouletteEnvironment, 
                                       start_episode, episodes, state_size, checkpoint_path):

        # if tensorboard is selected, an instance of the tb callback is built
        # the dashboard is set on the Q model and tensorboard is launched automatically
        tensorboard = None
        if self.configuration["training"]["USE_TENSORBOARD"]:
            tensorboard = self.callback_wrapper.tensorboard_callback(checkpoint_path, model)            
               
        # Training loop for each episode 
        scores = None       
        for episode in range(start_episode, episodes):                    
            state = environment.reset()
            state = np.reshape(state, newshape=(1, state_size))
            total_reward = 0
            for time_step in range(environment.max_steps):
                logger.info(f'Timestep {time_step + 1} - Episode {episode+1}/{episodes}')   
                # action is always performed using the Q model
                action = agent.act(model, state)
                next_state, reward, done, info, extraction = environment.step(action)
                total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])

                # render environment 
                if environment.render_environment:               
                    environment.render(episode, time_step, action, extraction)

                # Remember experience
                agent.remember(state, action, reward, next_state, done)
                state = next_state

                # Perform replay if the memory size is sufficient
                # use both the Q model and the target model
                if len(agent.memory) > self.replay_size:
                    scores = agent.replay(model, target_model, self.batch_size)                    
                    self.update_session_stats(scores, episode, time_step, reward, total_reward)

                # call on_epoch_end method of selected callbacks             
                if tensorboard is not None and scores is not None:                    
                    tensorboard.on_epoch_end(epoch=episode, logs=scores)                

                # Update target network periodically
                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                if done:
                    logger.info(f"Episode {episode+1}/{episodes} - Time steps: {time_step+1} - Capital: {info['capital']} - Total Reward: {total_reward}")
                    break
                     
        return agent
 
    #--------------------------------------------------------------------------
    def train_model(self, model, target_model, data, checkpoint_path, from_checkpoint=False):

        environment = RouletteEnvironment(data, self.configuration)   
        agent = DQNAgent(self.configuration)

        # perform different initialization duties based on state of session:
        # training from scratch vs resumed training
        # calculate number of epochs taking into account possible training resumption
        if not from_checkpoint:               
            episodes = self.configuration['training']['EPISODES']
            from_episode = 0
            start_episode = 0
            history = None
        else:
            _, history = self.serializer.load_session_configuration(checkpoint_path)                     
            episodes = history['total_epochs'] + CONFIG['training']['ADDITIONAL_EPISODES'] 
            from_episode = history['total_epochs']
            start_episode = from_episode                    

        # determine state size as the observation space size       
        state_size = environment.observation_space.shape[0]         
        agent = self.reinforcement_learning_pipeline(model, target_model, agent, environment, 
                                                              start_episode, episodes, state_size, checkpoint_path)

        # Save the final model at the end of training
        self.serializer.save_pretrained_model(model, checkpoint_path)        
        self.serializer.save_session_configuration(checkpoint_path, history, self.configuration)


