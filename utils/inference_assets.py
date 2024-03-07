import os
import json
import numpy as np
import tensorflow as tf
from IPython.display import display
from ipywidgets import Dropdown

# [MODEL INFERENCE]
#============================================================================== 
# Methods for model validation
#==============================================================================
class Inference:


    def __init__(self, seed):
        self.seed = seed
        np.random.seed(seed)
        tf.random.set_seed(seed)    

    #-------------------------------------------------------------------------- 
    def load_pretrained_model(self, path):

        '''
        Load pretrained keras model (in folders) from the specified directory. 
        If multiple model directories are found, the user is prompted to select one,
        while if only one model directory is found, that model is loaded directly.
        If `load_parameters` is True, the function also loads the model parameters 
        from the target .json file in the same directory. 

        Keyword arguments:
            path (str): The directory path where the pretrained models are stored.
            load_parameters (bool, optional): If True, the function also loads the 
                                              model parameters from a JSON file. 
                                              Default is True.

        Returns:
            model (keras.Model): The loaded Keras model.

        '''        
        model_folders = []
        for entry in os.scandir(path):
            if entry.is_dir():
                model_folders.append(entry.name)
        if len(model_folders) > 1:
            model_folders.sort()
            index_list = [idx + 1 for idx, item in enumerate(model_folders)]     
            print('Please select a pretrained model:') 
            print()
            for i, directory in enumerate(model_folders):
                print(f'{i + 1} - {directory}')        
            print()               
            while True:
                try:
                    dir_index = int(input('Type the model index to select it: '))
                    print()
                except:
                    continue
                break                         
            while dir_index not in index_list:
                try:
                    dir_index = int(input('Input is not valid! Try again: '))
                    print()
                except:
                    continue
            self.folder_path = os.path.join(path, model_folders[dir_index - 1])

        elif len(model_folders) == 1:
            self.folder_path = os.path.join(path, model_folders[0])                 
        
        model_path = os.path.join(self.folder_path, 'model') 
        model = tf.keras.models.load_model(model_path)
        path = os.path.join(self.folder_path, 'model_parameters.json')
        with open(path, 'r') as f:
            configuration = json.load(f)               
        
        return model, configuration


    #-------------------------------------------------------------------------- 
    def load_pretrained_model_JL(self, path):

        '''
        Load pretrained keras model (in folders) from the specified directory. 
        If multiple model directories are found, the user is prompted to select one,
        while if only one model directory is found, that model is loaded directly.
        If `load_parameters` is True, the function also loads the model parameters 
        from the target .json file in the same directory. 

        Keyword arguments:
            path (str): The directory path where the pretrained models are stored.
            load_parameters (bool, optional): If True, the function also loads the 
                                              model parameters from a JSON file. 
                                              Default is True.

        Returns:
            model (keras.Model): The loaded Keras model.

        '''        
        model_folders = [entry.name for entry in os.scandir(path) if entry.is_dir()]
    
        if len(model_folders) > 1:
            model_folders.sort()
            dropdown = Dropdown(options=model_folders, description='Select Model:')
            display(dropdown)
            # Wait for the user to select a model. This cell should be manually executed again after selection.            
            self.folder_path = os.path.join(path, dropdown.value)

        elif len(model_folders) == 1:
            self.folder_path = os.path.join(path, model_folders[0])
        else:
            raise FileNotFoundError('No model directories found in the specified path.')
        
        model_path = os.path.join(self.folder_path, 'model')
        model = tf.keras.models.load_model(model_path)
        
        configuration = {}        
        parameters_path = os.path.join(self.folder_path, 'model_parameters.json')
        if os.path.exists(parameters_path):
            with open(parameters_path, 'r') as f:
                configuration = json.load(f)
        else:
            print('No parameters file found. Continuing without loading parameters.')
            
        return model, configuration  