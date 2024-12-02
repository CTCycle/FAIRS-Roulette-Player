import numpy as np
import torch
import tensorflow as tf
import keras


from FAIRS.commons.utils.process.mapping import RouletteMapper
from FAIRS.commons.constants import CONFIG, PRED_PATH
from FAIRS.commons.logger import logger




###############################################################################
class RouletteForecaster:

    def __init__(self, model : keras.Model, configuration, sequences : np.array):        

        np.random.seed(configuration["SEED"])
        torch.manual_seed(configuration["SEED"])
        tf.random.set_seed(configuration["SEED"])
        self.mapper = RouletteMapper()        
              
        self.model = model 
        self.configuration = configuration
        self.sequences = sequences 
        self.window_size = configuration["dataset"]["PERCEPTIVE_SIZE"] 

        self.layer_names = [layer.name for layer in model.layers]  
        logger.debug(f'model layers detected: {self.layer_names}')

        self.encoder_layer_names = [x for x in self.layer_names if 'tranformer_encoder' in x] 
        self.decoder_layer_names = [x for x in self.layer_names if 'tranformer_decoder' in x]        

    #--------------------------------------------------------------------------    
    def get_prediction_window(self):
        last_extractions =  np.expand_dims(self.sequences[-1, :, 0][1:], axis=0)
        last_positions = np.expand_dims(self.sequences[-1, :, 1][1:], axis=0)
        start_extraction = last_extractions[0,1]
        start_position = last_positions[0,1]

        return last_extractions, last_positions, start_extraction, start_position       
    
    #--------------------------------------------------------------------------    
    def generate_sequences(self):
  
        inverted_position_mapping = {v : k for k, v in self.mapper.position_map.items()}     
        last_extractions, last_positions, sequence_start, pos_start = self.get_prediction_window()    
           
           
        return last_extractions
    

    



