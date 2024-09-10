import pandas as pd
import numpy as np

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

# [DATA SPLITTING]
###############################################################################
class RollingWindows:

    def __init__(self):

        # Set the sizes for the train and validation datasets        
        self.validation_size = CONFIG["dataset"]["VALIDATION_SIZE"]
        self.window_size = CONFIG["dataset"]["WINDOW_SIZE"]
       

    #--------------------------------------------------------------------------
    def timeseries_rolling_windows(self, dataframe : pd.DataFrame):
        
        features = {'timeseries' : dataframe['timeseries'].values,
                    'position' : dataframe['position'].values,
                    'color' : dataframe['encoded color'].values}
        
        rolling_windows = {}
        for k, v in features.items():                   
            X_data = np.array([v[i : i + self.window_size] for i in range(len(v) - self.window_size)])
            Y_data = np.array([v[i + self.window_size : i + self.window_size + 1] 
                               for i in range(len(v) - self.window_size)])
            
            
            # transpose data to shape (samples, window size, features)            
            rolling_windows[k] = (X_data, Y_data)
        
        return rolling_windows
    
    #--------------------------------------------------------------------------
    def stack_features_by_window(self, train_data : dict, validation_data : dict):

        # stack arrays to create single array with all data, then transpose to have number
        # of features on the last axis
        stacked_train_X = np.transpose(np.stack([v[0] for k, v in train_data.items()]), (1, 2, 0))
        stacked_val_X = np.transpose(np.stack([v[0] for k, v in validation_data.items()]), (1, 2, 0))
        stacked_train_Y = np.transpose(np.stack([v[1] for k, v in train_data.items()]), (1, 2, 0))
        stacked_val_Y = np.transpose(np.stack([v[1] for k, v in validation_data.items()]), (1, 2, 0))

        return stacked_train_X, stacked_train_Y, stacked_val_X, stacked_val_Y

   
