import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
import keras

from FAIRS.app.utils.data.database import FAIRSDatabase
from FAIRS.app.constants import CONFIG, DATA_PATH, METADATA_PATH, CHECKPOINT_PATH
from FAIRS.app.logger import logger



###############################################################################
def checkpoint_selection_menu(models_list):

    index_list = [idx + 1 for idx, item in enumerate(models_list)]     
    print('Currently available pretrained models:')             
    for i, directory in enumerate(models_list):
        print(f'{i + 1} - {directory}')                         
    while True:
        try:
            selection_index = int(input('\nSelect the pretrained model: '))
            print()
        except ValueError:
            logger.error('Invalid choice for the pretrained model, asking again')
            continue
        if selection_index in index_list:
            break
        else:
            logger.warning('Model does not exist, please select a valid index')

    return selection_index


# [DATA SERIALIZATION]
###############################################################################
class DataSerializer:

    def __init__(self, configuration):         
        self.metadata_path = os.path.join(METADATA_PATH, 'preprocessing_metadata.json')    
        self.database = FAIRSDatabase(configuration)  
        self.seed = configuration['SEED']
        self.parameters = configuration['dataset']          
        self.configuration = configuration

    #--------------------------------------------------------------------------
    def load_roulette_dataset(self, sample_size=None):        
        dataset = self.database.load_source_data_table()
        sample_size = self.parameters["SAMPLE_SIZE"] if sample_size is None else sample_size        
        dataset = dataset.sample(frac=sample_size, random_state=self.seed)     

        return dataset

    #--------------------------------------------------------------------------
    def save_preprocessed_data(self, processed_data):               
        self.database.save_preprocessed_data_table(processed_data)      
        metadata = {'seed' : self.configuration['SEED'], 
                    'dataset' : self.configuration['dataset'],
                    'date' : datetime.now().strftime("%Y-%m-%d")}
                
        with open(self.metadata_path, 'w') as file:
            json.dump(metadata, file, indent=4)     

    #--------------------------------------------------------------------------
    def load_processed_data(self):         
        processed_data = self.database.load_processed_data_table()     

        with open(self.metadata_path, 'r') as file:
            metadata = json.load(file)        
       
        return processed_data, metadata 
        
           

    
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
        os.makedirs(os.path.join(checkpoint_path, 'data'), exist_ok=True)
        logger.debug(f'Created checkpoint folder at {checkpoint_path}')
        
        return checkpoint_path    

    #--------------------------------------------------------------------------
    def save_pretrained_model(self, model : keras.Model, path):
        model_files_path = os.path.join(path, 'saved_model.keras')
        model.save(model_files_path)
        logger.info(f'Training session is over. Model {os.path.basename(path)} has been saved')

    #--------------------------------------------------------------------------
    def save_training_configuration(self, path, history : dict, configuration : dict, metadata : dict):         
        os.makedirs(os.path.join(path, 'configuration'), exist_ok=True)         
        config_path = os.path.join(path, 'configuration', 'configuration.json')
        metadata_path = os.path.join(path, 'configuration', 'metadata.json')     
        history_path = os.path.join(path, 'configuration', 'session_history.json')        

        # Save training and model configuration
        with open(config_path, 'w') as f:
            json.dump(configuration, f) 

        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)      

        # Save session history
        with open(history_path, 'w') as f:
            json.dump(history, f)

        logger.debug(f'Model configuration, session history and metadata saved for {os.path.basename(path)}')

    #--------------------------------------------------------------------------
    def load_training_configuration(self, path): 
        config_path = os.path.join(path, 'configuration', 'configuration.json')
        metadata_path = os.path.join(path, 'configuration', 'metadata.json') 
        history_path = os.path.join(path, 'configuration', 'session_history.json') 
        
        with open(config_path, 'r') as f:
            configuration = json.load(f) 
   
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)        

        with open(history_path, 'r') as f:
            history = json.load(f)

        return configuration, metadata, history  

    #-------------------------------------------------------------------------- 
    def scan_checkpoints_folder(self):
        model_folders = []
        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():
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
    def load_checkpoint(self, checkpoint_name : str):
        checkpoint_path = os.path.join(CHECKPOINT_PATH, checkpoint_name)
        model_path = os.path.join(checkpoint_path, 'saved_model.keras') 
        model = load_model(model_path) 
        
        return model
            
    #-------------------------------------------------------------------------- 
    def select_and_load_checkpoint(self):
        # look into checkpoint folder to get pretrained model names      
        model_folders = self.scan_checkpoints_folder()
        # quit the script if no pretrained models are found 
        if len(model_folders) == 0:
            logger.error('No pretrained model checkpoints in resources')
            sys.exit()

        # select model if multiple checkpoints are available
        if len(model_folders) > 1:
            selection_index = checkpoint_selection_menu(model_folders)                    
            checkpoint_path = os.path.join(
                CHECKPOINT_PATH, model_folders[selection_index-1])

        # load directly the pretrained model if only one is available 
        elif len(model_folders) == 1:
            checkpoint_path = os.path.join(CHECKPOINT_PATH, model_folders[0])
            logger.info(f'Since only checkpoint {os.path.basename(checkpoint_path)} is available, it will be loaded directly')
                          
        # effectively load the model using keras builtin method
        # load configuration data from .json file in checkpoint folder
        model = self.load_checkpoint(checkpoint_path)       
        configuration, metadata, history = self.load_training_configuration(checkpoint_path)           
            
        return model, configuration, metadata, checkpoint_path

             
    