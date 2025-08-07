import os
from keras import callbacks, Model
import webbrowser
import subprocess
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from FAIRS.app.interface.workers import WorkerInterrupted
from FAIRS.app.constants import CONFIG
from FAIRS.app.logger import logger


# [CALLBACK FOR UI PROGRESS BAR]
###############################################################################
class ProgressBarCallback(callbacks.Callback):
    def __init__(self, progress_callback, total_epochs, from_epoch=0):
        super().__init__()
        self.progress_callback = progress_callback
        self.total_epochs = total_epochs
        self.from_epoch = from_epoch

    #--------------------------------------------------------------------------
    def on_epoch_end(self, epoch, logs=None):
        processed_epochs = epoch - self.from_epoch + 1        
        additional_epochs = max(1, self.total_epochs - self.from_epoch) 
        percent = int(100 * processed_epochs / additional_epochs)
        if self.progress_callback is not None:
            self.progress_callback(percent)


# [CALLBACK FOR TRAIN INTERRUPTION]
###############################################################################
class LearningInterruptCallback(callbacks.Callback):
    def __init__(self, worker=None):
        super().__init__()
        self.worker = worker

    #--------------------------------------------------------------------------
    def on_batch_end(self, batch, logs=None):
        if self.worker is not None and self.worker.is_interrupted():            
            self.model.stop_training = True
            raise WorkerInterrupted()
        
    #--------------------------------------------------------------------------
    def on_validation_batch_end(self, batch, logs=None):
        if self.worker is not None and self.worker.is_interrupted():
            raise WorkerInterrupted()

    
# [CALLBACK FOR REAL TIME TRAINING MONITORING]
###############################################################################
class RealTimeHistory(callbacks.Callback):    
        
    def __init__(self, plot_path, past_logs=None, **kwargs):
        super(RealTimeHistory, self).__init__(**kwargs)
        self.plot_path = plot_path
        os.makedirs(self.plot_path, exist_ok=True)
        # Separate dicts for training vs. validation metrics
        self.total_epochs = 0 if past_logs is None else past_logs.get('epochs', 0)
        self.history = {'history' : {},
                        'epochs' : self.total_epochs}        

        # If past_logs provided, split into history and val_history
        if past_logs and 'history' in past_logs:
            for metric, values in past_logs['history'].items():
                self.history['history'][metric] = list(values)
            self.history['epochs'] = past_logs.get('epochs', len(values))                
                    
    #--------------------------------------------------------------------------
    def on_epoch_end(self, epoch, logs=None):
        if not logs:
            return
        
        for key, value in logs.items():
            if key not in self.history['history']:
                self.history['history'][key] = []
            self.history['history'][key].append(value)
        self.history['epochs'] = epoch + 1
        self.plot_training_history()

    #--------------------------------------------------------------------------
    def plot_training_history(self):
        fig_path = os.path.join(self.plot_path, 'training_history.jpeg')
        plt.figure(figsize=(16, 14)) 
        metrics = self.history['history']
        # Find unique base metric names 
        base_metrics = sorted(set(
            m[4:] if m.startswith('val_') else m
            for m in metrics.keys()))

        plt.figure(figsize=(16, 5 * len(base_metrics)))
        for i, base in enumerate(base_metrics):
            plt.subplot(len(base_metrics), 1, i + 1)
            # Plot training metric
            if base in metrics:
                plt.plot(metrics[base], label='train')
            # Plot validation metric if exists
            val_key = f'val_{base}'
            if val_key in metrics:
                plt.plot(metrics[val_key], label='val')
            plt.title(base)
            plt.ylabel('')
            plt.xlabel('Epoch')
            plt.legend(loc='best', fontsize=10)

        plt.tight_layout()
        plt.savefig(fig_path, bbox_inches='tight', format='jpeg', dpi=300)
        plt.close()

