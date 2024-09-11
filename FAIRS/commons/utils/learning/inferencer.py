import os
import pandas as pd
import numpy as np
import torch
import tensorflow as tf
import keras
from tqdm import tqdm

from FAIRS.commons.utils.preprocessing.mapping import RouletteMapper
from FAIRS.commons.utils.dataloader.serializer import DataSerializer
from FAIRS.commons.constants import CONFIG, PRED_PATH
from FAIRS.commons.logger import logger




###############################################################################
class RouletteGenerator:

    def __init__(self, model : keras.Model, configuration, sequences : np.array):        

        np.random.seed(configuration["SEED"])
        torch.manual_seed(configuration["SEED"])
        tf.random.set_seed(configuration["SEED"])
        self.mapper = RouletteMapper()        
              
        self.model = model 
        self.configuration = configuration
        self.sequences = sequences 
        self.window_size = configuration["dataset"]["WINDOW_SIZE"] 

        self.layer_names = [layer.name for layer in model.layers]     
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
    def greed_search_generator(self):
  
        inverted_position_mapping = {v : k for k, v in self.mapper.position_map.items()}     
        last_extractions, last_positions, sequence_start, pos_start = self.get_prediction_window()
            
        decoder_sequence = keras.ops.zeros((1, self.window_size), dtype=torch.int32)   
        decoder_position = keras.ops.zeros((1, self.window_size), dtype=torch.int32)        
        decoder_sequence[0, 0] = sequence_start 
        decoder_position[0, 0] = pos_start

        for i in tqdm(range(1, self.window_size)):                
            predictions = self.model.predict([last_extractions, last_positions, 
                                                decoder_sequence, decoder_position], verbose=0)                
            next_position = keras.ops.argmax(predictions[0, i-1, :], axis=-1).item()  
            next_extraction = inverted_position_mapping[next_position]           
            decoder_position[0, i] = next_position
            decoder_sequence[0, i] = next_extraction       
           
        return decoder_position




