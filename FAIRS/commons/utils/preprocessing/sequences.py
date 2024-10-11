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
    def generate_historical_sequences(self, dataframe: pd.DataFrame):
       
        features = {'timeseries': dataframe['timeseries'].values,
                    'position': dataframe['position'].values,
                    'color': dataframe['encoded color'].values}        
        
        shifted_sequences = {}        
        for k, v in features.items():            
            X_data = np.array([v[i:i + self.window_size ] for i in range(len(v) - self.window_size + 1)])  
            shifted_sequences[k] = X_data

        # Stack and transpose the sequences to match the desired shape (num_samples, window_size, num_features)
        stacked_data = np.transpose(np.stack([shifted_sequences[key] for key in shifted_sequences]), (1, 2, 0))
        
        return stacked_data
    
 

   