###############################################################################
class GameStatsCallback(callbacks.Callback):
    
    def __init__(self, plot_path, plot_freq_steps=1, iterations=None, capitals=None, **kwargs): 
        super(GameStatsCallback, self).__init__(**kwargs)     
        self.plot_path = os.path.join(plot_path, 'game_statistics.jpeg')  
        self.plot_freq_steps = max(1, plot_freq_steps) 
        os.makedirs(plot_path, exist_ok=True)

        self.iterations = [] if iterations is None else iterations
        self.capitals = [] if capitals is None else capitals
        self.episode_end_indices = []
        self.global_step = 0
        self.episode_count = 0

    #--------------------------------------------------------------------------
    def reset_state(self):
        self.iterations = []
        self.capitals = []
        self.episode_end_indices = []
        self.global_step = 0
        self.episode_count = 0

    #--------------------------------------------------------------------------
    def on_train_begin(self, logs=None):
        self.reset_state()
       
    #--------------------------------------------------------------------------
    def on_batch_end(self, batch, logs=None):
        if not logs:
            return
        
        current_capital = logs.get('current_capital', None)
        done = logs.get('done', False)

        # Only log if current_capital is present (can skip if not provided)
        if current_capital is not None:
            self.iterations.append(self.global_step)
            self.capitals.append(current_capital)

        if done:
            self.episode_end_indices.append(self.global_step)
            self.episode_count += 1

        self.global_step += 1

        if self.global_step > 0 and self.global_step % self.plot_freq_steps == 0:
            self.plot_and_save(self.global_step)
        

    #--------------------------------------------------------------------------
    def on_epoch_end(self, epoch, logs=None):
        if not logs:
            return
        
        self.plot_and_save(self.global_step)        

    #--------------------------------------------------------------------------
    def on_train_end(self, logs=None):
        if not logs:
            return
        
        self.plot_and_save(self.global_step)

    #--------------------------------------------------------------------------
    def plot_and_save(self, current_step):
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_xlabel('Iterations (Time Steps)')
        ax.set_ylabel('Value')
        series = ax.plot(
            self.iterations, self.capitals, color='blue', label='Current Capital', alpha=0.8)
        vline_handles = []
        if self.episode_end_indices:
            first_marker = True
            for index in self.episode_end_indices:
                label = 'Episode End' if first_marker else ""
                vline = ax.axvline(x=index, color='grey', linestyle='--', alpha=0.6, label=label)
                if first_marker:
                    vline_handles.append(vline)
                    first_marker = False
        lines = series + vline_handles
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3)
        fig.suptitle(f'Training Progress: Capital (At step {current_step})')
        fig.tight_layout(rect=[0, 0.1, 1, 0.95])
        plt.savefig(self.plot_path, bbox_inches='tight', format='jpeg', dpi=300)
        plt.close(fig)


# [CALLBACKS HANDLER]
###############################################################################
def initialize_callbacks_handler(model : Model, configuration : dict, checkpoint_path, session=None,
                                 total_epochs=100, **kwargs) -> callbacks.CallbackList:    
    from_epoch = 0  
    additional_epochs = configuration.get('additional_epochs', 10)
    if session:
        from_epoch = session['epochs']
        total_epochs = additional_epochs + from_epoch

    callbacks_list = [
        LearningInterruptCallback(kwargs.get('worker', None))]      
    
    if configuration.get('plot_training_metrics', False):
        callbacks_list.append(RealTimeHistory(checkpoint_path, past_logs=session))        
        callbacks_list.append(GameStatsCallback(checkpoint_path, 50))

    if configuration.get('use_tensorboard', False):
        logger.debug('Using tensorboard during training')
        log_path = os.path.join(checkpoint_path, 'tensorboard')
        tb_callback = callbacks.TensorBoard(log_dir=log_path, histogram_freq=1) 
        tb_callback.set_model(model) # need to set the model since model.fit() is not called          
        start_tensorboard_subprocess(log_path)      

    if configuration.get('save_checkpoints', False):
        logger.debug('Adding checkpoint saving callback')
        checkpoint_filepath = os.path.join(checkpoint_path, 'model_checkpoint_E{epoch:02d}.keras')
        callbacks_list.append(callbacks.ModelCheckpoint(
            filepath=checkpoint_filepath, save_weights_only=False,  
            monitor='val_loss', save_best_only=False, mode='auto', verbose=0))
        
    cb_list = callbacks.CallbackList(callbacks_list, add_history=False, model=model)
        
    return cb_list


###############################################################################
def start_tensorboard_subprocess(log_dir):    
    tensorboard_command = ["tensorboard", "--logdir", log_dir, "--port", "6006"]
    subprocess.Popen(
        tensorboard_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)      
    time.sleep(5)            
    webbrowser.open("http://localhost:6006")       
        


    