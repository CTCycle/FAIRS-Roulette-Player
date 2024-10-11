import os
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

        self.state_size = configuration["dataset"]["WINDOW_SIZE"]
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
            return np.random.randrange(self.action_size)  
        q_values = self.model.predict(state)
        return np.argmax(q_values[0])  

    #--------------------------------------------------------------------------
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    #--------------------------------------------------------------------------
    def replay(self, batch_size):
        minibatch = np.random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


# [TOOLS FOR TRAINING MACHINE LEARNING MODELS]
###############################################################################
class DQNTraining:
    def __init__(self, configuration):
        
        self.environment = RouletteEnvironment(configuration)
        self.configuration = configuration
        self.episodes = configuration['training']['EPISODES']
        self.batch_size = configuration['training']['BATCH_SIZE']        
        
        np.random.seed(configuration["SEED"])
        torch.manual_seed(configuration["SEED"])
        tf.random.set_seed(configuration["SEED"])
        self.device = torch.device('cpu')
        self.scaler = GradScaler() if self.configuration["training"]["MIXED_PRECISION"] else None
        self.set_device()                

    # set device
    #--------------------------------------------------------------------------
    def set_device(self):
        if CONFIG["training"]["ML_DEVICE"] == 'GPU':
            if not torch.cuda.is_available():
                logger.info('No GPU found. Falling back to CPU')
                self.device = torch.device('cpu')
            else:
                self.device = torch.device('cuda:0')                
                if self.configuration["training"]["MIXED_PRECISION"]:
                    keras.mixed_precision.set_global_policy("mixed_float16")
                    logger.info('Mixed precision policy is active during training')
                torch.cuda.set_device(self.device)
                logger.info('GPU is set as active device')
        elif self.configuration["training"]["ML_DEVICE"] == 'CPU':
            self.device = torch.device('cpu')
            logger.info('CPU is set as active device')             
        else:
            logger.error(f'Unknown ML_DEVICE value: {self.configuration["training"]["ML_DEVICE"]}')
            self.device = torch.device('cpu')

    #--------------------------------------------------------------------------
    def train_model(self, model, train_data, validation_data, checkpoint_path, from_checkpoint=False):

        # Initialize training parameters
        current_checkpoint_path = checkpoint_path
        serializer = ModelSerializer()  

        agent = DQNAgent(model, self.configuration)

        if from_checkpoint:
            # Load previous session if training is resumed from a checkpoint
            _, history = serializer.load_session_configuration(current_checkpoint_path)
            total_epochs = history['total_epochs']
            epochs = total_epochs + CONFIG["training"]["ADDITIONAL_EPOCHS"]
            start_episode = total_epochs
        else:
            epochs = self.configuration['training']['EPOCHS']
            start_episode = 0

        # Initialize environment and agent's states
        state_size = self.environment.observation_space.shape[0]
        action_size = self.environment.action_space.n

        # Setup callbacks
        rth_callback = RealTimeHistory(current_checkpoint_path, past_logs=history)
        logger_callback = LoggingCallback()
        callbacks_list = [rth_callback, logger_callback]

        if CONFIG["training"]["USE_TENSORBOARD"]:
            log_dir = os.path.join(current_checkpoint_path, 'tensorboard')
            callbacks_list.append(keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1))

        # Training loop for each episode
        for episode in range(start_episode, self.episodes):
            state = self.environment.reset()
            state = np.reshape(state, [1, state_size])
            total_reward = 0

            for time_step in range(self.environment.max_steps):
                action = agent.act(state)
                next_state, reward, done, info = self.environment.step(action)
                total_reward += reward
                next_state = np.reshape(next_state, [1, state_size])

                # Remember experience
                agent.remember(state, action, reward, next_state, done)
                state = next_state

                # Perform replay if the memory size is sufficient
                if len(agent.memory) > self.batch_size:
                    agent.replay(self.batch_size)

                if done:
                    print(f"Episode {episode+1}/{self.episodes} - Time steps: {time_step+1} - Capital: {info['capital']} - Total Reward: {total_reward}")
                    break

            # Save progress at checkpoints (you can define a frequency or save every episode)
            if episode % self.configuration['training']['SAVE_FREQUENCY'] == 0:
                print(f"Saving model at episode {episode}")
                serializer.save_pretrained_model(agent.model, current_checkpoint_path)
                history = {'history': rth_callback.history, 'val_history': rth_callback.val_history, 'total_epochs': episode}
                serializer.save_session_configuration(current_checkpoint_path, history, self.configuration)

        # Save the final model at the end of training
        serializer.save_pretrained_model(agent.model, current_checkpoint_path)
        history = {'history': rth_callback.history, 'val_history': rth_callback.val_history, 'total_epochs': self.episodes}
        serializer.save_session_configuration(current_checkpoint_path, history, self.configuration)

        # Optional: Run validation if applicable
        if validation_data is not None:
            val_loss = model.evaluate(validation_data)
            print(f"Validation loss: {val_loss}")



