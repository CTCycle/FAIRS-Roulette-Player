import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import OrdinalEncoder

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [PREPROCESSING]
###############################################################################
class RouletteMapper:

    def __init__(self):
        self.categories = [['green', 'black', 'red']]
        self.position_map = {0: 0, 32: 1, 15: 2, 19: 3, 4: 4, 21: 5, 2: 6, 25: 7, 17: 8, 
                            34: 9, 6: 10, 27: 11, 13: 12, 36: 13, 11: 14, 30: 15, 8: 16, 
                            23: 17, 10: 18, 5: 19, 24: 20, 16: 21, 33: 22, 1: 23, 20: 24, 
                            14: 25, 31: 26, 9: 27, 22: 28, 18: 29, 29: 30, 7: 31, 28: 32, 
                            12: 33, 35: 34, 3: 35, 26: 36}
        self.color_map = {'black' : [15, 4, 2, 17, 6, 13, 11, 8, 10, 24, 33, 20, 31, 22, 29, 28, 35, 26],
                          'red' : [32, 19, 21, 25, 34, 27, 36, 30, 23, 5, 16, 1, 14, 9, 18, 7, 12, 3],
                          'green' : [0]}  

    #--------------------------------------------------------------------------
    def map_roulette_positions(self, dataframe : pd.DataFrame):        
        
        dataframe['position'] = dataframe['timeseries'].map(self.position_map)
        
        return dataframe    
    
    #--------------------------------------------------------------------------
    def map_roulette_colors(self, dataframe : pd.DataFrame):    
                        
        reverse_color_map = {v: k for k, values in self.color_map.items() for v in values}        
        dataframe['color'] = dataframe['timeseries'].map(reverse_color_map)

        return dataframe    
    
    #--------------------------------------------------------------------------
    def encode_roulette_extractions(self, dataframe : pd.DataFrame): 
        
        dataframe = self.map_roulette_positions(dataframe)
        dataframe = self.map_roulette_colors(dataframe)

        encoder = OrdinalEncoder(categories=self.categories, 
                                 handle_unknown='use_encoded_value', 
                                 unknown_value=-1)
        color_mapped_values = dataframe['color'].values.reshape(-1, 1)
        encoded_data = encoder.fit_transform(color_mapped_values)
        dataframe['encoded color'] = encoded_data.astype(int)                                             

        return dataframe, encoder
        
    
    
    
     
    
    
   
     

   
