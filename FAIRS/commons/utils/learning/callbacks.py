import os
import keras
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import webbrowser
import subprocess
import time

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

    
# [CALLBACK FOR REAL TIME TRAINING MONITORING]
###############################################################################
class RealTimeHistory(keras.callbacks.Callback):    
        
    def __init__(self, plot_path, past_logs=None, **kwargs):
        super(RealTimeHistory, self).__init__(**kwargs)
        self.plot_path = plot_path 
        self.past_logs = past_logs       
                       
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
        fig_path = os.path.join(self.plot_path, 'training_history.jpeg')
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
        plt.savefig(fig_path, bbox_inches='tight', format='jpeg', dpi=300)       
        plt.close()


# [LOGGING]
###############################################################################
class LoggingCallback(keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        if logs is not None:
            logger.debug(f"Epoch {epoch + 1}: {logs}")





# add logger callback for the training session
###############################################################################
class CallbacksWrapper:

    def __init__(self, configuration):
        self.configuration = configuration

    #--------------------------------------------------------------------------
    def real_time_history(self, configuration, checkpoint_path, history):
        RTH_callback = RealTimeHistory(checkpoint_path, configuration, past_logs=history)
        logger_callback = LoggingCallback()          
        
        return RTH_callback, logger_callback
    
    #--------------------------------------------------------------------------
    def _start_tensorboard(self, log_dir):    
        tensorboard_command = ["tensorboard", "--logdir", log_dir, "--port", "6006"]
        subprocess.Popen(tensorboard_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)      
        time.sleep(4)            
        webbrowser.open("http://localhost:6006")  

    #--------------------------------------------------------------------------
    def tensorboard_callback(self, checkpoint_path, model) -> keras.callbacks.TensorBoard:        
        logger.debug('Using tensorboard during training')
        log_path = os.path.join(checkpoint_path, 'tensorboard')
        tb_callback = keras.callbacks.TensorBoard(log_dir=log_path, update_freq=20, 
                                         histogram_freq=1) 

        tb_callback.set_model(model)              
        self._start_tensorboard(log_path)        

        return tb_callback 
    
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
    
   


