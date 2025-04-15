import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import os
import keras
import webbrowser
import subprocess
import time

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
# [CALLBACK FOR REAL TIME TRAINING MONITORING]
###############################################################################
class RealTimeHistory:    
        
    def __init__(self, plot_path, past_logs=None):        
        self.plot_path = plot_path 
        self.past_logs = past_logs 
        self.fig_path = os.path.join(self.plot_path, 'training_history.jpeg')      
                       
        # Initialize dictionaries to store history 
        self.history = {}
        self.val_history = {}
        if past_logs is not None:
            self.history = past_logs['history']
            self.val_history = past_logs['val_history']      
        
        # Ensure plot directory exists
        os.makedirs(self.plot_path, exist_ok=True)
    
    #--------------------------------------------------------------------------
    def on_epoch_end(self, epoch, logs={}):
        # Log metrics and losses
        for key, value in logs.items():
            if key.startswith('val_'):
                if key not in self.val_history:
                    self.val_history[key] = []
                self.val_history[key].append(value)
            else:
                if key not in self.history:
                    self.history[key] = []
                self.history[key].append(value)
        
        self.plot_training_history()

    #--------------------------------------------------------------------------
    def plot_training_history(self):        
        plt.figure(figsize=(16, 14))      
        for i, (metric, values) in enumerate(self.history.items()):
            plt.subplot(len(self.history), 1, i + 1)
            plt.plot(range(len(values)), values, label=f'train')
            if f'val_{metric}' in self.val_history:
                plt.plot(range(len(self.val_history[f'val_{metric}'])), 
                         self.val_history[f'val_{metric}'], label=f'validation')
                plt.legend(loc='best', fontsize=8)
            plt.title(metric)
            plt.ylabel('')
            plt.xlabel('Epoch')
        
        plt.tight_layout()
        plt.savefig(self.fig_path, bbox_inches='tight', format='jpeg', dpi=300)       
        plt.close()


###############################################################################
class GameStatsCallback:
    
    def __init__(self, plot_path, plot_freq_steps=1, iterations=None, capitals=None):        
        self.plot_path = os.path.join(plot_path, 'game_statistics.jpeg')  
        self.plot_freq_steps = max(1, plot_freq_steps) 
        os.makedirs(plot_path, exist_ok=True)                
       
        self.iterations = [] if iterations is None else iterations
        self.capitals = [] if capitals is None else capitals  
        self.capitals = capitals
        self.episode_end_indices = []
       
        self.global_step = 0
        self.episode_count = 0
       
    #--------------------------------------------------------------------------
    def log_step(self, current_capital, done):        
        self.iterations.append(self.global_step)        
        self.capitals.append(current_capital)
  
        if done:
            self.episode_end_indices.append(self.global_step)
            self.episode_count += 1
        
        self.global_step += 1

        # Check if it's time to plot based on step frequency
        # We use global_step > 0 to avoid plotting at step 0
        if self.global_step > 0 and self.global_step % self.plot_freq_steps == 0:
             self.plot_and_save(self.global_step)    

    #--------------------------------------------------------------------------
    def plot_and_save(self, current_step):       
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Configure the single y-axis
        ax.set_xlabel('Iterations (Time Steps)')
        ax.set_ylabel('Value')   
        
        series = ax.plot(self.iterations, self.capitals, color='blue', label='Current Capital', alpha=0.8)
        
        # Add vertical lines for episode ends
        vline_handles = []
        if self.episode_end_indices:
            first_marker = True
            for index in self.episode_end_indices:
                label = 'Episode End' if first_marker else ""
                vline = ax.axvline(x=index, color='grey', linestyle='--', alpha=0.6, label=label)
                if first_marker:
                    vline_handles.append(vline)
                    first_marker = False
        
        # Create combined legend
        lines = series + vline_handles
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3)
        
        # Add a title and adjust layout
        fig.suptitle(f'Training Progress: Capital (At step {current_step})')
        fig.tight_layout(rect=[0, 0.1, 1, 0.95])
        
        # Save and close the figure
        plt.savefig(self.plot_path, bbox_inches='tight', format='jpeg', dpi=300)
        plt.close(fig)



# add logger callback for the training session
###############################################################################
class CallbacksWrapper:

    def __init__(self, configuration):
        self.configuration = configuration

    #--------------------------------------------------------------------------
    def real_time_history(self, configuration, checkpoint_path, history):
        RTH_callback = RealTimeHistory(checkpoint_path, configuration, past_logs=history)              
        
        return RTH_callback
    
    #--------------------------------------------------------------------------
    def start_tensorboard_subprocess(self, log_dir):    
        tensorboard_command = ["tensorboard", "--logdir", log_dir, "--port", "6006"]
        subprocess.Popen(
            tensorboard_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)      
        time.sleep(5)            
        webbrowser.open("http://localhost:6006")  

    #--------------------------------------------------------------------------
    def tensorboard_callback(self, checkpoint_path, model) -> keras.callbacks.TensorBoard:        
        logger.debug('Using tensorboard during training')
        log_path = os.path.join(checkpoint_path, 'tensorboard')
        tb_callback = keras.callbacks.TensorBoard(log_dir=log_path, histogram_freq=1) 
        tb_callback.set_model(model)              
        self.start_tensorboard_subprocess(log_path)        

        return tb_callback 
    
    #--------------------------------------------------------------------------
    def game_stats_callback(self, checkpoint_path, plot_freq_steps=1):          
        game_stats = GameStatsCallback(
            plot_path=checkpoint_path, plot_freq_steps=plot_freq_steps)
        return game_stats
    
    #--------------------------------------------------------------------------
    def checkpoints_saving(self, checkpoint_path):       
        logger.debug('Adding checkpoint saving callback')
        checkpoint_filepath = os.path.join(checkpoint_path, 'model_checkpoint.keras')
        chkp_save = keras.callbacks.ModelCheckpoint(filepath=checkpoint_filepath,
                                                    save_weights_only=True,  
                                                    monitor='loss',       
                                                    save_best_only=True,      
                                                    mode='auto',              
                                                    verbose=1)

        return chkp_save
    
    