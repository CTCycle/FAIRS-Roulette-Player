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
        self.window_size = configuration["dataset"]["PERCEPTIVE_SIZE"] 

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
    def generate_sequence_by_greed_search(self):
  
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
    

    #--------------------------------------------------------------------------    
    # def build_predictions_dataset(self):

        
    #     # create dummy arrays to fill first positions 
    #     nan_array_probs = np.full((parameters['window_size'], 3), np.nan)
    #     nan_array_values = np.full((parameters['window_size'], 1), np.nan)
    #     # create and reshape last window of inputs to obtain the future prediction
    #     last_window = timeseries['encoding'].tail(parameters['window_size'])
    #     last_window = np.reshape(last_window, (1, parameters['window_size'], 1))
    #     # predict from inputs and last window and stack arrays   
    #     probability_vectors = model.predict(pred_inputs)   
    #     next_prob_vector = model.predict(last_window)
    #     predicted_probs = np.vstack((nan_array_probs, probability_vectors, next_prob_vector))
    #     # find the most probable class using argmax on the probability vector
    #     expected_value = np.argmax(probability_vectors, axis=-1)    
    #     next_exp_value = np.argmax(next_prob_vector, axis=-1)
    #     # decode the classes to obtain original color code  
    #     expected_value = encoder.inverse_transform(expected_value.reshape(-1, 1))       
    #     next_exp_value = encoder.inverse_transform(next_exp_value.reshape(-1, 1))
    #     predicted_value = np.vstack((nan_array_values, expected_value, next_exp_value))    
    #     # create the dataframe by adding the new columns with predictions
    #     df_timeseries.loc[df_timeseries.shape[0]] = ['?', '?'] 
    #     df_timeseries['probability of green'] = predicted_probs[:, 0]
    #     df_timeseries['probability of black'] = predicted_probs[:, 1]
    #     df_timeseries['probability of red'] = predicted_probs[:, 2] 
    #     df_timeseries['predicted color'] = predicted_value[:, 0]      
        
    # # predict extractions using the pretrained NumMatrix model, generate a dataframe
    # # containing original values and predictions     
    # else: 
    #     # create dummy arrays to fill first positions 
    #     nan_array_probs = np.full((parameters['window_size'], 37), np.nan)
    #     nan_array_values = np.full((parameters['window_size'], 1), np.nan)
    #     # create and reshape last window of inputs to obtain the future prediction
    #     last_window_ext = timeseries['encoding'].tail(parameters['window_size'])
    #     last_window_ext = np.reshape(last_window_ext, (1, parameters['window_size'], 1))
    #     last_window_pos = timeseries['position'].tail(parameters['window_size'])
    #     last_window_pos = np.reshape(last_window_pos, (1, parameters['window_size'], 1))
    #     # predict from inputs and last window    
    #     probability_vectors = model.predict([val_inputs, pos_inputs]) 
    #     next_prob_vector = model.predict([last_window_ext, last_window_pos])
    #     predicted_probs = np.vstack((nan_array_probs, probability_vectors, next_prob_vector))
    #     # find the most probable class using argmax on the probability vector
    #     expected_value = np.argmax(probability_vectors, axis=-1)    
    #     next_exp_value = np.argmax(next_prob_vector, axis=-1)     
    #     predicted_values = np.vstack((nan_array_values, expected_value.reshape(-1, 1), next_exp_value.reshape(-1, 1)))     
    #     # create the dataframe by adding the new columns with predictions
    #     df_timeseries.loc[df_timeseries.shape[0]] = ['?', '?', '?'] 
    #     for x in range(37):
    #         df_timeseries[f'probability of {x+1}'] = predicted_probs[:, x]     
    #     df_timeseries['predicted number'] = predicted_values[:, 0] 

    # # print predictions on console
    
    # print(f'Next predicted value: {next_exp_value[0,0]}\n')   
    # print('Probability vector from softmax (%):')
    # for i, x in enumerate(next_prob_vector[0]):
    #     if parameters['model_name'] == 'CCM':
    #         i = encoder.inverse_transform(np.reshape(i, (1, 1)))
    #         print(f'{i[0,0]} = {round((x * 100), 4)}')  
    #     else:
    #         print(f'{i+1} = {round((x * 100), 4)}')

    # # save files as .csv in prediction folder    
    # if parameters['model_name'] == 'CCM':  
    #     file_loc = os.path.join(PREDICTIONS_PATH, 'CCM_predictions.csv')         
    #     df_timeseries.to_csv(file_loc, index=False, sep=';', encoding='utf-8')
    # else:
    #     file_loc = os.path.join(PREDICTIONS_PATH, 'NMM_predictions.csv')         
    #     df_timeseries.to_csv(file_loc, index=False, sep=';', encoding='utf-8')










