import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
import keras

from FAIRS.commons.constants import CONFIG, DATA_PATH, PRED_PATH, DATASET_NAME, CHECKPOINT_PATH
from FAIRS.commons.logger import logger



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


# get FAIRS data for training
###############################################################################
def get_training_dataset(sample_size=None):     

    if sample_size is None:
        sample_size =  CONFIG["dataset"]["SAMPLE_SIZE"]
    file_loc = os.path.join(DATA_PATH, DATASET_NAME) 
    dataset = pd.read_csv(file_loc, encoding='utf-8', sep=';')
    num_samples = int(dataset.shape[0] * sample_size)
    dataset = dataset[(dataset.shape[0] - num_samples):]

    return dataset

# get FAIRS data for predictions
###############################################################################
def get_predictions_dataset():

    file_loc = os.path.join(PRED_PATH, 'FAIRS_predictions.csv') 
    dataset = pd.read_csv(file_loc, encoding='utf-8', sep=';')    

    return dataset
    

# [DATA SERIALIZATION]
###############################################################################
class DataSerializer:

    def __init__(self):        
        self.data_config = CONFIG["dataset"] 
        
           

    
# [MODEL SERIALIZATION]
###############################################################################
class ModelSerializer:

    def __init__(self):
        self.model_name = 'FAIRS'

    # function to create a folder where to save model checkpoints
    #--------------------------------------------------------------------------
    def create_checkpoint_folder(self):

        '''
        Creates a folder with the current date and time to save the model.

        Keyword arguments:
            None

        Returns:
            str: A string containing the path of the folder where the model will be saved.
        
        '''        
        today_datetime = datetime.now().strftime('%Y%m%dT%H%M%S')        
        checkpoint_folder_path = os.path.join(CHECKPOINT_PATH, f'{self.model_name}_{today_datetime}')         
        os.makedirs(checkpoint_folder_path, exist_ok=True)        
        os.makedirs(os.path.join(checkpoint_folder_path, 'data'), exist_ok=True)
        logger.debug(f'Created checkpoint folder at {checkpoint_folder_path}')
        
        return checkpoint_folder_path 

    #--------------------------------------------------------------------------
    def save_pretrained_model(self, model : keras.Model, path):

        model_files_path = os.path.join(path, 'saved_model.keras')
        model.save(model_files_path)
        logger.info(f'Training session is over. Model has been saved in folder {path}')

    #--------------------------------------------------------------------------
    def save_session_configuration(self, path, history : dict, configurations : dict):

        '''
        Saves the model parameters to a JSON file. The parameters are provided 
        as a dictionary and are written to a file named 'model_parameters.json' 
        in the specified directory.

        Keyword arguments:
            parameters_dict (dict): A dictionary containing the parameters to be saved.
            path (str): The directory path where the parameters will be saved.

        Returns:
            None  

        '''
        config_folder = os.path.join(path, 'configurations')
        os.makedirs(config_folder, exist_ok=True)

        # Paths to the JSON files
        config_path = os.path.join(config_folder, 'configurations.json')
        history_path = os.path.join(config_folder, 'session_history.json')

        # Function to merge dictionaries
        def merge_dicts(original, new_data):
            for key, value in new_data.items():
                if key in original:
                    if isinstance(value, dict) and isinstance(original[key], dict):
                        merge_dicts(original[key], value)
                    elif isinstance(value, list) and isinstance(original[key], list):
                        original[key].extend(value)
                    else:
                        original[key] = value
                else:
                    original[key] = value    

        # Save the merged configurations
        with open(config_path, 'w') as f:
            json.dump(configurations, f)

        # Load existing session history if the file exists and merge
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                existing_history = json.load(f)
            merge_dicts(existing_history, history)
        else:
            existing_history = history

        # Save the merged session history
        with open(history_path, 'w') as f:
            json.dump(existing_history, f)

        logger.debug(f'Model configuration and session history have been saved and merged at {path}')      

    #--------------------------------------------------------------------------
    def load_session_configuration(self, path): 

        config_path = os.path.join(path, 'configurations', 'configurations.json')        
        with open(config_path, 'r') as f:
            configurations = json.load(f)        

        history_path = os.path.join(path, 'configurations', 'session_history.json')
        with open(history_path, 'r') as f:
            history = json.load(f)

        return configurations, history  

    #-------------------------------------------------------------------------- 
    def scan_checkpoints_folder(self):
        model_folders = []
        for entry in os.scandir(CHECKPOINT_PATH):
            if entry.is_dir():
                model_folders.append(entry.name)
        
        return model_folders 

    #--------------------------------------------------------------------------
    def save_model_plot(self, model, path):

        if CONFIG["model"]["SAVE_MODEL_PLOT"]:
            logger.debug('Generating model architecture graph')
            plot_path = os.path.join(path, 'model_layout.png')       
            keras.utils.plot_model(model, to_file=plot_path, show_shapes=True, 
                       show_layer_names=True, show_layer_activations=True, 
                       expand_nested=True, rankdir='TB', dpi=400)
            
    #--------------------------------------------------------------------------
    def load_checkpoint(self, checkpoint_name):           

        model_folder_path = os.path.join(CHECKPOINT_PATH, checkpoint_name)
        model_path = os.path.join(model_folder_path, 'saved_model.keras') 
        model = keras.models.load_model(model_path) 
        
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
            checkpoint_path = os.path.join(CHECKPOINT_PATH, model_folders[selection_index-1])

        # load directly the pretrained model if only one is available 
        elif len(model_folders) == 1:
            checkpoint_path = os.path.join(CHECKPOINT_PATH, model_folders[0])
            logger.info(f'Since only checkpoint {os.path.basename(checkpoint_path)} is available, it will be loaded directly')
                          
        # effectively load the model using keras builtin method
        # load configuration data from .json file in checkpoint folder
        model = self.load_checkpoint(checkpoint_path)       
        configuration, history = self.load_session_configuration(checkpoint_path)           
            
        return model, configuration, history, checkpoint_path

             
    