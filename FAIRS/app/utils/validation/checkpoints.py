import os
import pandas as pd
import numpy as np
from keras import Model

from FAIRS.app.utils.learning.callbacks import LearningInterruptCallback
from FAIRS.app.utils.data.serializer import DataSerializer, ModelSerializer
from FAIRS.app.interface.workers import check_thread_status, update_progress_callback
from FAIRS.app.constants import CONFIG, CHECKPOINT_PATH, DATA_PATH
from FAIRS.app.logger import logger



# [LOAD MODEL]
################################################################################
class ModelEvaluationSummary:

    def __init__(self, configuration : dict):         
        self.configuration = configuration

    #---------------------------------------------------------------------------
    def scan_checkpoint_folder(self):
        model_paths = []
        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():                
                pretrained_model_path = os.path.join(entry.path, 'saved_model.keras')                
                if os.path.isfile(pretrained_model_path):
                    model_paths.append(entry.path)                

        return model_paths  

    #---------------------------------------------------------------------------
    def get_checkpoints_summary(self, **kwargs):
        modser = ModelSerializer() 
        serializer = DataSerializer(self.configuration)             
        model_paths = self.scan_checkpoint_folder()
        model_parameters = []            
        for i, model_path in enumerate(model_paths):            
            model = modser.load_checkpoint(model_path)
            configuration, history = modser.load_training_configuration(model_path)
            model_name = os.path.basename(model_path)                   
            precision = 16 if configuration.get("use_mixed_precision", np.nan) else 32 
            has_scheduler = configuration.get('use_scheduler', False)
            scores = history.get('history', {})
            chkp_config = {
                    'checkpoint': model_name,
                    'sample_size': configuration.get('sample_size', np.nan),
                    'validation_size': configuration.get('validation_size', np.nan),
                    'seed': configuration.get('train_seed', np.nan),
                    'precision': precision,
                    'epochs': history.get('epochs', np.nan),                    
                    'batch_size': configuration.get('batch_size', np.nan),
                    'split_seed': configuration.get('split_seed', np.nan),
                    'image_augmentation': configuration.get('img_augmentation', np.nan),
                    'image_height': 128,  
                    'image_width': 128,
                    'image_channels': 3,
                    'jit_compile': configuration.get('jit_compile', np.nan),
                    'has_tensorboard_logs': configuration.get('use_tensorboard', np.nan),
                    'initial_LR': configuration.get('initial_LR', np.nan),
                    'constant_steps_LR': configuration.get('constant_steps', np.nan) if has_scheduler else np.nan,
                    'decay_steps_LR': configuration.get('decay_steps', np.nan) if has_scheduler else np.nan,
                    'target_LR': configuration.get('target_LR', np.nan) if has_scheduler else np.nan,                    
                    'initial_neurons': configuration.get('initial_neurons', np.nan),
                    'dropout_rate': configuration.get('dropout_rate', np.nan),
                    'train_loss': scores.get('loss', [np.nan])[-1], 
                    'val_loss': scores.get('val_loss', [np.nan])[-1],
                    'train_cosine_similarity': scores.get('cosine_similarity', [np.nan])[-1], 
                    'val_cosine_similarity': scores.get('val_cosine_similarity', [np.nan])[-1]}
            
            model_parameters.append(chkp_config)

            # check for thread status and progress bar update   
            check_thread_status(kwargs.get('worker', None))         
            update_progress_callback(
                i+1, len(model_paths), kwargs.get('progress_callback', None)) 

        dataframe = pd.DataFrame(model_parameters)
        serializer.save_checkpoints_summary(dataframe)    
            
        return dataframe
    
    #--------------------------------------------------------------------------
    def get_evaluation_report(self, model : Model, validation_dataset, **kwargs):
        callbacks_list = [LearningInterruptCallback(kwargs.get('worker', None))]
        validation = model.evaluate(validation_dataset, verbose=1, callbacks=callbacks_list) 
        logger.info(f'Evaluation of pretrained model has been completed')   
        logger.info(f'RMSE loss {validation[0]:.3f}')
        logger.info(f'Cosine similarity {validation[1]:.3f}') 