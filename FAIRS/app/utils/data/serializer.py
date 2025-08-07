import os
import sys
import json
import numpy as np
import pandas as pd
from keras import Model
from keras.utils import plot_model
from keras.models import load_model
from datetime import datetime

from FAIRS.app.utils.data.database import FAIRSDatabase
from FAIRS.app.constants import CONFIG, DATA_PATH, METADATA_PATH, CHECKPOINT_PATH
from FAIRS.app.logger import logger


# [DATA SERIALIZATION]
###############################################################################
class DataSerializer:

    def __init__(self, configuration : dict): 
        self.seed = configuration.get('seed', 42)
        # create database instance
        self.database = FAIRSDatabase()
        self.configuration = configuration

    #--------------------------------------------------------------------------
    def load_roulette_dataset(self, sample_size=1.0):        
        dataset = self.database.load_roulette_dataset()
        if sample_size < 1.0:            
            dataset = dataset.sample(frac=sample_size, random_state=self.seed)     

        return dataset
    
    #--------------------------------------------------------------------------
    def save_roulette_dataset(self, dataset : pd.DataFrame):        
        dataset = self.database.save_roulette_data(dataset)
        
        return dataset
    
    #--------------------------------------------------------------------------
    def save_checkpoints_summary(self, data : pd.DataFrame):            
        self.database.save_checkpoints_summary(data) 
           

    
# [MODEL SERIALIZATION]
###############################################################################
class ModelSerializer:

    def __init__(self):
        self.model_name = 'FAIRS'

    # function to create a folder where to save model checkpoints
    #--------------------------------------------------------------------------
    def create_checkpoint_folder(self):     
        today_datetime = datetime.now().strftime('%Y%m%dT%H%M%S')        
        checkpoint_path = os.path.join(
            CHECKPOINT_PATH, f'{self.model_name}_{today_datetime}')         
        os.makedirs(checkpoint_path, exist_ok=True)        
        os.makedirs(os.path.join(checkpoint_path, 'configuration'), exist_ok=True)
        logger.debug(f'Created checkpoint folder at {checkpoint_path}')
        
        return checkpoint_path  

    #------------------------------------------------------------------------
    def save_pretrained_model(self, model : Model, path : str):
        model_files_path = os.path.join(path, 'saved_model.keras')
        model.save(model_files_path)
        logger.info(f'Training session is over. Model {os.path.basename(path)} has been saved')

    #--------------------------------------------------------------------------
    def save_training_configuration(self, path, history : dict, configuration : dict): 
        config_path = os.path.join(path, 'configuration', 'configuration.json')
        history_path = os.path.join(path, 'configuration', 'session_history.json')        

        # Save training and model configuration
        with open(config_path, 'w') as f:
            json.dump(configuration, f) 
       
        # Save session history
        with open(history_path, 'w') as f:
            json.dump(history, f)

        logger.debug(f'Model configuration, session history and metadata saved for {os.path.basename(path)}')

    #--------------------------------------------------------------------------
    def load_training_configuration(self, path): 
        config_path = os.path.join(path, 'configuration', 'configuration.json')
        history_path = os.path.join(path, 'configuration', 'session_history.json')
        with open(config_path, 'r') as f:
            configuration = json.load(f) 

        with open(history_path, 'r') as f:
            history = json.load(f)

        return configuration, history  

    #-------------------------------------------------------------------------- 
    def scan_checkpoints_folder(self):
        model_folders = []
        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():
                # Check if the folder contains at least one .keras file
                has_keras = any(
                    f.name.endswith('.keras') and f.is_file()
                    for f in os.scandir(entry.path))
                if has_keras:
                    model_folders.append(entry.name)
                    
        return model_folders 

    #--------------------------------------------------------------------------
    def save_model_plot(self, model, path):        
        logger.debug('Generating model architecture graph')
        plot_path = os.path.join(path, 'model_layout.png')       
        plot_model(model, to_file=plot_path, show_shapes=True, 
                    show_layer_names=True, show_layer_activations=True, 
                    expand_nested=True, rankdir='TB', dpi=400)
            
    #--------------------------------------------------------------------------
    def load_checkpoint(self, checkpoint : str):
        # effectively load the model using keras builtin method
        # load configuration data from .json file in checkpoint folder
        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint) 
        model_path = os.path.join(checkpoint_path, 'saved_model.keras') 
        model = load_model(model_path)       
        configuration, session = self.load_training_configuration(checkpoint_path)        
            
        return model, configuration, session, checkpoint_path
            
    
             
    