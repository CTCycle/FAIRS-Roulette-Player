import pandas as pd
import numpy as np

from FAIRS.commons.constants import CONFIG
from FAIRS.commons.logger import logger

# [DATA SPLITTING]
###############################################################################
class DatasetSplit:

    def __init__(self, dataframe: pd.DataFrame):

        # Set the sizes for the train and validation datasets        
        self.validation_size = CONFIG["dataset"]["VALIDATION_SIZE"]
        self.window_size = CONFIG["dataset"]["WINDOW_SIZE"]
        self.train_size = 1.0 - self.validation_size
        self.dataframe = dataframe.reset_index(drop=True)  

        # Compute the sizes of each split
        total_samples = len(dataframe)
        self.train_size = int(total_samples * self.train_size)
        self.val_size = int(total_samples * self.validation_size)
        
    #--------------------------------------------------------------------------
    def split_train_and_validation(self):
       
        df_train = self.dataframe.iloc[:self.train_size]
        df_test = self.dataframe.iloc[self.train_size:]

        return df_train, df_test

  

   
