import numpy as np
import keras
import torch
from tqdm import tqdm

from FAIRS.commons.utils.data.serializer import ModelSerializer
from FAIRS.commons.utils.learning.callbacks import CallbacksWrapper
from FAIRS.commons.utils.learning.environment import RouletteEnvironment
from FAIRS.commons.utils.learning.agents import DQNAgent
from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNTraining:

    def __init__(self, configuration, metadata):     
        keras.utils.set_random_seed(configuration["SEED"])         
        self.batch_size = configuration['training']['BATCH_SIZE']        
        self.update_frequency = configuration['training']['UPDATE_FREQUENCY'] 
        self.replay_size = configuration['agent']['REPLAY_BUFFER']           
        self.selected_device = CONFIG["device"]["DEVICE"]
        self.device_id = CONFIG["device"]["DEVICE_ID"]
        self.mixed_precision = CONFIG["device"]["MIXED_PRECISION"]  
        self.configuration = configuration 
        self.metadata = metadata 

        # initialize variables        
        self.game_stats_frequency = 50
        self.callback_wrapper = CallbacksWrapper(configuration) 
        self.serializer = ModelSerializer()           
        self.agent = DQNAgent(self.configuration) 
        self.session_stats = {'episode': [],
                              'time_step': [],
                              'loss': [],
                              'metrics': [],
                              'reward': [],
                              'total_reward': []}                

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

    # set device
    #--------------------------------------------------------------------------
    def update_session_stats(self, scores, episode, time_step, reward, total_reward):
        loss = scores.get('loss', None)
        metric = scores.get('root_mean_squared_error', None)                   
        self.session_stats['episode'].append(episode)
        self.session_stats['time_step'].append(time_step)
        self.session_stats['loss'].append(loss.item() if loss is not None else 0.0)
        self.session_stats['metrics'].append(metric.item() if metric is not None else 0.0)
        self.session_stats['reward'].append(reward)
        self.session_stats['total_reward'].append(total_reward)   

    #--------------------------------------------------------------------------
    def train_with_reinforcement_learning(self, model : keras.Model, target_model : keras.Model,
                                          environment : RouletteEnvironment, start_episode, 
                                          episodes, state_size, checkpoint_path):
        # if tensorboard is selected, an instance of the tb callback is built
        # the dashboard is set on the Q model and tensorboard is launched automatically
        tensorboard = None
        game_statistics = self.callback_wrapper.game_stats_callback(
            checkpoint_path, plot_freq_steps=self.game_stats_frequency)
        real_time_history = self.callback_wrapper.real_time_history(
            self.configuration, checkpoint_path, history=self.session_stats)
        if self.configuration["training"]["USE_TENSORBOARD"]:
            tensorboard = self.callback_wrapper.tensorboard_callback(
                checkpoint_path, model)            
               
        # Training loop for each episode 
        scores = None             
        for i, episode in enumerate(range(start_episode, episodes)): 
            start_over = True if i == 0 else False                                
            state = environment.reset(start_over=start_over)
            state = np.reshape(state, newshape=(1, state_size))
            total_reward = 0
            for time_step in range(environment.max_steps):          
                gain = environment.capital/environment.initial_capital
                gain = np.reshape(gain, newshape=(1, 1)) 
                # action is always performed using the Q model
                action = self.agent.act(model, state, gain)
                next_state, reward, done, extraction = environment.step(action)
                total_reward += reward                
                next_state = np.reshape(next_state, [1, state_size])

                # render environment 
                if environment.render_environment:               
                    environment.render(episode, time_step, action, extraction)

                # Remember experience
                self.agent.remember(state, action, reward, gain, next_state, done)
                state = next_state

                # Perform replay if the memory size is sufficient
                # use both the Q model and the target model
                if len(self.agent.memory) > self.replay_size:
                    scores = self.agent.replay(
                        model, target_model, environment, self.batch_size)                   
                    self.update_session_stats(
                        scores, episode, time_step, reward, total_reward)
                    if time_step % 10 == 0:
                        logger.info(
                            f'Loss: {scores["loss"]} | RMSE: {scores["root_mean_squared_error"]}') 
                        logger.info(
                            f'Episode {episode+1}/{episodes} - Time steps: {time_step} - Capital: {environment.capital} - Total Reward: {total_reward}')                             

                # call on_epoch_end method of selected callbacks             
                if tensorboard is not None and scores is not None:                    
                    tensorboard.on_epoch_end(epoch=episode, logs=scores) 

                # Update plot with game statistics
                game_statistics.log_step(environment.capital, done)              

                # Update target network periodically
                if time_step % self.update_frequency == 0:
                    target_model.set_weights(model.get_weights())

                if done:
                    break
                     
        return self.agent 
 
    #--------------------------------------------------------------------------
    def train_model(self, model, target_model, data, checkpoint_path, from_checkpoint=False):
        environment = RouletteEnvironment(data, self.configuration)
        # perform different initialization duties based on state of session:
        # training from scratch vs resumed training
        # calculate number of epochs taking into account possible training resumption
        if not from_checkpoint:               
            episodes = self.configuration['training']['EPISODES']
            from_episode = 0
            start_episode = 0
            history = None
        else:
            _, self.metadata, history = self.serializer.load_training_configuration(checkpoint_path)                     
            episodes = history['total_episodes'] + CONFIG['training']['ADDITIONAL_EPISODES'] 
            from_episode = history['total_episodes']
            start_episode = from_episode                          

        # determine state size as the observation space size       
        state_size = environment.observation_space.shape[0] 
        logger.info(f'Size of the observation space (previous extractions): {state_size}')        
        agent = self.train_with_reinforcement_learning(
            model, target_model, environment, start_episode, episodes, 
            state_size, checkpoint_path)
        
        # use the real time history callback data to retrieve current loss and metric values
        # this allows to correctly resume the training metrics plot if training from checkpoint
        history = {'history' : self.session_stats, 
                   'val_history' : None,
                   'total_episodes' : episodes}

        # Save the final model at the end of training
        self.serializer.save_pretrained_model(model, checkpoint_path)
        # serialize training memory using pickle
        self.agent.dump_memory(checkpoint_path)    
        self.serializer.save_training_configuration(
            checkpoint_path, history, self.configuration, self.metadata)


