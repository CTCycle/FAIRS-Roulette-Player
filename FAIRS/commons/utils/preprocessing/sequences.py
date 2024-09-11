import pandas as pd
import numpy as np

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger


# [DATA SPLITTING]
###############################################################################
class TimeSequencer:

    def __init__(self):

        # Set the sizes for the train and validation datasets        
        self.validation_size = CONFIG["dataset"]["VALIDATION_SIZE"]
        self.window_size = CONFIG["dataset"]["WINDOW_SIZE"]       

    #--------------------------------------------------------------------------
    def generate_shifted_sequences(self, dataframe : pd.DataFrame):
        
        features = {'timeseries' : dataframe['timeseries'].values,
                    'position' : dataframe['position'].values,
                    'color' : dataframe['encoded color'].values}
        
        full_sequence_len = self.window_size + 1
        shifted_sequences = {}
        for k, v in features.items():                   
            X_data = np.array([v[i : i + full_sequence_len] for i in range(len(v) - full_sequence_len)])                             
            shifted_sequences[k] = X_data

        stacked_data = np.transpose(np.stack([v for v in shifted_sequences.values()]), (1, 2, 0))
        
        return stacked_data
    
 

   
